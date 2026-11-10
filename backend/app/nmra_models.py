from sqlalchemy import DateTime, Integer, String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from datetime import date, datetime, timezone

class NMRARegistration(Base):
    __tablename__ = "nmra_registrations"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    d_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False
    )

    product_name: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    registration_expiry: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    import_licence_expiry: Mapped[date | None] = mapped_column(
        Date,
        nullable=True
    )

    certificate_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class NMRAProductMapping(Base):
    __tablename__ = "nmra_product_mappings"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    client_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    item_code: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    product_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    d_number: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("nmra_registrations.d_number"),
        nullable=False
    )

    source_file: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    source_row: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

class NMRAAttachment(Base):
    __tablename__ = "nmra_attachments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    registration_id: Mapped[int] = mapped_column(
        ForeignKey("nmra_registrations.id"),
        nullable=False
    )

    filename: Mapped[str] = mapped_column(
        String(500),
        nullable=False
    )

    storage_key: Mapped[str] = mapped_column(
        String(1024),
        unique=True,
        nullable=False
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    review_status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    approved_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

class NMRAAttachmentItem(Base):
    __tablename__ = "nmra_attachment_items"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    attachment_id: Mapped[int] = mapped_column(
        ForeignKey("nmra_attachments.id"),
        nullable=False
    )

    item_code: Mapped[str] = mapped_column(
        String(150),
        nullable=False
    )

    product_description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    row_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    evidence_text: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True
    )

    extraction_method: Mapped[str] = mapped_column(
        String(30),
        default="OCR",
        nullable=False
    )

    review_status: Mapped[str] = mapped_column(
        String(30),
        default="UNREVIEWED",
        nullable=False
    )

class NMRAItemReviewAudit(Base):
    __tablename__ = "nmra_item_review_audit"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    item_id: Mapped[int] = mapped_column(
        ForeignKey("nmra_attachment_items.id"),
        nullable=False,
    )

    reviewed_by: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    previous_values: Mapped[str] = mapped_column(
        String(4000),
        nullable=False,
    )

    new_values: Mapped[str] = mapped_column(
        String(4000),
        nullable=False,
    )

    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class EmployeeUser(Base):
    __tablename__ = "employee_users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )

    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="REVIEWER",
    )

    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
