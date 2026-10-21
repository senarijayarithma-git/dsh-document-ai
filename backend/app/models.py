from datetime import datetime, timezone
from sqlalchemy import ForeignKey, String, DateTime, Integer, Text, UniqueConstraint, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

class Base(DeclarativeBase):
    pass

class Client(Base):
    __tablename__ = 'clients'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    reference_code: Mapped[str] = mapped_column(String(80), unique=True)

class Shipment(Base):
    __tablename__ = 'shipments'
    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.id'))
    reference: Mapped[str] = mapped_column(String(120), unique=True)
    status: Mapped[str] = mapped_column(String(40), default='REVIEW')

class EmailMessage(Base):
    __tablename__ = 'email_messages'
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey('shipments.id'))
    provider_message_id: Mapped[str] = mapped_column(String(512), unique=True)
    sender: Mapped[str | None] = mapped_column(String(320))
    subject: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Document(Base):
    __tablename__ = 'documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey('shipments.id'))
    email_message_id: Mapped[int | None] = mapped_column(ForeignKey('email_messages.id'))
    filename: Mapped[str] = mapped_column(String(512))
    storage_key: Mapped[str] = mapped_column(String(1024), unique=True)
    sha256: Mapped[str] = mapped_column(String(64))
    document_type: Mapped[str] = mapped_column(String(80), default='unknown')
    version: Mapped[int] = mapped_column(Integer, default=1)
    extracted_json: Mapped[dict | None] = mapped_column(JSONB)

class ExtractedField(Base):
    __tablename__ = 'extracted_fields'
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id'))
    field_name: Mapped[str] = mapped_column(String(128))
    value_json: Mapped[dict] = mapped_column(JSONB)
    page_number: Mapped[int] = mapped_column(Integer)
    evidence_text: Mapped[str | None] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(String(40), default='UNREVIEWED')

class ValidationRun(Base):
    __tablename__ = 'validation_runs'
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey('shipments.id'))
    ruleset_version: Mapped[str] = mapped_column(String(50))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ValidationFinding(Base):
    __tablename__ = 'validation_findings'
    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('validation_runs.id'))
    rule_code: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[list] = mapped_column(JSONB, default=list)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(255))
    action: Mapped[str] = mapped_column(String(120))
    details: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
