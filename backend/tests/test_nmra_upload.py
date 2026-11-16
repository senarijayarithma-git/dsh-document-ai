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
