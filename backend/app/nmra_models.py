from sqlalchemy import DateTime, Integer, String, Date, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from datetime import date, datetime, timezone
from sqlalchemy import CheckConstraint
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

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
    certificate_version_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("nmra_certificate_versions.id"),
        nullable=True,
        index=True,
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

class NMRACertificateVersion(Base):
    __tablename__ = "nmra_certificate_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    registration_id = Column(
        Integer,
        ForeignKey("nmra_registrations.id"),
        nullable=False,
        index=True,
    )

    version = Column(Integer, nullable=False)

    filename = Column(String(500), nullable=False)

    storage_key = Column(
        String(1024),
        nullable=False,
        unique=True,
    )

    review_status = Column(
        String(30),
        nullable=False,
        default="PENDING",
    )

    uploaded_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "registration_id",
            "version",
            name="uq_nmra_certificate_registration_version",
        ),
    )


class NMRADocumentPage(Base):
    __tablename__ = "nmra_document_pages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    certificate_version_id = Column(
        Integer,
        ForeignKey("nmra_certificate_versions.id"),
        nullable=True,
        index=True,
    )

    attachment_id = Column(
        Integer,
        ForeignKey("nmra_attachments.id"),
        nullable=True,
        index=True,
    )

    page_number = Column(Integer, nullable=False)

    extracted_text = Column(Text, nullable=False)

    extraction_method = Column(
        String(30),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "certificate_version_id",
            "page_number",
            name="uq_nmra_certificate_page",
        ),
        UniqueConstraint(
            "attachment_id",
            "page_number",
            name="uq_nmra_attachment_page",
        ),
        CheckConstraint(
            "(certificate_version_id IS NOT NULL AND "
            "attachment_id IS NULL) OR "
            "(certificate_version_id IS NULL AND "
            "attachment_id IS NOT NULL)",
            name="ck_nmra_document_page_one_parent",
        ),
        CheckConstraint(
            "page_number > 0",
            name="ck_nmra_document_page_positive_number",
        ),
    )
