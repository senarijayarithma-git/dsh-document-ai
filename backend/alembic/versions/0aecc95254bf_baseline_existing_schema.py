"""Initial DSH Document AI database schema."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0aecc95254bf"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all seven application tables."""
    op.create_table('documents',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('document_type', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('extracted_data', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('employee_users',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=False),
    sa.Column('password_hash', sa.String(length=500), nullable=False),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('nmra_registrations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('d_number', sa.String(length=100), nullable=False),
    sa.Column('product_name', sa.String(length=500), nullable=True),
    sa.Column('registration_expiry', sa.Date(), nullable=True),
    sa.Column('import_licence_expiry', sa.Date(), nullable=True),
    sa.Column('certificate_filename', sa.String(length=500), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('d_number')
    )
    op.create_table('nmra_attachments',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('registration_id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=500), nullable=False),
    sa.Column('storage_key', sa.String(length=1024), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('review_status', sa.String(length=30), nullable=False),
    sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('approved_by', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['registration_id'], ['nmra_registrations.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('storage_key')
    )
    op.create_table('nmra_product_mappings',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('client_id', sa.Integer(), nullable=True),
    sa.Column('item_code', sa.String(length=150), nullable=False),
    sa.Column('product_description', sa.String(length=500), nullable=True),
    sa.Column('d_number', sa.String(length=100), nullable=False),
    sa.Column('source_file', sa.String(length=500), nullable=True),
    sa.Column('source_row', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['d_number'], ['nmra_registrations.d_number'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('nmra_attachment_items',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('attachment_id', sa.Integer(), nullable=False),
    sa.Column('item_code', sa.String(length=150), nullable=False),
    sa.Column('product_description', sa.String(length=500), nullable=True),
    sa.Column('page_number', sa.Integer(), nullable=False),
    sa.Column('row_number', sa.Integer(), nullable=True),
    sa.Column('evidence_text', sa.String(length=1000), nullable=True),
    sa.Column('extraction_method', sa.String(length=30), nullable=False),
    sa.Column('review_status', sa.String(length=30), nullable=False),
    sa.ForeignKeyConstraint(['attachment_id'], ['nmra_attachments.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('nmra_item_review_audit',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('item_id', sa.Integer(), nullable=False),
    sa.Column('reviewed_by', sa.String(length=255), nullable=False),
    sa.Column('action', sa.String(length=50), nullable=False),
    sa.Column('previous_values', sa.String(length=4000), nullable=False),
    sa.Column('new_values', sa.String(length=4000), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['item_id'], ['nmra_attachment_items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )



def downgrade() -> None:
    """Remove tables in reverse dependency order."""
    op.drop_table("nmra_item_review_audit")
    op.drop_table("nmra_attachment_items")
    op.drop_table("nmra_product_mappings")
    op.drop_table("nmra_attachments")
    op.drop_table("nmra_registrations")
    op.drop_table("employee_users")
    op.drop_table("documents")
