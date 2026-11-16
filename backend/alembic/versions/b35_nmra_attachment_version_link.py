
"""Link NMRA supporting attachments to certificate versions."""

from alembic import op
import sqlalchemy as sa


revision = "b35_nmra_attachment_version_link"
down_revision = "b34_nmra_versions_and_pages"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "nmra_attachments",
        sa.Column(
            "certificate_version_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_nmra_attachment_certificate_version",
        "nmra_attachments",
        "nmra_certificate_versions",
        ["certificate_version_id"],
        ["id"],
    )

    op.create_index(
        "ix_nmra_attachments_certificate_version_id",
        "nmra_attachments",
        ["certificate_version_id"],
    )


def downgrade():
    op.drop_index(
        "ix_nmra_attachments_certificate_version_id",
        table_name="nmra_attachments",
    )

    op.drop_constraint(
        "fk_nmra_attachment_certificate_version",
        "nmra_attachments",
        type_="foreignkey",
    )

    op.drop_column(
        "nmra_attachments",
        "certificate_version_id",
    )
