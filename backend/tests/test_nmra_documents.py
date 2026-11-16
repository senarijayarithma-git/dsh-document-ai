
from uuid import uuid4

import pymupdf
import pytest

from app.nmra_models import EmployeeUser
from app.auth_security import create_access_token, hash_password


def make_pdf(text):
    pdf = pymupdf.open()
    page = pdf.new_page()
    page.insert_text((72, 72), text)
    data = pdf.tobytes()
    pdf.close()
    return data


@pytest.fixture
def viewer_headers(test_db, monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "dsh-nmra-document-test-secret-only-2026",
    )

    employee = EmployeeUser(
        email=f"viewer-{uuid4().hex}@example.com",
        full_name="Document Test Viewer",
        password_hash=hash_password("TestPassword123!"),
        role="VIEWER",
        is_active=True,
    )

    test_db.add(employee)
    test_db.flush()

    token = create_access_token(employee.id)

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def reviewer_headers(test_db, monkeypatch):
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "dsh-nmra-document-test-secret-only-2026",
    )

    employee = EmployeeUser(
        email=f"reviewer-{uuid4().hex}@example.com",
        full_name="Document Test Reviewer",
        password_hash=hash_password("TestPassword123!"),
        role="REVIEWER",
        is_active=True,
    )

    test_db.add(employee)
    test_db.flush()

    token = create_access_token(employee.id)

    return {"Authorization": f"Bearer {token}"}


def test_viewer_can_search_and_read_uploaded_nmra_documents(
    client,
    viewer_headers,
    reviewer_headers,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setenv("NMRA_STORAGE_DIR", str(tmp_path))

    d_number = f"TEST-{uuid4().hex}".upper()
    evidence_text = f"Unique evidence {uuid4().hex}"

    upload_response = client.post(
        "/nmra/upload",
        data={"d_number": d_number},
        files=[
            (
                "certificate",
                (
                    "certificate.pdf",
                    make_pdf(evidence_text),
                    "application/pdf",
                ),
            ),
            (
                "attachments",
                (
                    "support.pdf",
                    make_pdf("Supporting evidence"),
                    "application/pdf",
                ),
            ),
        ],
        headers=reviewer_headers,
    )

    assert upload_response.status_code == 201, upload_response.text

    search_response = client.get(
        "/nmra/registrations",
        params={"q": evidence_text},
        headers=viewer_headers,
    )

    assert search_response.status_code == 200
    matches = search_response.json()

    registration = next(
        item for item in matches
        if item["d_number"] == d_number
    )

    details_response = client.get(
        f"/nmra/registrations/{registration['id']}",
        headers=viewer_headers,
    )

    assert details_response.status_code == 200
    details = details_response.json()

    assert len(details["versions"]) == 1
    assert len(details["attachments"]) == 1

    certificate_id = details["versions"][0]["id"]
    attachment_id = details["attachments"][0]["id"]

    certificate_pages = client.get(
        f"/nmra/certificates/{certificate_id}/pages",
        headers=viewer_headers,
    )

    assert certificate_pages.status_code == 200
    assert evidence_text in certificate_pages.json()[0]["text"]

    attachment_pages = client.get(
        f"/nmra/attachments/{attachment_id}/pages",
        headers=viewer_headers,
    )

    assert attachment_pages.status_code == 200
    assert "Supporting evidence" in attachment_pages.json()[0]["text"]

    certificate_pdf = client.get(
        f"/nmra/certificates/{certificate_id}/pdf",
        headers=viewer_headers,
    )

    assert certificate_pdf.status_code == 200
    assert certificate_pdf.headers["content-type"].startswith(
        "application/pdf"
    )
    assert certificate_pdf.content.startswith(b"%PDF-")

    attachment_pdf = client.get(
        f"/nmra/attachments/{attachment_id}/pdf",
        headers=viewer_headers,
    )

    assert attachment_pdf.status_code == 200
    assert attachment_pdf.content.startswith(b"%PDF-")


def test_nmra_document_search_requires_authentication(client):
    response = client.get("/nmra/registrations")

    assert response.status_code == 401
