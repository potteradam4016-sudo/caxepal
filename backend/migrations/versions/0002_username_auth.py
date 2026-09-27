"""Convert existing accounts to username sign-in and remove action tokens.

Revision ID: 0002
Revises: 0001
"""
import re
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    # New databases already receive the username schema from 0001.
    if "email" not in columns:
        return
    rows = bind.execute(sa.text("SELECT id, email FROM users ORDER BY id")).all()
    used = set()
    converted = []
    for user_id, old_address in rows:
        candidate = old_address.split("@", 1)[0].strip().casefold()
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,31}", candidate) or candidate in used:
            candidate = "user_" + user_id.replace("-", "")[:24]
        used.add(candidate)
        converted.append((user_id, candidate))
    op.rename_table("auth_tokens", "obsolete_auth_tokens") if "auth_tokens" in inspector.get_table_names() else None
    op.execute("ALTER TABLE users RENAME COLUMN email TO username")
    for user_id, username in converted:
        bind.execute(sa.text("UPDATE users SET username=:username WHERE id=:id"),
                     {"username": username, "id": user_id})
    op.drop_column("users", "email_verified")
    if "auth_tokens" in inspector.get_table_names():
        op.drop_table("obsolete_auth_tokens")


def downgrade():
    raise RuntimeError("Username conversion removes contact addresses and cannot be reversed.")
