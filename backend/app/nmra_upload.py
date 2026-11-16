
import logging
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth_dependencies import require_nmra_reviewer
from app.database import get_db
from app.nmra_models import (
    NMRAAttachment,
    NMRACertificateVersion,
    NMRADocumentPage,
    NMRARegistration,
)
from app.nmra_pdf_service import (
    MAX_PDF_BYTES,
    NMRAInvalidPDFError,
    NMRAPDFLimitError,
    extract_nmra_pdf_pages,
)
from app.nmra_storage import (
    NMRAStorageError,
    delete_private_pdf,
    save_private_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/nmra",
    tags=["NMRA Upload"],
    dependencies=[Depends(require_nmra_reviewer)],
)

MAX_ATTACHMENTS = 10


def safe_filename(filename: str | None) -> str:
    # Never use the supplied filename as a filesystem path.
    name = (filename or "document.pdf").replace("\\", "/")
    name = PurePosixPath(name).name.strip()

    if not name or len(name) > 500:
        raise HTTPException(400, "Invalid PDF filename")

    if not name.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF filenames are accepted")

    return name


async def prepare_pdf(upload: UploadFile):
    filename = safe_filename(upload.filename)

    if upload.content_type != "application/pdf":
        raise HTTPException(
            400,
            f"{filename}: expected application/pdf",
        )

    data = await upload.read(MAX_PDF_BYTES + 1)

    if len(data) > MAX_PDF_BYTES:
        raise HTTPException(
            413,
            f"{filename}: PDF exceeds 10 MiB",
        )

    try:
        pages = extract_nmra_pdf_pages(data)
    except NMRAPDFLimitError as exc:
        raise HTTPException(413, str(exc)) from exc
    except NMRAInvalidPDFError as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            503,
            "OCR service is unavailable",
        ) from exc
    except Exception as exc:
        logger.exception("NMRA PDF extraction failed")
        raise HTTPException(
            500,
            "Unable to extract PDF text",
        ) from exc

    return {
        "filename": filename,
        "data": data,
        "pages": pages,
    }


def add_pages(
    db: Session,
    pages,
    *,
    certificate_version_id=None,
    attachment_id=None,
):
    now = datetime.now(timezone.utc)

    for page in pages:
        db.add(
            NMRADocumentPage(
                certificate_version_id=certificate_version_id,
                attachment_id=attachment_id,
                page_number=page.page_number,
                extracted_text=page.text,
                extraction_method=page.method,
                created_at=now,
            )
        )


@router.post("/upload", status_code=201)
async def upload_nmra_documents(
    d_number: str = Form(...),
    certificate: UploadFile = File(...),
    attachments: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
):
    d_number = d_number.strip().upper()

    if not d_number or len(d_number) > 100:
        raise HTTPException(422, "Invalid D-number")

    attachment_files = attachments or []

    if len(attachment_files) > MAX_ATTACHMENTS:
        raise HTTPException(
            413,
            "Maximum 10 attachments per upload",
        )

    # Validate and extract everything before saving files.
    prepared_certificate = await prepare_pdf(certificate)
    prepared_attachments = []

    for attachment in attachment_files:
        prepared_attachments.append(
            await prepare_pdf(attachment)
        )

    saved_keys = []

    try:
        # Lock the registration row when it already exists.
        registration = db.scalar(
            select(NMRARegistration)
            .where(NMRARegistration.d_number == d_number)
            .with_for_update()
        )

        if registration is None:
            registration = NMRARegistration(
                d_number=d_number,
                certificate_filename=prepared_certificate["filename"],
            )
            db.add(registration)
            db.flush()

        latest_version = db.scalar(
            select(NMRACertificateVersion.version)
            .where(
                NMRACertificateVersion.registration_id
                == registration.id
            )
            .order_by(NMRACertificateVersion.version.desc())
            .limit(1)
        )

        next_version = (latest_version or 0) + 1
        now = datetime.now(timezone.utc)

        certificate_key = save_private_pdf(
            prepared_certificate["data"]
        )
        saved_keys.append(certificate_key)

        certificate_record = NMRACertificateVersion(
            registration_id=registration.id,
            version=next_version,
            filename=prepared_certificate["filename"],
            storage_key=certificate_key,
            review_status="PENDING",
            uploaded_at=now,
        )

        db.add(certificate_record)
        db.flush()

        add_pages(
            db,
            prepared_certificate["pages"],
            certificate_version_id=certificate_record.id,
        )

        attachment_results = []

        for prepared in prepared_attachments:
            attachment_key = save_private_pdf(
                prepared["data"]
            )
            saved_keys.append(attachment_key)

            attachment_record = NMRAAttachment(
                registration_id=registration.id,
                certificate_version_id=certificate_record.id,
                filename=prepared["filename"],
                storage_key=attachment_key,
                version=next_version,
                review_status="PENDING",
                uploaded_at=now,
            )

            db.add(attachment_record)
            db.flush()

            add_pages(
                db,
                prepared["pages"],
                attachment_id=attachment_record.id,
            )

            attachment_results.append(
                {
                    "id": attachment_record.id,
                    "filename": prepared["filename"],
                    "pages": len(prepared["pages"]),
                }
            )

        db.commit()

        return {
            "message": "NMRA documents uploaded for review",
            "registration_id": registration.id,
            "d_number": d_number,
            "certificate_version_id": certificate_record.id,
            "version": next_version,
            "certificate": {
                "filename": prepared_certificate["filename"],
                "pages": len(prepared_certificate["pages"]),
            },
            "attachments": attachment_results,
            "review_status": "PENDING",
        }

    except (IntegrityError, SQLAlchemyError):
        db.rollback()
        for key in saved_keys:
            try:
                delete_private_pdf(key)
            except NMRAStorageError:
                logger.exception("Failed to clean up NMRA PDF")
        logger.exception("NMRA database upload failed")
        raise HTTPException(
            409,
            "Upload conflict or database error; please retry",
        )

    except Exception:
        db.rollback()
        for key in saved_keys:
            try:
                delete_private_pdf(key)
            except NMRAStorageError:
                logger.exception("Failed to clean up NMRA PDF")
        raise
