def match_product_code(
    invoice_code: str | None,
    nmra_codes: list[str],
) -> str:
    """Compare an invoice product code with supplied NMRA codes."""

    if not invoice_code or not invoice_code.strip():
        return "INSUFFICIENT_DATA"

    normalized_invoice_code = invoice_code.strip().casefold()

    matching_codes = [
        code
        for code in nmra_codes
        if code and code.strip().casefold() == normalized_invoice_code
    ]

    if len(matching_codes) == 0:
        return "NO_MATCH"

    if len(matching_codes) > 1:
        return "AMBIGUOUS"

    return "MATCHED"

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.nmra_models import NMRAAttachment, NMRAAttachmentItem


def get_approved_nmra_codes(db: Session) -> list[str]:
    """Retrieve item codes from approved NMRA attachments only."""

    statement = (
        select(NMRAAttachmentItem.item_code)
        .join(
            NMRAAttachment,
            NMRAAttachmentItem.attachment_id == NMRAAttachment.id,
        )
        .where(
            NMRAAttachment.review_status == "APPROVED",
            NMRAAttachment.approved_at.is_not(None),
            NMRAAttachmentItem.review_status == "REVIEWED",
            NMRAAttachmentItem.row_number.is_not(None),
            NMRAAttachmentItem.row_number > 0,
        )
    )

    return list(db.scalars(statement).all())

from app.nmra_models import NMRARegistration


def get_approved_nmra_item_records(
    db: Session,
) -> list[dict]:
    """Return approved NMRA items with source provenance."""

    statement = (
        select(
            NMRAAttachmentItem.item_code,
            NMRARegistration.d_number,
            NMRAAttachment.id.label("attachment_id"),
            NMRAAttachmentItem.page_number,
            NMRAAttachmentItem.row_number,
        )
        .join(
            NMRAAttachment,
            NMRAAttachmentItem.attachment_id == NMRAAttachment.id,
        )
        .join(
            NMRARegistration,
            NMRAAttachment.registration_id == NMRARegistration.id,
        )
        .where(
            NMRAAttachment.review_status == "APPROVED",
            NMRAAttachment.approved_at.is_not(None),
            NMRAAttachmentItem.review_status == "REVIEWED",
            NMRAAttachmentItem.row_number.is_not(None),
            NMRAAttachmentItem.row_number > 0,
        )
    )

    return [
        dict(row)
        for row in db.execute(statement).mappings().all()
    ]


def match_product_code_with_evidence(
    invoice_code: str | None,
    approved_records: list[dict],
) -> dict:
    """Match a product code using approved NMRA evidence."""

    if not invoice_code or not invoice_code.strip():
        return {
            "status": "INSUFFICIENT_DATA",
            "evidence": [],
        }

    normalized_code = invoice_code.strip().casefold()

    matches = [
        record
        for record in approved_records
        if isinstance(record.get("item_code"), str)
        and record["item_code"].strip().casefold()
        == normalized_code
    ]

    if not matches:
        return {
            "status": "NO_MATCH",
            "evidence": [],
        }

    # Every matching record must identify its registration.
    if any(
        not isinstance(record.get("d_number"), str)
        or not record["d_number"].strip()
        for record in matches
    ):
        return {
            "status": "INSUFFICIENT_DATA",
            "evidence": matches,
        }

    registration_numbers = {
        record["d_number"].strip().casefold()
        for record in matches
    }

    status = (
        "MATCHED"
        if len(registration_numbers) == 1
        else "AMBIGUOUS"
    )

    return {
        "status": status,
        "evidence": matches,
    }
