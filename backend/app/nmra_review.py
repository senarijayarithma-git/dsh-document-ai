import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth_dependencies import (
    get_current_employee,
    require_nmra_reviewer,
)
from app.auth_schemas import EmployeeProfileResponse
from app.nmra_models import (
    EmployeeUser,
    NMRAAttachment,
    NMRAAttachmentItem,
    NMRAItemReviewAudit,
)

router = APIRouter(
    prefix="/nmra",
    tags=["NMRA Review"],
    dependencies=[Depends(get_current_employee)],
)

class NMRAItemCorrectionRequest(BaseModel):
    item_code: str = Field(min_length=1, max_length=150)
    product_description: str | None = Field(default=None, max_length=500)
    page_number: int = Field(ge=1)
    row_number: int | None = Field(default=None, ge=1)
    correction_reason: str = Field(min_length=10, max_length=1000)

    @field_validator("item_code")
    @classmethod
    def validate_item_code(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError("Item code cannot be blank.")

        return value

    @field_validator("correction_reason")
    @classmethod
    def validate_correction_reason(cls, value: str) -> str:
        value = value.strip()

        if len(value) < 10:
            raise ValueError(
                "Correction reason must contain at least 10 characters."
            )

        return value

@router.get("/attachments/{attachment_id}/items")
def get_attachment_items(
    attachment_id: int,
    db: Session = Depends(get_db),
):
    attachment = db.get(NMRAAttachment, attachment_id)

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA attachment not found.",
        )

    items = db.scalars(
        select(NMRAAttachmentItem)
        .where(
            NMRAAttachmentItem.attachment_id == attachment_id
        )
        .order_by(
            NMRAAttachmentItem.page_number,
            NMRAAttachmentItem.row_number,
            NMRAAttachmentItem.id,
        )
    ).all()

    return {
        "attachment_id": attachment.id,
        "filename": attachment.filename,
        "version": attachment.version,
        "review_status": attachment.review_status,
        "total_items": len(items),
        "items": [
            {
                "id": item.id,
                "item_code": item.item_code,
                "product_description": item.product_description,
                "page_number": item.page_number,
                "row_number": item.row_number,
                "evidence_text": item.evidence_text,
                "extraction_method": item.extraction_method,
                "review_status": item.review_status,
            }
            for item in items
        ],
    }

@router.get("/attachments/{attachment_id}/review-summary")
def get_attachment_review_summary(
    attachment_id: int,
    db: Session = Depends(get_db),
):
    attachment = db.get(NMRAAttachment, attachment_id)

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA attachment not found.",
        )

    items = db.scalars(
        select(NMRAAttachmentItem).where(
            NMRAAttachmentItem.attachment_id == attachment_id
        )
    ).all()

    return {
        "attachment_id": attachment.id,
        "filename": attachment.filename,
        "attachment_status": attachment.review_status,
        "total_candidates": len(items),
        "unreviewed": sum(
            item.review_status == "UNREVIEWED"
            for item in items
        ),
        "reviewed": sum(
            item.review_status == "REVIEWED"
            for item in items
        ),
        "missing_row_numbers": sum(
            item.row_number is None
            for item in items
        ),
        "approved": attachment.review_status == "APPROVED",
    }

@router.get("/attachments/{attachment_id}/items/{item_id}")
def get_attachment_item(
    attachment_id: int,
    item_id: int,
    db: Session = Depends(get_db),
):
    attachment = db.get(NMRAAttachment, attachment_id)

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA attachment not found.",
        )

    item = db.scalar(
        select(NMRAAttachmentItem).where(
            NMRAAttachmentItem.id == item_id,
            NMRAAttachmentItem.attachment_id == attachment_id,
        )
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA attachment item not found.",
        )

    return {
        "id": item.id,
        "attachment_id": item.attachment_id,
        "item_code": item.item_code,
        "product_description": item.product_description,
        "page_number": item.page_number,
        "row_number": item.row_number,
        "evidence_text": item.evidence_text,
        "extraction_method": item.extraction_method,
        "review_status": item.review_status,
    }

@router.patch(
    "/attachments/{attachment_id}/items/{item_id}",
)
def correct_nmra_item(
    attachment_id: int,
    item_id: int,
    request: NMRAItemCorrectionRequest,
    db: Session = Depends(get_db),
    employee: EmployeeUser = Depends(require_nmra_reviewer),
):
    # Lock the attachment so concurrent corrections and
    # approval operations can be coordinated safely.
    attachment = db.scalar(
        select(NMRAAttachment)
        .where(NMRAAttachment.id == attachment_id)
        .with_for_update()
    )

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA attachment not found.",
        )

    if attachment.review_status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="Only PENDING attachments can be corrected.",
        )

    item = db.scalar(
        select(NMRAAttachmentItem)
        .where(
            NMRAAttachmentItem.id == item_id,
            NMRAAttachmentItem.attachment_id == attachment_id,
        )
        .with_for_update()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA item not found in this attachment.",
        )

    previous_values = {
        "item_code": item.item_code,
        "product_description": item.product_description,
        "page_number": item.page_number,
        "row_number": item.row_number,
        "review_status": item.review_status,
    }

    item.item_code = request.item_code.strip().upper()
    item.product_description = (
        request.product_description.strip()
        if request.product_description is not None
        else None
    )
    item.page_number = request.page_number
    item.row_number = request.row_number
    item.review_status = "REVIEWED"

    new_values = {
        "item_code": item.item_code,
        "product_description": item.product_description,
        "page_number": item.page_number,
        "row_number": item.row_number,
        "review_status": item.review_status,
        "correction_reason": request.correction_reason.strip(),
    }

    audit = NMRAItemReviewAudit(
        item_id=item.id,
        reviewed_by=str(employee.id),
        action="CORRECT_ITEM",
        previous_values=json.dumps(previous_values),
        new_values=json.dumps(new_values),
    )

    db.add(audit)
    db.commit()
    db.refresh(item)

    return {
        "message": "NMRA item correction saved.",
        "item_id": item.id,
        "attachment_id": attachment_id,
        "review_status": item.review_status,
        "reviewed_by_employee_id": employee.id,
        "audit_id": audit.id,
    }

@router.post(
    "/attachments/{attachment_id}/items/{item_id}/verify",
)
def verify_nmra_item(
    attachment_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    employee: EmployeeUser = Depends(require_nmra_reviewer),
):
    # Lock the attachment to coordinate with corrections
    # and future approval operations.
    attachment = db.scalar(
        select(NMRAAttachment)
        .where(NMRAAttachment.id == attachment_id)
        .with_for_update()
    )

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA attachment not found.",
        )

    if attachment.review_status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="Only PENDING attachments can be reviewed.",
        )

    item = db.scalar(
        select(NMRAAttachmentItem)
        .where(
            NMRAAttachmentItem.id == item_id,
            NMRAAttachmentItem.attachment_id == attachment_id,
        )
        .with_for_update()
    )

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA item not found in this attachment.",
        )

    if item.review_status != "UNREVIEWED":
        raise HTTPException(
            status_code=409,
            detail="This item has already been reviewed.",
        )

    previous_values = {
        "item_code": item.item_code,
        "product_description": item.product_description,
        "page_number": item.page_number,
        "row_number": item.row_number,
        "review_status": item.review_status,
    }

    item.review_status = "REVIEWED"

    new_values = {
        **previous_values,
        "review_status": "REVIEWED",
    }

    audit = NMRAItemReviewAudit(
        item_id=item.id,
        reviewed_by=str(employee.id),
        action="VERIFY_ITEM",
        previous_values=json.dumps(previous_values),
        new_values=json.dumps(new_values),
    )

    db.add(audit)
    db.commit()
    db.refresh(item)

    return {
        "message": "NMRA item verified successfully.",
        "item_id": item.id,
        "attachment_id": attachment_id,
        "review_status": item.review_status,
        "reviewed_by_employee_id": employee.id,
        "audit_id": audit.id,
    }

@router.post("/attachments/{attachment_id}/approve")
def approve_nmra_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    employee: EmployeeUser = Depends(require_nmra_reviewer),
):
    # Lock the attachment to coordinate approval with
    # concurrent item corrections and verifications.
    attachment = db.scalar(
        select(NMRAAttachment)
        .where(NMRAAttachment.id == attachment_id)
        .with_for_update()
    )

    if attachment is None:
        raise HTTPException(
            status_code=404,
            detail="NMRA attachment not found.",
        )

    if attachment.review_status != "PENDING":
        raise HTTPException(
            status_code=409,
            detail="Only PENDING attachments can be approved.",
        )

    items = db.scalars(
        select(NMRAAttachmentItem)
        .where(
            NMRAAttachmentItem.attachment_id == attachment_id
        )
        .order_by(NMRAAttachmentItem.id)
    ).all()

    if not items:
        raise HTTPException(
            status_code=409,
            detail="Cannot approve an attachment with no item candidates.",
        )

    unreviewed = [
        item.id
        for item in items
        if item.review_status != "REVIEWED"
    ]

    if unreviewed:
        raise HTTPException(
            status_code=409,
            detail=(
                "All item candidates must be reviewed before approval. "
                f"Unreviewed item IDs: {unreviewed[:20]}"
            ),
        )

    invalid_rows = [
        item.id
        for item in items
        if item.row_number is None or item.row_number < 1
    ]

    if invalid_rows:
        raise HTTPException(
            status_code=409,
            detail=(
                "All item candidates must have valid row numbers. "
                f"Invalid item IDs: {invalid_rows[:20]}"
            ),
        )

    attachment.review_status = "APPROVED"
    attachment.approved_at = datetime.now(timezone.utc)
    attachment.approved_by = str(employee.id)

    db.commit()
    db.refresh(attachment)

    return {
        "message": "NMRA attachment approved successfully.",
        "attachment_id": attachment.id,
        "review_status": attachment.review_status,
        "approved_at": attachment.approved_at,
        "approved_by_employee_id": employee.id,
        "total_approved_items": len(items),
    }
