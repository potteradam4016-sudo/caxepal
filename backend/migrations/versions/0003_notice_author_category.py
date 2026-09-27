"""Store representative notice author and publisher category.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("notices", sa.Column("author_name", sa.String(length=100), nullable=True))
    op.add_column("notices", sa.Column("publisher_category", sa.String(length=32),
                                       nullable=False, server_default="other"))
    op.create_index("ix_notices_publisher_category", "notices", ["publisher_category"])


def downgrade():
    op.drop_index("ix_notices_publisher_category", table_name="notices")
    op.drop_column("notices", "publisher_category")
    op.drop_column("notices", "author_name")
