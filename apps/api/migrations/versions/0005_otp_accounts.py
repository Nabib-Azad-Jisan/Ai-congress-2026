"""Add verified-contact account fields and keep existing sellers on the farmer role."""
from alembic import op

from app.db import ensure_otp_schema

revision = '0005'
down_revision = '0004'


def upgrade():
    ensure_otp_schema(op.get_bind())


def downgrade():
    # Earlier app versions can safely read a database with the additive profile fields.
    pass
