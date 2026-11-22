
from app.main import app
from app.auth_dependencies import get_current_employee
from app.nmra_models import EmployeeUser


def test_verify_extracted_returns_nmra_matches(client):
    test_employee = EmployeeUser(
        id=999998,
        email="nmra-api-test@example.com",
        full_name="NMRA API Test Employee",
        role="ADMIN",
        is_active=True,
        password_hash="test-only-not-a-real-password",
    )

    previous_override = app.dependency_overrides.get(
        get_current_employee
    )
    app.dependency_overrides[get_current_employee] = (
        lambda: test_employee
    )

    shipment = {
        "invoice": {
            "invoice_number": "INV-NMRA-001",
            "consignee": "Test Imports",
            "items": [
                {
                    "description": "Test Medical Product",
                    "product_code": "BLT00001",
                    "quantity": 1,
                }
            ],
        },
        "packing_list": {
            "invoice_number": "INV-NMRA-001",
            "consignee": "Test Imports",
            "package_count": 1,
            "gross_weight_kg": 5,
        },
        "air_waybill": {
            "awb_number": "123-45678901",
            "consignee": "Test Imports",
            "package_count": 1,
            "gross_weight_kg": 5,
        },
    }

    try:
        response = client.post(
            "/shipments/verify-extracted",
            json=shipment,
        )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(
                get_current_employee, None
            )
        else:
            app.dependency_overrides[
                get_current_employee
            ] = previous_override

    assert response.status_code == 200

    data = response.json()

    assert "nmra_matches" in data
    assert len(data["nmra_matches"]) == 1

    assert data["nmra_matches"][0]["product_code"] == "BLT00001"

    findings = {
        finding["rule_code"]: finding
        for finding in data["findings"]
    }

    assert findings["REG-001"]["status"] == "NOT_VERIFIED"

from datetime import datetime, timezone
from uuid import uuid4

from app.database import get_db
from app.nmra_models import (
    NMRARegistration,
    NMRAAttachment,
    NMRAAttachmentItem,
)


def test_verify_extracted_matches_approved_nmra_evidence(
    client,
    test_db,
):
    unique_id = uuid4().hex[:12].upper()
    product_code = f"API{unique_id}"
    d_number = f"TEST-API-{unique_id}"

    registration = NMRARegistration(
        d_number=d_number,
        product_name="API Matching Test Product",
    )
    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="api-test-approved.pdf",
        storage_key=f"api-test-{unique_id}.pdf",
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
        product_description="API Matching Test Product",
        page_number=2,
        row_number=3,
        review_status="REVIEWED",
    )
    test_db.add(item)
    test_db.flush()

    test_employee = EmployeeUser(
        id=999997,
        email="nmra-match-test@example.com",
        full_name="NMRA Matching Test Employee",
        role="ADMIN",
        is_active=True,
        password_hash="test-only-not-a-real-password",
    )

    previous_override = app.dependency_overrides.get(
        get_current_employee
    )
    app.dependency_overrides[get_current_employee] = (
        lambda: test_employee
    )

    shipment = {
        "invoice": {
            "invoice_number": "INV-API-MATCH",
            "consignee": "Test Imports",
            "items": [
                {
                    "description": "API Matching Test Product",
                    "product_code": product_code,
                    "quantity": 1,
                }
            ],
        },
        "packing_list": {
            "invoice_number": "INV-API-MATCH",
            "consignee": "Test Imports",
        },
        "air_waybill": {
            "consignee": "Test Imports",
        },
    }

    try:
        response = client.post(
            "/shipments/verify-extracted",
            json=shipment,
        )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(
                get_current_employee, None
            )
        else:
            app.dependency_overrides[
                get_current_employee
            ] = previous_override

    assert response.status_code == 200

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
def test_verify_extracted_excludes_pending_nmra_evidence(
    client,
    test_db,
):
    unique_id = uuid4().hex[:12].upper()
    product_code = f"API{unique_id}"
    d_number = f"TEST-API-{unique_id}"

    registration = NMRARegistration(
        d_number=d_number,
        product_name="API Matching Test Product",
    )
    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="api-test-approved.pdf",
        storage_key=f"api-test-{unique_id}.pdf",
        version=1,
        review_status="PENDING",
        approved_at=None,
        approved_by=None,
    )
    test_db.add(attachment)
    test_db.flush()

    item = NMRAAttachmentItem(
        attachment_id=attachment.id,
        item_code=product_code,
        product_description="API Matching Test Product",
        page_number=2,
        row_number=3,
        review_status="REVIEWED",
    )
    test_db.add(item)
    test_db.flush()

    test_employee = EmployeeUser(
        id=999997,
        email="nmra-match-test@example.com",
        full_name="NMRA Matching Test Employee",
        role="ADMIN",
        is_active=True,
        password_hash="test-only-not-a-real-password",
    )

    previous_override = app.dependency_overrides.get(
        get_current_employee
    )
    app.dependency_overrides[get_current_employee] = (
        lambda: test_employee
    )

    shipment = {
        "invoice": {
            "invoice_number": "INV-API-MATCH",
            "consignee": "Test Imports",
            "items": [
                {
                    "description": "API Matching Test Product",
                    "product_code": product_code,
                    "quantity": 1,
                }
            ],
        },
        "packing_list": {
            "invoice_number": "INV-API-MATCH",
            "consignee": "Test Imports",
        },
        "air_waybill": {
            "consignee": "Test Imports",
        },
    }

    try:
        response = client.post(
            "/shipments/verify-extracted",
            json=shipment,
        )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(
                get_current_employee, None
            )
        else:
            app.dependency_overrides[
                get_current_employee
            ] = previous_override

    assert response.status_code == 200

    data = response.json()
    matches = data["nmra_matches"]

    assert len(matches) == 1
    assert matches[0]["product_code"] == product_code
    assert matches[0]["status"] == "NO_MATCH"

    assert matches[0]["evidence"] == []
    findings = {
        finding["rule_code"]: finding
        for finding in data["findings"]
    }

    assert findings["REG-001"]["status"] == "NOT_VERIFIED"

def test_verify_extracted_detects_ambiguous_nmra_evidence(
    client,
    test_db,
):
    unique_id = uuid4().hex[:12].upper()
    product_code = f"AMB{unique_id}"

    registration_numbers = [
        f"TEST-AMB-A-{unique_id}",
        f"TEST-AMB-B-{unique_id}",
    ]

    for index, d_number in enumerate(registration_numbers):
        registration = NMRARegistration(
            d_number=d_number,
            product_name="Ambiguous Test Product",
        )
        test_db.add(registration)
        test_db.flush()

        attachment = NMRAAttachment(
            registration_id=registration.id,
            filename=f"ambiguous-{index}.pdf",
            storage_key=f"ambiguous-{unique_id}-{index}.pdf",
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
            product_description="Ambiguous Test Product",
            page_number=1,
            row_number=index + 1,
            review_status="REVIEWED",
        )
        test_db.add(item)
        test_db.flush()

    test_employee = EmployeeUser(
        id=999996,
        email="nmra-ambiguity-test@example.com",
        full_name="NMRA Ambiguity Test Employee",
        role="ADMIN",
        is_active=True,
        password_hash="test-only-not-a-real-password",
    )

    previous_override = app.dependency_overrides.get(
        get_current_employee
    )
    app.dependency_overrides[get_current_employee] = (
        lambda: test_employee
    )

    shipment = {
        "invoice": {
            "invoice_number": "INV-API-AMBIGUOUS",
            "consignee": "Test Imports",
            "items": [
                {
                    "description": "Ambiguous Test Product",
                    "product_code": product_code,
                    "quantity": 1,
                }
            ],
        },
        "packing_list": {
            "invoice_number": "INV-API-AMBIGUOUS",
            "consignee": "Test Imports",
        },
        "air_waybill": {
            "consignee": "Test Imports",
        },
    }

    try:
        response = client.post(
            "/shipments/verify-extracted",
            json=shipment,
        )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(
                get_current_employee, None
            )
        else:
            app.dependency_overrides[
                get_current_employee
            ] = previous_override

    assert response.status_code == 200

    data = response.json()
    matches = data["nmra_matches"]

    assert len(matches) == 1
    assert matches[0]["product_code"] == product_code
    assert matches[0]["status"] == "AMBIGUOUS"

    evidence = matches[0]["evidence"]

    assert len(evidence) == 2
    assert {
        record["d_number"]
        for record in evidence
    } == set(registration_numbers)

    findings = {
        finding["rule_code"]: finding
        for finding in data["findings"]
    }

    assert findings["REG-001"]["status"] == "NOT_VERIFIED"

