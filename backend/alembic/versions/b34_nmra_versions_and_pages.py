
"""Add NMRA certificate versions and searchable PDF pages."""

from alembic import op
import sqlalchemy as sa


revision = "b34_nmra_versions_and_pages"
down_revision = "0aecc95254bf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "nmra_certificate_versions",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "registration_id",
            sa.Integer(),
            sa.ForeignKey("nmra_registrations.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column(
            "storage_key",
            sa.String(1024),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "review_status",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "registration_id",
            "version",
            name="uq_nmra_certificate_registration_version",
        ),
    )

    op.create_index(
        "ix_nmra_certificate_versions_registration_id",
        "nmra_certificate_versions",
        ["registration_id"],
    )

    op.create_table(
        "nmra_document_pages",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "certificate_version_id",
            sa.Integer(),
            sa.ForeignKey("nmra_certificate_versions.id"),
            nullable=True,
        ),
        sa.Column(
            "attachment_id",
            sa.Integer(),
            sa.ForeignKey("nmra_attachments.id"),
            nullable=True,
        ),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column(
            "extraction_method",
            sa.String(30),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "certificate_version_id",
            "page_number",
            name="uq_nmra_certificate_page",
        ),
        sa.UniqueConstraint(
            "attachment_id",
            "page_number",
            name="uq_nmra_attachment_page",
        ),
        sa.CheckConstraint(
            "(certificate_version_id IS NOT NULL AND "
            "attachment_id IS NULL) OR "
            "(certificate_version_id IS NULL AND "
            "attachment_id IS NOT NULL)",
            name="ck_nmra_document_page_one_parent",
        ),
        sa.CheckConstraint(
            "page_number > 0",
            name="ck_nmra_document_page_positive_number",
        ),
    )

    op.create_index(
        "ix_nmra_document_pages_certificate_version_id",
        "nmra_document_pages",
        ["certificate_version_id"],
    )

    op.create_index(
        "ix_nmra_document_pages_attachment_id",
        "nmra_document_pages",
        ["attachment_id"],
    )


def downgrade():
    op.drop_index(
        "ix_nmra_document_pages_attachment_id",
        table_name="nmra_document_pages",
    )
    op.drop_index(
        "ix_nmra_document_pages_certificate_version_id",
        table_name="nmra_document_pages",
    )
    op.drop_table("nmra_document_pages")

    op.drop_index(
        "ix_nmra_certificate_versions_registration_id",
        table_name="nmra_certificate_versions",
    )
    op.drop_table("nmra_certificate_versions")
