
import os

from uuid import uuid4

from app.auth_security import create_access_token, hash_password
from app.nmra_models import EmployeeUser


def test_authenticated_employee_can_validate_shipment(
    client,
    test_db,
    monkeypatch,
):
    # Use a secret exclusively for automated testing.
    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "dsh-business-api-automated-test-secret-2026",
    )

    # Create an employee in the isolated test database.
    employee = EmployeeUser(
        email=f"business-test-{uuid4().hex}@example.com",
        full_name="Business API Test Employee",
        password_hash=hash_password("TestPassword123!"),
        role="ADMIN",
        is_active=True,
    )

    test_db.add(employee)
    test_db.flush()

    # Generate a real JWT for this test employee.
    token = create_access_token(employee.id)

    response = client.post(
        "/shipments/validate",
        headers={
            "Authorization": f"Bearer {token}",
        },
        json={
            "invoice": {
                "invoice_number": "INV-001",
                "consignee": "ABC Imports",
                "total": 5000,
                "currency": "USD",
                "items": [
                    {
                        "description": "Electronic Components",
                        "quantity": 100,
                    }
                ],
            },
            "packing_list": {
                "invoice_number": "INV-001",
                "consignee": "ABC Imports",
                "package_count": 10,
                "net_weight_kg": 90,
                "gross_weight_kg": 100,
                "items": [
                    {
                        "description": "Electronic Components",
                        "quantity": 100,
                    }
                ],
            },
            "air_waybill": {
                "awb_number": "123-45678901",
                "consignee": "ABC Imports",
                "package_count": 10,
                "gross_weight_kg": 100,
            },
        },
    )

    assert response.status_code == 200, response.text

    data = response.json()

    assert "findings" in data
    assert isinstance(data["findings"], list)

import io

import pytest


@pytest.fixture
def authenticated_client(client, test_db, monkeypatch):
    from uuid import uuid4

    from app.auth_security import create_access_token, hash_password
    from app.nmra_models import EmployeeUser

    monkeypatch.setenv(
        "JWT_SECRET_KEY",
        "dsh-business-api-automated-test-secret-2026",
    )

    employee = EmployeeUser(
        email=f"regression-{uuid4().hex}@example.com",
        full_name="Regression Test Employee",
        password_hash=hash_password("TestPassword123!"),
        role="ADMIN",
        is_active=True,
    )

    test_db.add(employee)
    test_db.flush()

    token = create_access_token(employee.id)

    client.headers.update({
        "Authorization": f"Bearer {token}",
    })

    return client


def test_authenticated_employee_can_list_documents(
    authenticated_client,
):
    response = authenticated_client.get("/documents")

    assert response.status_code == 200, response.text


def test_authenticated_employee_can_request_missing_document(
    authenticated_client,
):
    response = authenticated_client.get(
        "/documents/999999999"
    )

    assert response.status_code == 404, response.text


def test_authenticated_employee_can_extract_text_from_pdf(
    authenticated_client,
):
    from reportlab.pdfgen import canvas

    pdf_buffer = io.BytesIO()

    pdf = canvas.Canvas(pdf_buffer)
    pdf.drawString(72, 750, "DSH Document AI Regression Test")
    pdf.save()

    pdf_buffer.seek(0)

    response = authenticated_client.post(
        "/documents/extract-text",
        files={
            "file": (
                "regression-test.pdf",
                pdf_buffer,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200, response.text

def test_structured_extraction_rejects_missing_text(
    authenticated_client,
):
    response = authenticated_client.post(
        "/documents/extract-structured",
        json={
            "document_type": "invoice",
        },
    )

    assert response.status_code == 422, response.text


def test_structured_extraction_rejects_missing_document_type(
    authenticated_client,
):
    response = authenticated_client.post(
        "/documents/extract-structured",
        json={
            "text": "Invoice number INV-001",
        },
    )

    assert response.status_code == 422, response.text


def test_chat_rejects_invalid_document_id(
    authenticated_client,
):
    response = authenticated_client.post(
        "/chat/ask",
        json={
            "document_id": 0,
            "question": "What is the invoice number?",
        },
    )

    assert response.status_code == 422, response.text


def test_chat_rejects_empty_question(
    authenticated_client,
):
    response = authenticated_client.post(
        "/chat/ask",
        json={
            "document_id": 1,
            "question": "",
        },
    )

    assert response.status_code == 422, response.text
