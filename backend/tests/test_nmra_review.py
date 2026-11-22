from sqlalchemy import text


def test_database_is_isolated(test_db):
    actual_database = test_db.execute(
        text("SELECT current_database()")
    ).scalar_one()

    assert actual_database == "dsh_document_ai_test"


def test_nmra_review_endpoint_requires_authentication(client):
    response = client.patch(
        "/nmra/attachments/999999/items/999999",
        json={
            "item_code": "TEST-001",
            "product_description": "Test product",
            "page_number": 1,
            "row_number": 1,
            "correction_reason": "Testing authentication requirements",
        },
    )

    assert response.status_code == 401

from fastapi import HTTPException

from app.auth_dependencies import require_nmra_reviewer


def test_admin_can_access_nmra_corrections():
    employee = type(
        "TestEmployee",
        (),
        {"id": 1, "role": "ADMIN"},
    )()

    result = require_nmra_reviewer(employee)

    assert result == employee


def test_reviewer_can_access_nmra_corrections():
    employee = type(
        "TestEmployee",
        (),
        {"id": 2, "role": "REVIEWER"},
    )()

    result = require_nmra_reviewer(employee)

    assert result == employee


def test_viewer_cannot_access_nmra_corrections():
    employee = type(
        "TestEmployee",
        (),
        {"id": 3, "role": "VIEWER"},
    )()

    try:
        require_nmra_reviewer(employee)
    except HTTPException as error:
        assert error.status_code == 403
    else:
        raise AssertionError(
            "VIEWER must not be allowed to correct NMRA items."
        )

import os
import pytest

from app.auth_security import (
    create_access_token,
    hash_password,
)
from app.nmra_models import EmployeeUser


@pytest.fixture
def make_employee(test_db, monkeypatch):
    # Use a test-only JWT secret for these tests.
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


@pytest.fixture
def valid_correction():
    return {
        "item_code": "TEST-ITEM-001",
        "product_description": "Corrected test product",
        "page_number": 1,
        "row_number": 1,
        "correction_reason": "Correcting the item information for testing.",
    }


def test_admin_authenticated_request(
    client,
    make_employee,
):
    employee, headers = make_employee("ADMIN")

    response = client.get(
        "/auth/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee.id
    assert response.json()["role"] == "ADMIN"


def test_reviewer_authenticated_request(
    client,
    make_employee,
):
    employee, headers = make_employee("REVIEWER")

    response = client.get(
        "/auth/me",
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == employee.id
    assert response.json()["role"] == "REVIEWER"


def test_viewer_cannot_correct_nmra_item(
    client,
    make_employee,
    valid_correction,
):
    _, headers = make_employee("VIEWER")

    response = client.patch(
        "/nmra/attachments/999999/items/999999",
        json=valid_correction,
        headers=headers,
    )

    assert response.status_code == 403


def test_invalid_correction_is_rejected(
    client,
    make_employee,
    valid_correction,
):
    _, headers = make_employee("REVIEWER")

    invalid_data = valid_correction.copy()
    invalid_data["correction_reason"] = "short"

    response = client.patch(
        "/nmra/attachments/999999/items/999999",
        json=invalid_data,
        headers=headers,
    )

    assert response.status_code == 422


def test_missing_attachment_returns_404(
    client,
    make_employee,
    valid_correction,
):
    _, headers = make_employee("ADMIN")

    response = client.patch(
        "/nmra/attachments/999999/items/999999",
        json=valid_correction,
        headers=headers,
    )

    assert response.status_code == 404

import json
from uuid import uuid4

from sqlalchemy import select

from app.nmra_models import (
    NMRARegistration,
    NMRAAttachment,
    NMRAAttachmentItem,
    NMRAItemReviewAudit,
)


@pytest.fixture
def nmra_test_item(test_db):
    unique_id = uuid4().hex

    registration = NMRARegistration(
        d_number=f"TEST-{unique_id}",
        product_name="Original test product",
    )
    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="automated-test.pdf",
        storage_key=f"test/{unique_id}.pdf",
        version=1,
        review_status="PENDING",
    )
    test_db.add(attachment)
    test_db.flush()

    item = NMRAAttachmentItem(
        attachment_id=attachment.id,
        item_code="ORIGINAL-001",
        product_description="Original OCR description",
        page_number=2,
        row_number=3,
        evidence_text="Original OCR evidence must remain unchanged.",
        extraction_method="OCR",
        review_status="UNREVIEWED",
    )
    test_db.add(item)
    test_db.flush()

    return registration, attachment, item


@pytest.mark.parametrize("role", ["ADMIN", "REVIEWER"])
def test_authorized_employee_can_correct_item(
    client,
    test_db,
    make_employee,
    valid_correction,
    nmra_test_item,
    role,
):
    employee, headers = make_employee(role)
    _, attachment, item = nmra_test_item

    original_evidence = item.evidence_text
    original_extraction_method = item.extraction_method

    response = client.patch(
        f"/nmra/attachments/{attachment.id}/items/{item.id}",
        json=valid_correction,
        headers=headers,
    )

    assert response.status_code == 200, response.text

    test_db.refresh(item)

    assert item.item_code == "TEST-ITEM-001"
    assert item.product_description == "Corrected test product"
    assert item.page_number == 1
    assert item.row_number == 1
    assert item.review_status == "REVIEWED"

    # The original OCR evidence must never be overwritten.
    assert item.evidence_text == original_evidence
    assert item.extraction_method == original_extraction_method

    # Correcting an item must not approve the attachment.
    test_db.refresh(attachment)
    assert attachment.review_status == "PENDING"

    audits = test_db.scalars(
        select(NMRAItemReviewAudit).where(
            NMRAItemReviewAudit.item_id == item.id
        )
    ).all()

    assert len(audits) == 1

    audit = audits[0]

    assert audit.reviewed_by == str(employee.id)

    previous = json.loads(audit.previous_values)
    updated = json.loads(audit.new_values)

    assert previous["item_code"] == "ORIGINAL-001"
    assert updated["item_code"] == "TEST-ITEM-001"


def test_approved_attachment_cannot_be_corrected(
    client,
    test_db,
    make_employee,
    valid_correction,
    nmra_test_item,
):
    _, headers = make_employee("ADMIN")
    _, attachment, item = nmra_test_item

    attachment.review_status = "APPROVED"
    test_db.flush()

    response = client.patch(
        f"/nmra/attachments/{attachment.id}/items/{item.id}",
        json=valid_correction,
        headers=headers,
    )

    assert response.status_code == 409

    test_db.refresh(item)
    assert item.item_code == "ORIGINAL-001"


def test_viewer_cannot_correct_existing_item(
    client,
    test_db,
    make_employee,
    valid_correction,
    nmra_test_item,
):
    _, headers = make_employee("VIEWER")
    _, attachment, item = nmra_test_item

    response = client.patch(
        f"/nmra/attachments/{attachment.id}/items/{item.id}",
        json=valid_correction,
        headers=headers,
    )

    assert response.status_code == 403

    test_db.refresh(item)
    assert item.item_code == "ORIGINAL-001"

@pytest.mark.parametrize("role", ["ADMIN", "REVIEWER"])
def test_authorized_employee_can_verify_item(
    client,
    test_db,
    make_employee,
    nmra_test_item,
    role,
):
    employee, headers = make_employee(role)
    _, attachment, item = nmra_test_item

    original_code = item.item_code
    original_evidence = item.evidence_text
    original_description = item.product_description

    response = client.post(
        f"/nmra/attachments/{attachment.id}/items/{item.id}/verify",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["review_status"] == "REVIEWED"
    assert response.json()["reviewed_by_employee_id"] == employee.id

    test_db.refresh(item)
    test_db.refresh(attachment)

    assert item.review_status == "REVIEWED"
    assert item.item_code == original_code
    assert item.evidence_text == original_evidence
    assert item.product_description == original_description
    assert attachment.review_status == "PENDING"

    audits = test_db.scalars(
        select(NMRAItemReviewAudit).where(
            NMRAItemReviewAudit.item_id == item.id
        )
    ).all()

    assert len(audits) == 1
    assert audits[0].action == "VERIFY_ITEM"
    assert audits[0].reviewed_by == str(employee.id)

    previous = json.loads(audits[0].previous_values)
    updated = json.loads(audits[0].new_values)

    assert previous["review_status"] == "UNREVIEWED"
    assert updated["review_status"] == "REVIEWED"
    assert previous["item_code"] == updated["item_code"]


def test_viewer_cannot_verify_item(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("VIEWER")
    _, attachment, item = nmra_test_item

    response = client.post(
        f"/nmra/attachments/{attachment.id}/items/{item.id}/verify",
        headers=headers,
    )

    assert response.status_code == 403

    test_db.refresh(item)
    assert item.review_status == "UNREVIEWED"


def test_item_cannot_be_verified_twice(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("REVIEWER")
    _, attachment, item = nmra_test_item

    url = (
        f"/nmra/attachments/{attachment.id}/items/"
        f"{item.id}/verify"
    )

    first = client.post(url, headers=headers)
    assert first.status_code == 200, first.text

    second = client.post(url, headers=headers)
    assert second.status_code == 409

    audits = test_db.scalars(
        select(NMRAItemReviewAudit).where(
            NMRAItemReviewAudit.item_id == item.id
        )
    ).all()

    assert len(audits) == 1


def test_approved_attachment_item_cannot_be_verified(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("ADMIN")
    _, attachment, item = nmra_test_item

    attachment.review_status = "APPROVED"
    test_db.flush()

    response = client.post(
        f"/nmra/attachments/{attachment.id}/items/{item.id}/verify",
        headers=headers,
    )

    assert response.status_code == 409

    test_db.refresh(item)
    assert item.review_status == "UNREVIEWED"

@pytest.mark.parametrize("role", ["ADMIN", "REVIEWER"])
def test_authorized_employee_can_approve_attachment(
    client,
    test_db,
    make_employee,
    nmra_test_item,
    role,
):
    employee, headers = make_employee(role)
    _, attachment, item = nmra_test_item

    item.review_status = "REVIEWED"
    test_db.flush()

    response = client.post(
        f"/nmra/attachments/{attachment.id}/approve",
        headers=headers,
    )

    assert response.status_code == 200, response.text

    data = response.json()
    assert data["review_status"] == "APPROVED"
    assert data["total_approved_items"] == 1
    assert data["approved_by_employee_id"] == employee.id
    assert data["approved_at"] is not None

    test_db.refresh(attachment)

    assert attachment.review_status == "APPROVED"
    assert attachment.approved_by == str(employee.id)
    assert attachment.approved_at is not None


def test_cannot_approve_unreviewed_items(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("REVIEWER")
    _, attachment, item = nmra_test_item

    response = client.post(
        f"/nmra/attachments/{attachment.id}/approve",
        headers=headers,
    )

    assert response.status_code == 409
    assert "reviewed" in response.json()["detail"].lower()

    test_db.refresh(attachment)
    assert attachment.review_status == "PENDING"
    assert attachment.approved_at is None


def test_cannot_approve_missing_row_number(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("REVIEWER")
    _, attachment, item = nmra_test_item

    item.review_status = "REVIEWED"
    item.row_number = None
    test_db.flush()

    response = client.post(
        f"/nmra/attachments/{attachment.id}/approve",
        headers=headers,
    )

    assert response.status_code == 409
    assert "row numbers" in response.json()["detail"].lower()

    test_db.refresh(attachment)
    assert attachment.review_status == "PENDING"


def test_cannot_approve_attachment_without_candidates(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("ADMIN")
    _, attachment, item = nmra_test_item

    test_db.delete(item)
    test_db.flush()

    response = client.post(
        f"/nmra/attachments/{attachment.id}/approve",
        headers=headers,
    )

    assert response.status_code == 409
    assert "no item candidates" in response.json()["detail"].lower()

    test_db.refresh(attachment)
    assert attachment.review_status == "PENDING"


def test_cannot_approve_attachment_twice(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("ADMIN")
    _, attachment, item = nmra_test_item

    item.review_status = "REVIEWED"
    test_db.flush()

    url = f"/nmra/attachments/{attachment.id}/approve"

    first = client.post(url, headers=headers)
    assert first.status_code == 200, first.text

    second = client.post(url, headers=headers)
    assert second.status_code == 409


def test_viewer_cannot_approve_attachment(
    client,
    test_db,
    make_employee,
    nmra_test_item,
):
    _, headers = make_employee("VIEWER")
    _, attachment, item = nmra_test_item

    item.review_status = "REVIEWED"
    test_db.flush()

    response = client.post(
        f"/nmra/attachments/{attachment.id}/approve",
        headers=headers,
    )

    assert response.status_code == 403

    test_db.refresh(attachment)
    assert attachment.review_status == "PENDING"


def test_approval_requires_authentication(
    client,
    nmra_test_item,
):
    _, attachment, _ = nmra_test_item

    response = client.post(
        f"/nmra/attachments/{attachment.id}/approve",
    )

    assert response.status_code == 401
