from app.nmra_matching import match_product_code


def test_matching_product_codes():
    result = match_product_code(
        "BLT00001",
        ["BLT00001", "XSYS0001"],
    )

    assert result == "MATCHED"


def test_product_code_matching_ignores_case_and_outer_spaces():
    result = match_product_code(
        " blt00001 ",
        ["BLT00001"],
    )

    assert result == "MATCHED"


def test_nonmatching_product_code():
    result = match_product_code(
        "UNKNOWN123",
        ["BLT00001", "XSYS0001"],
    )

    assert result == "NO_MATCH"


def test_missing_invoice_product_code():
    result = match_product_code(
        None,
        ["BLT00001"],
    )

    assert result == "INSUFFICIENT_DATA"


def test_duplicate_matching_codes_are_ambiguous():
    result = match_product_code(
        "BLT00001",
        ["BLT00001", "blt00001"],
    )

    assert result == "AMBIGUOUS"

from sqlalchemy import inspect


def test_nmra_tables_exist_in_test_database(verified_test_engine):
    inspector = inspect(verified_test_engine)

    required_tables = {
        "nmra_registrations",
        "nmra_attachments",
        "nmra_attachment_items",
    }

    existing_tables = set(inspector.get_table_names())

    assert required_tables.issubset(existing_tables), (
        f"Missing NMRA test tables: "
        f"{sorted(required_tables - existing_tables)}"
    )

from datetime import datetime, timezone
from uuid import uuid4

from app.nmra_matching import get_approved_nmra_codes
from app.nmra_models import (
    NMRARegistration,
    NMRAAttachment,
    NMRAAttachmentItem,
)


def test_approved_reviewed_item_is_retrieved(test_db):
    unique_id = uuid4().hex[:12].upper()
    item_code = f"TEST{unique_id}"

    registration = NMRARegistration(
        d_number=f"TEST-REG-{unique_id}",
        product_name="Automated Test Product",
    )

    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="test-approved.pdf",
        storage_key=f"test-{unique_id}.pdf",
        version=1,
        review_status="APPROVED",
        approved_at=datetime.now(timezone.utc),
        approved_by="pytest",
    )

    test_db.add(attachment)
    test_db.flush()

    item = NMRAAttachmentItem(
        attachment_id=attachment.id,
        item_code=item_code,
        product_description="Automated Test Product",
        page_number=1,
        row_number=1,
        review_status="REVIEWED",
    )

    test_db.add(item)
    test_db.flush()

    approved_codes = get_approved_nmra_codes(test_db)

    assert item_code in approved_codes

import pytest


@pytest.mark.parametrize(
    "attachment_status,approved, item_status,row_number",
    [
        ("PENDING", False, "REVIEWED", 1),
        ("APPROVED", True, "UNREVIEWED", 1),
        ("APPROVED", True, "REVIEWED", None),
        ("APPROVED", True, "REVIEWED", 0),
    ],
)
def test_ineligible_nmra_items_are_excluded(
    test_db,
    attachment_status,
    approved,
    item_status,
    row_number,
):
    unique_id = uuid4().hex[:12].upper()
    item_code = f"TEST{unique_id}"

    registration = NMRARegistration(
        d_number=f"TEST-REG-{unique_id}",
        product_name="Test Excluded Product",
    )
    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="test-ineligible.pdf",
        storage_key=f"test-{unique_id}.pdf",
        version=1,
        review_status=attachment_status,
        approved_at=(
            datetime.now(timezone.utc)
            if approved else None
        ),
        approved_by="pytest" if approved else None,
    )
    test_db.add(attachment)
    test_db.flush()

    item = NMRAAttachmentItem(
        attachment_id=attachment.id,
        item_code=item_code,
        product_description="Test Excluded Product",
        page_number=1,
        row_number=row_number,
        review_status=item_status,
    )
    test_db.add(item)
    test_db.flush()

    approved_codes = get_approved_nmra_codes(test_db)

    assert item_code not in approved_codes

from app.nmra_matching import get_approved_nmra_item_records


def test_approved_nmra_records_include_source_evidence(test_db):
    unique_id = uuid4().hex[:12].upper()
    item_code = f"TEST{unique_id}"
    d_number = f"TEST-REG-{unique_id}"

    registration = NMRARegistration(
        d_number=d_number,
        product_name="Evidence Test Product",
    )
    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="test-evidence.pdf",
        storage_key=f"test-evidence-{unique_id}.pdf",
        version=1,
        review_status="APPROVED",
        approved_at=datetime.now(timezone.utc),
        approved_by="pytest",
    )
    test_db.add(attachment)
    test_db.flush()

    item = NMRAAttachmentItem(
        attachment_id=attachment.id,
        item_code=item_code,
        product_description="Evidence Test Product",
        page_number=2,
        row_number=5,
        review_status="REVIEWED",
    )
    test_db.add(item)
    test_db.flush()

    records = get_approved_nmra_item_records(test_db)

    matching_records = [
        record
        for record in records
        if record["item_code"] == item_code
    ]

    assert len(matching_records) == 1

    record = matching_records[0]

    assert record["d_number"] == d_number
    assert record["attachment_id"] == attachment.id
    assert record["page_number"] == 2
    assert record["row_number"] == 5

@pytest.mark.parametrize(
    "attachment_status,approved,item_status,row_number",
    [
        ("PENDING", False, "REVIEWED", 1),
        ("APPROVED", False, "REVIEWED", 1),
        ("APPROVED", True, "UNREVIEWED", 1),
        ("APPROVED", True, "REVIEWED", None),
        ("APPROVED", True, "REVIEWED", 0),
    ],
)
def test_ineligible_nmra_evidence_is_excluded(
    test_db,
    attachment_status,
    approved,
    item_status,
    row_number,
):
    unique_id = uuid4().hex[:12].upper()
    item_code = f"TEST{unique_id}"

    registration = NMRARegistration(
        d_number=f"TEST-REG-{unique_id}",
        product_name="Excluded Evidence Test Product",
    )
    test_db.add(registration)
    test_db.flush()

    attachment = NMRAAttachment(
        registration_id=registration.id,
        filename="test-excluded-evidence.pdf",
        storage_key=f"excluded-evidence-{unique_id}.pdf",
        version=1,
        review_status=attachment_status,
        approved_at=(
            datetime.now(timezone.utc)
            if approved else None
        ),
        approved_by="pytest" if approved else None,
    )
    test_db.add(attachment)
    test_db.flush()

    item = NMRAAttachmentItem(
        attachment_id=attachment.id,
        item_code=item_code,
        product_description="Excluded Evidence Test Product",
        page_number=1,
        row_number=row_number,
        review_status=item_status,
    )
    test_db.add(item)
    test_db.flush()

    records = get_approved_nmra_item_records(test_db)

    assert not any(
        record["item_code"] == item_code
        for record in records
    )

def test_duplicate_code_preserves_both_approved_evidence_records(test_db):
    unique_id = uuid4().hex[:12].upper()
    item_code = f"DUP{unique_id}"

    expected_d_numbers = set()

    for number in (1, 2):
        d_number = f"TEST-DUP-{number}-{unique_id}"
        expected_d_numbers.add(d_number)

        registration = NMRARegistration(
            d_number=d_number,
            product_name=f"Duplicate Test Product {number}",
        )
        test_db.add(registration)
        test_db.flush()

        attachment = NMRAAttachment(
            registration_id=registration.id,
            filename=f"duplicate-{number}.pdf",
            storage_key=f"duplicate-{unique_id}-{number}.pdf",
            version=1,
            review_status="APPROVED",
            approved_at=datetime.now(timezone.utc),
            approved_by="pytest",
        )
        test_db.add(attachment)
        test_db.flush()

        item = NMRAAttachmentItem(
            attachment_id=attachment.id,
            item_code=item_code,
            product_description="Duplicate Test Product",
            page_number=number,
            row_number=1,
            review_status="REVIEWED",
        )
        test_db.add(item)
        test_db.flush()

    records = get_approved_nmra_item_records(test_db)

    matching_records = [
        record
        for record in records
        if record["item_code"] == item_code
    ]

    assert len(matching_records) == 2

    assert {
        record["d_number"]
        for record in matching_records
    } == expected_d_numbers

    assert len({
        record["attachment_id"]
        for record in matching_records
    }) == 2

from app.nmra_matching import match_product_code_with_evidence


@pytest.mark.parametrize(
    "invoice_code,records,expected_status,expected_count",
    [
        (
            "BLT00001",
            [{"item_code": "BLT00001", "d_number": "REG-001"}],
            "MATCHED",
            1,
        ),
        (
            " blt00001 ",
            [
                {"item_code": "BLT00001", "d_number": "REG-001"},
                {"item_code": "BLT00001", "d_number": "REG-001"},
            ],
            "MATCHED",
            2,
        ),
        (
            "BLT00001",
            [
                {"item_code": "BLT00001", "d_number": "REG-001"},
                {"item_code": "BLT00001", "d_number": "REG-002"},
            ],
            "AMBIGUOUS",
            2,
        ),
        (
            "UNKNOWN123",
            [{"item_code": "BLT00001", "d_number": "REG-001"}],
            "NO_MATCH",
            0,
        ),
        (
            None,
            [{"item_code": "BLT00001", "d_number": "REG-001"}],
            "INSUFFICIENT_DATA",
            0,
        ),
    ],
)
def test_product_code_matching_with_evidence(
    invoice_code,
    records,
    expected_status,
    expected_count,
):
    result = match_product_code_with_evidence(
        invoice_code,
        records,
    )

    assert result["status"] == expected_status
    assert len(result["evidence"]) == expected_count

@pytest.mark.parametrize(
    "d_number",
    [None, "", "   "],
)
def test_missing_registration_number_is_not_matched(d_number):
    records = [
        {
            "item_code": "BLT00001",
            "d_number": d_number,
        }
    ]

    result = match_product_code_with_evidence(
        "BLT00001",
        records,
    )

    assert result["status"] == "INSUFFICIENT_DATA"
    assert len(result["evidence"]) == 1

