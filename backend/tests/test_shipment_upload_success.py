import pymupdf
import pytest

from app.ai_extraction import (
    InvoiceExtraction,
    PackingListExtraction,
    AirWaybillExtraction,
)
from datetime import datetime, timezone
from uuid import uuid4

from app.nmra_models import (
    NMRARegistration,
    NMRAAttachment,
    NMRAAttachmentItem,
)

@pytest.fixture
def authenticated_client(client):
    from app.main import app
    from app.auth_dependencies import get_current_employee
    from app.nmra_models import EmployeeUser

    employee = EmployeeUser(
        id=999999,
        email="upload-test@example.com",
        full_name="Upload Test Employee",
        role="ADMIN",
        is_active=True,
        password_hash="test-only-not-a-real-password",
    )

    previous_override = app.dependency_overrides.get(
        get_current_employee
    )

    app.dependency_overrides[get_current_employee] = (
        lambda: employee
    )

    try:
        yield client
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(
                get_current_employee, None
            )
        else:
            app.dependency_overrides[
                get_current_employee
            ] = previous_override

def make_pdf(text):
    """Create a valid, text-readable PDF in memory."""
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def test_upload_processes_all_three_pdfs(authenticated_client, monkeypatch):
    import app.main as main_module

    processed_types = []

    # Prevent cache access during this test.
    monkeypatch.setattr(
        main_module,
        "get_cached_result",
        lambda key: None,
    )
    monkeypatch.setattr(
        main_module,
        "save_cached_result",
        lambda *args, **kwargs: None,
    )

    def fake_extraction(text, document_type):
        processed_types.append(document_type)

        if document_type == "invoice":
            return InvoiceExtraction(
                invoice_number="INV-TEST-001",
                items=[
                    {
                        "product": "Test Product",
                        "item_code": "NMRA-TEST-001",
                        "quantity": 5,
                        "unit_price": 10,
                        "amount": 50,
                    }
                ],
                total_amount=50,
            )

        if document_type == "packing_list":
            return PackingListExtraction(
                invoice_number="INV-TEST-001",
                items=[
                    {
                        "product": "Test Product",
                        "quantity": 5,
                    }
                ],
            )

        if document_type == "air_waybill":
            return AirWaybillExtraction(
                awb_number="AWB-TEST-001",
            )

        raise AssertionError(
            f"Unexpected document type: {document_type}"
        )

    monkeypatch.setattr(
        main_module,
        "extract_structured_data",
        fake_extraction,
    )

    files = {
        "invoice_file": (
            "invoice.pdf",
            make_pdf("Invoice INV-TEST-001"),
            "application/pdf",
        ),
        "packing_list_file": (
            "packing.pdf",
            make_pdf("Packing list INV-TEST-001"),
            "application/pdf",
        ),
        "air_waybill_file": (
            "airwaybill.pdf",
            make_pdf("Air waybill AWB-TEST-001"),
            "application/pdf",
        ),
    }

    response = authenticated_client.post(
        "/shipments/upload-and-verify",
        files=files,
    )

    assert response.status_code == 200, response.text

    assert processed_types == [
        "invoice",
        "packing_list",
        "air_waybill",
    ]

    data = response.json()

    assert set(data["documents"]) == {
        "invoice",
        "packing_list",
        "air_waybill",
    }

    assert data["documents"]["invoice"]["extracted_data"][
        "items"
    ][0]["item_code"] == "NMRA-TEST-001"

    assert "summary" in data
    assert "findings" in data
    assert "report" in data
    assert "nmra_matches" in data
    assert len(data["nmra_matches"]) == 1

    match = data["nmra_matches"][0]

    assert match["product_code"] == "NMRA-TEST-001"
    assert match["status"] in {
        "MATCHED",
        "NO_MATCH",
        "AMBIGUOUS",
        "INSUFFICIENT_DATA",
    }

def test_uploaded_invoice_matches_approved_nmra_evidence(
    authenticated_client,
    test_db,
    monkeypatch,
):
    import app.main as main_module

    unique_id = uuid4().hex[:12].upper()
    product_code = f"UPL{unique_id}"
    d_number = f"TEST-UPLOAD-{unique_id}"

    registration = NMRARegistration(
        d_number=d_number,
        product_name="Upload Matching Test Product",
    )
    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="upload-approved.pdf",
        storage_key=f"upload-approved-{unique_id}.pdf",
        version=1,
        review_status="APPROVED",
        approved_at=datetime.now(timezone.utc),
        approved_by="pytest",
    )
    test_db.add(attachment)
    test_db.flush()

    item = NMRAAttachmentItem(
        attachment_id=attachment.id,
        item_code=product_code,
        product_description="Upload Matching Test Product",
        page_number=2,
        row_number=3,
        review_status="REVIEWED",
    )
    test_db.add(item)
    test_db.flush()

    monkeypatch.setattr(
        main_module,
        "get_cached_result",
        lambda key: None,
    )
    monkeypatch.setattr(
        main_module,
        "save_cached_result",
        lambda *args, **kwargs: None,
    )

    def fake_extraction(text, document_type):
        if document_type == "invoice":
            return InvoiceExtraction(
                invoice_number="INV-UPLOAD-MATCH",
                items=[
                    {
                        "product": "Upload Matching Test Product",
                        "item_code": product_code,
                        "quantity": 1,
                    }
                ],
            )

        if document_type == "packing_list":
            return PackingListExtraction(
                invoice_number="INV-UPLOAD-MATCH",
            )

        if document_type == "air_waybill":
            return AirWaybillExtraction(
                awb_number="AWB-UPLOAD-MATCH",
            )

        raise AssertionError(
            f"Unexpected document type: {document_type}"
        )

    monkeypatch.setattr(
        main_module,
        "extract_structured_data",
        fake_extraction,
    )

    files = {
        "invoice_file": (
            "invoice.pdf",
            make_pdf("Invoice INV-UPLOAD-MATCH"),
            "application/pdf",
        ),
        "packing_list_file": (
            "packing.pdf",
            make_pdf("Packing list INV-UPLOAD-MATCH"),
            "application/pdf",
        ),
        "air_waybill_file": (
            "airwaybill.pdf",
            make_pdf("Air waybill AWB-UPLOAD-MATCH"),
            "application/pdf",
        ),
    }

    response = authenticated_client.post(
        "/shipments/upload-and-verify",
        files=files,
    )

    assert response.status_code == 200, response.text

    data = response.json()
    matches = data["nmra_matches"]

    assert len(matches) == 1
    assert matches[0]["product_code"] == product_code
    assert matches[0]["status"] == "MATCHED"

    evidence = matches[0]["evidence"]

    assert len(evidence) == 1
    assert evidence[0]["d_number"] == d_number
    assert evidence[0]["attachment_id"] == attachment.id
    assert evidence[0]["page_number"] == 2
    assert evidence[0]["row_number"] == 3

    findings = {
        finding["rule_code"]: finding
        for finding in data["findings"]
    }

    assert findings["REG-001"]["status"] == "NOT_VERIFIED"
