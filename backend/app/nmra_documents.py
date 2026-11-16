
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.auth_dependencies import get_current_employee
from app.database import get_db
from app.nmra_models import (
    NMRARegistration,
    NMRACertificateVersion,
    NMRAAttachment,
    NMRADocumentPage,
)
from app.nmra_storage import get_storage_root, NMRAStorageError


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/nmra",
    tags=["NMRA Documents"],
    dependencies=[Depends(get_current_employee)],
)


def resolve_private_pdf(storage_key: str) -> Path:
    # Storage keys must be simple UUID-based PDF filenames.
    if (
        not storage_key
        or Path(storage_key).name != storage_key
        or not storage_key.endswith(".pdf")
        or len(storage_key) != 36
    ):
        raise HTTPException(404, "PDF not found")

    try:
        root = get_storage_root()
    except NMRAStorageError:
        logger.error("NMRA storage is not configured")
        raise HTTPException(503, "Document storage unavailable")

    path = (root / storage_key).resolve()

    if not path.is_relative_to(root):
        raise HTTPException(404, "PDF not found")

    if not path.is_file():
        raise HTTPException(404, "PDF not found")

    return path


def serialize_pages(pages):
    return [
        {
            "page_number": page.page_number,
            "text": page.extracted_text,
            "method": page.extraction_method,
        }
        for page in pages
    ]


@router.get("/registrations")
def search_registrations(
    q: str = "",
    db: Session = Depends(get_db),
):
    query = select(NMRARegistration)

    if q.strip():
        term = f"%{q.strip()}%"

        matching_certificate_ids = (
            select(NMRACertificateVersion.registration_id)
            .join(
                NMRADocumentPage,
                NMRADocumentPage.certificate_version_id
                == NMRACertificateVersion.id,
            )
            .where(NMRADocumentPage.extracted_text.ilike(term))
        )

        matching_attachment_ids = (
            select(NMRAAttachment.registration_id)
            .join(
                NMRADocumentPage,
                NMRADocumentPage.attachment_id
                == NMRAAttachment.id,
            )
            .where(NMRADocumentPage.extracted_text.ilike(term))
        )

        query = query.where(
            or_(
                NMRARegistration.d_number.ilike(term),
                NMRARegistration.product_name.ilike(term),
                NMRARegistration.id.in_(matching_certificate_ids),
                NMRARegistration.id.in_(matching_attachment_ids),
            )
        )

    registrations = db.scalars(
        query.order_by(NMRARegistration.id.desc()).limit(100)
    ).all()

    return [
        {
            "id": registration.id,
            "d_number": registration.d_number,
            "product_name": registration.product_name,
            "registration_expiry": registration.registration_expiry,
            "import_licence_expiry": registration.import_licence_expiry,
        }
        for registration in registrations
    ]


@router.get("/registrations/{registration_id}")
def get_registration(
    registration_id: int,
    db: Session = Depends(get_db),
):
    registration = db.get(NMRARegistration, registration_id)

    if registration is None:
        raise HTTPException(404, "Registration not found")

    versions = db.scalars(
        select(NMRACertificateVersion)
        .where(
            NMRACertificateVersion.registration_id
            == registration_id
        )
        .order_by(NMRACertificateVersion.version.desc())
    ).all()

    attachments = db.scalars(
        select(NMRAAttachment)
        .where(NMRAAttachment.registration_id == registration_id)
        .order_by(NMRAAttachment.id.desc())
    ).all()

    return {
        "id": registration.id,
        "d_number": registration.d_number,
        "product_name": registration.product_name,
        "registration_expiry": registration.registration_expiry,
        "import_licence_expiry": registration.import_licence_expiry,
        "versions": [
            {
                "id": version.id,
                "version": version.version,
                "filename": version.filename,
                "review_status": version.review_status,
                "uploaded_at": version.uploaded_at,
            }
            for version in versions
        ],
        "attachments": [
            {
                "id": attachment.id,
                "certificate_version_id":
                    attachment.certificate_version_id,
                "filename": attachment.filename,
                "review_status": attachment.review_status,
                "uploaded_at": attachment.uploaded_at,
            }
            for attachment in attachments
        ],
    }


@router.get("/certificates/{certificate_id}/pages")
def get_certificate_pages(
    certificate_id: int,
    db: Session = Depends(get_db),
):
    certificate = db.get(
        NMRACertificateVersion,
        certificate_id,
    )

    if certificate is None:
        raise HTTPException(404, "Certificate not found")

    pages = db.scalars(
        select(NMRADocumentPage)
        .where(
            NMRADocumentPage.certificate_version_id
            == certificate_id
        )
        .order_by(NMRADocumentPage.page_number)
    ).all()

    return serialize_pages(pages)


@router.get("/attachments/{attachment_id}/pages")
def get_attachment_pages(
    attachment_id: int,
    db: Session = Depends(get_db),
):
    attachment = db.get(NMRAAttachment, attachment_id)

    if attachment is None:
        raise HTTPException(404, "Attachment not found")

    pages = db.scalars(
        select(NMRADocumentPage)
        .where(NMRADocumentPage.attachment_id == attachment_id)
        .order_by(NMRADocumentPage.page_number)
    ).all()

    return serialize_pages(pages)


@router.get("/certificates/{certificate_id}/pdf")
def get_certificate_pdf(
    certificate_id: int,
    db: Session = Depends(get_db),
):
    certificate = db.get(
        NMRACertificateVersion,
        certificate_id,
    )

    if certificate is None:
        raise HTTPException(404, "Certificate not found")

    path = resolve_private_pdf(certificate.storage_key)

    return FileResponse(
        path,
        media_type="application/pdf",
        content_disposition_type="inline",
        filename="certificate.pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/attachments/{attachment_id}/pdf")
def get_attachment_pdf(
    attachment_id: int,
    db: Session = Depends(get_db),
):
    attachment = db.get(NMRAAttachment, attachment_id)

    if attachment is None:
        raise HTTPException(404, "Attachment not found")

    path = resolve_private_pdf(attachment.storage_key)

    return FileResponse(
        path,
        media_type="application/pdf",
        content_disposition_type="inline",
        filename="attachment.pdf",
        headers={"Cache-Control": "no-store"},
    )
