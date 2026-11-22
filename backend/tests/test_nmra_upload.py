import io

import pymupdf
from fastapi.testclient import TestClient

from app.main import app
from uuid import uuid4

from sqlalchemy import select

from app.nmra_models import (
    NMRARegistration,
    NMRACertificateVersion,
    NMRAAttachment,
    NMRAAttachmentItem,
    NMRADocumentPage,
)
import os
import pytest

from app.nmra_models import EmployeeUser

from app.auth_security import (
    create_access_token,
    hash_password,
)

@pytest.fixture
def make_employee(test_db, monkeypatch):
    # Use a test-only JWT secret.
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "dsh-nmra-automated-test-secret-only-2026",
    )

    def create_employee(role):
        employee = EmployeeUser(
            email=f"test-{role.lower()}-{os.urandom(6).hex()}@example.com",
            full_name=f"Test {role}",
            password_hash=hash_password("TestPassword123!"),
            role=role,
            is_active=True,
        )

        test_db.add(employee)
        test_db.flush()

        token = create_access_token(employee.id)

        return employee, {
            "Authorization": f"Bearer {token}",
        }

    return create_employee

def make_pdf(text="Synthetic NMRA test document"):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    data = pdf.tobytes()
    pdf.close()
    return data


def test_upload_requires_authentication():
    client = TestClient(app)

    response = client.post(
        "/nmra/upload",
        data={"d_number": "TEST-D-100"},
        files={
            "certificate": (
                "certificate.pdf",
                io.BytesIO(make_pdf()),
                "application/pdf",
            )
        },
    )

    assert response.status_code in (401, 403)


def test_upload_rejects_missing_certificate():
    client = TestClient(app)

    response = client.post(
        "/nmra/upload",
        data={"d_number": "TEST-D-101"},
    )

    assert response.status_code in (401, 403, 422)

def test_authenticated_upload_saves_certificate_and_attachments(
    client,
    test_db,
    make_employee,
    tmp_path,
    monkeypatch,
):
    # Use temporary storage, never real company storage.
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    _, headers = make_employee("ADMIN")
    d_number = f"TEST-{uuid4().hex}".upper()
    response = client.post(
        "/nmra/upload",
        data={"d_number": d_number},
        files=[
            (
                "certificate",
                (
                    "certificate.pdf",
                    make_pdf("Certificate test evidence"),
                    "application/pdf",
                ),
            ),
            (
                "attachments",
                (
                    "attachment-one.pdf",
                    make_pdf("First attachment evidence"),
                    "application/pdf",
                ),
            ),
            (
                "attachments",
                (
                    "attachment-two.pdf",
                    make_pdf("Second attachment evidence"),
                    "application/pdf",
                ),
            ),
        ],
        headers=headers,
    )

    assert response.status_code == 201, response.text

    result = response.json()

    assert result["d_number"] == d_number
    assert result["version"] == 1
    assert result["review_status"] == "PENDING"
    assert len(result["attachments"]) == 2

    registration = test_db.scalar(
        select(NMRARegistration).where(
            NMRARegistration.d_number == d_number
        )
    )
    assert registration is not None

    certificate = test_db.scalar(
        select(NMRACertificateVersion).where(
            NMRACertificateVersion.registration_id
            == registration.id
        )
    )
    assert certificate is not None
    assert certificate.version == 1

    attachments = test_db.scalars(
        select(NMRAAttachment).where(
            NMRAAttachment.certificate_version_id
            == certificate.id
        )
    ).all()

    assert len(attachments) == 2

    certificate_pages = test_db.scalars(
        select(NMRADocumentPage).where(
            NMRADocumentPage.certificate_version_id
            == certificate.id
        )
    ).all()

    assert len(certificate_pages) == 1
    assert "Certificate test evidence" in (
        certificate_pages[0].extracted_text
    )

    for attachment in attachments:
        pages = test_db.scalars(
            select(NMRADocumentPage).where(
                NMRADocumentPage.attachment_id
                == attachment.id
            )
        ).all()

        assert len(pages) == 1

    # Confirm original PDFs were stored privately.
    assert (tmp_path / certificate.storage_key).is_file()

    for attachment in attachments:
        assert (tmp_path / attachment.storage_key).is_file()

def test_upload_new_version_preserves_previous_documents(
    client,
    test_db,
    make_employee,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    _, headers = make_employee("ADMIN")
    d_number = f"TEST-{uuid4().hex}".upper()

    def upload(certificate_text, attachment_name):
        return client.post(
            "/nmra/upload",
            data={"d_number": d_number},
            files=[
                (
                    "certificate",
                    (
                        "certificate.pdf",
                        make_pdf(certificate_text),
                        "application/pdf",
                    ),
                ),
                (
                    "attachments",
                    (
                        attachment_name,
                        make_pdf("Supporting evidence"),
                        "application/pdf",
                    ),
                ),
            ],
            headers=headers,
        )

    first = upload("Certificate version one", "old.pdf")
    assert first.status_code == 201, first.text
    assert first.json()["version"] == 1

    second = upload("Certificate version two", "new.pdf")
    assert second.status_code == 201, second.text
    assert second.json()["version"] == 2

    registration = test_db.scalar(
        select(NMRARegistration).where(
            NMRARegistration.d_number == d_number
        )
    )

    versions = test_db.scalars(
        select(NMRACertificateVersion)
        .where(
            NMRACertificateVersion.registration_id
            == registration.id
        )
        .order_by(NMRACertificateVersion.version)
    ).all()

    assert len(versions) == 2
    assert [v.version for v in versions] == [1, 2]

    for version in versions:
        assert (tmp_path / version.storage_key).is_file()

        attachments = test_db.scalars(
            select(NMRAAttachment).where(
                NMRAAttachment.certificate_version_id
                == version.id
            )
        ).all()

        assert len(attachments) == 1
        assert (tmp_path / attachments[0].storage_key).is_file()

        pages = test_db.scalars(
            select(NMRADocumentPage).where(
                NMRADocumentPage.certificate_version_id
                == version.id
            )
        ).all()

        assert len(pages) == 1
        assert f"Certificate version {['one', 'two'][version.version - 1]}" in (
            pages[0].extracted_text
        )

def test_viewer_cannot_upload_nmra_documents(
    client,
    make_employee,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    _, headers = make_employee("VIEWER")

    d_number = f"TEST-{uuid4().hex}".upper()

    response = client.post(
        "/nmra/upload",
        data={"d_number": d_number},
        files=[
            (
                "certificate",
                (
                    "certificate.pdf",
                    make_pdf("Viewer must not upload"),
                    "application/pdf",
                ),
            )
        ],
        headers=headers,
    )

    assert response.status_code == 403
    assert list(tmp_path.iterdir()) == []

def test_reviewer_can_upload_nmra_documents(
    client,
    make_employee,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    _, headers = make_employee("REVIEWER")
    d_number = f"TEST-{uuid4().hex}".upper()

    response = client.post(
        "/nmra/upload",
        data={"d_number": d_number},
        files=[
            (
                "certificate",
                (
                    "certificate.pdf",
                    make_pdf("Reviewer upload test"),
                    "application/pdf",
                ),
            )
        ],
        headers=headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["d_number"] == d_number
    assert response.json()["version"] == 1

def test_upload_automatically_saves_unreviewed_items(
    client,
    test_db,
    make_employee,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    def fake_extract(_pdf_path):
        return [
            {
                "item_code": "BLT00001",
                "product_description": None,
                "page_number": 1,
                "row_number": 1,
                "evidence_text": "1 BLT00001 TEST PRODUCT",
                "extraction_method": "OCR",
                "review_status": "UNREVIEWED",
            }
        ]

    monkeypatch.setattr(
        "app.nmra_upload.extract_attachment_items",
        fake_extract,
    )

    _, headers = make_employee("ADMIN")
    d_number = f"TEST-{uuid4().hex}".upper()

    response = client.post(
        "/nmra/upload",
        data={"d_number": d_number},
        files=[
            (
                "certificate",
                (
                    "certificate.pdf",
                    make_pdf("Certificate evidence"),
                    "application/pdf",
                ),
            ),
            (
                "attachments",
                (
                    "attachment.pdf",
                    make_pdf("Attachment evidence"),
                    "application/pdf",
                ),
            ),
        ],
        headers=headers,
    )

    assert response.status_code == 201, response.text

    attachment_id = response.json()["attachments"][0]["id"]

    items = test_db.scalars(
        select(NMRAAttachmentItem).where(
            NMRAAttachmentItem.attachment_id == attachment_id
        )
    ).all()

    assert len(items) == 1
    assert items[0].item_code == "BLT00001"
    assert items[0].review_status == "UNREVIEWED"

    attachment = test_db.get(NMRAAttachment, attachment_id)
    assert attachment.review_status == "PENDING"
    assert attachment.approved_at is None
    assert attachment.approved_by is None


def test_upload_ocr_failure_rolls_back_and_cleans_files(
    client,
    test_db,
    make_employee,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    def failing_extract(_pdf_path):
        raise RuntimeError("Simulated OCR failure")

    monkeypatch.setattr(
        "app.nmra_upload.extract_attachment_items",
        failing_extract,
    )

    _, headers = make_employee("ADMIN")
    d_number = f"TEST-{uuid4().hex}".upper()

    # Depending on the application's exception handler,
    # an unexpected OCR failure may propagate to TestClient.
    from fastapi.testclient import TestClient

    with TestClient(
        app,
        raise_server_exceptions=False,
    ) as failure_client:
        response = failure_client.post(
            "/nmra/upload",
            data={"d_number": d_number},
            files=[
                (
                    "certificate",
                    (
                        "certificate.pdf",
                        make_pdf("Certificate evidence"),
                        "application/pdf",
                    ),
                ),
                (
                    "attachments",
                    (
                        "attachment.pdf",
                        make_pdf("Attachment evidence"),
                        "application/pdf",
                    ),
                ),
            ],
            headers=headers,
        )

    assert response.status_code >= 500

    registration = test_db.scalar(
        select(NMRARegistration).where(
            NMRARegistration.d_number == d_number
        )
    )
    assert registration is None

    # No private PDFs should remain after the failed upload.
    assert list(tmp_path.iterdir()) == []

def test_upload_with_zero_candidates_requires_manual_review(
    client,
    test_db,
    make_employee,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    # Simulate a valid PDF with no recognizable item codes.
    monkeypatch.setattr(
        "app.nmra_upload.extract_attachment_items",
        lambda _pdf_path: [],
    )

    _, headers = make_employee("ADMIN")
    d_number = f"TEST-{uuid4().hex}".upper()

    response = client.post(
        "/nmra/upload",
        data={"d_number": d_number},
        files=[
            (
                "certificate",
                (
                    "certificate.pdf",
                    make_pdf("Certificate evidence"),
                    "application/pdf",
                ),
            ),
            (
                "attachments",
                (
                    "attachment.pdf",
                    make_pdf("Supporting document without item codes"),
                    "application/pdf",
                ),
            ),
        ],
        headers=headers,
    )

    assert response.status_code == 201, response.text

    attachment_result = response.json()["attachments"][0]

    assert attachment_result["candidate_count"] == 0
    assert attachment_result["extraction_status"] == "REVIEW_REQUIRED"
    assert attachment_result["review_status"] == "PENDING"
    assert "Manual review required" in attachment_result["review_message"]

    attachment = test_db.get(
        NMRAAttachment,
        attachment_result["id"],
    )

    assert attachment is not None
    assert attachment.review_status == "PENDING"
    assert attachment.approved_at is None
    assert attachment.approved_by is None

    items = test_db.scalars(
        select(NMRAAttachmentItem).where(
            NMRAAttachmentItem.attachment_id == attachment.id
        )
    ).all()

    assert items == []
