"""Distinguish password signup from contact-verified identity profiles."""
from alembic import op

from app.db import ensure_signup_contact_schema

revision = '0009'
down_revision = '0008'


def upgrade():
    ensure_signup_contact_schema(op.get_bind())


def downgrade():
    # Preserve contact provenance if the application is rolled back.
    pass
