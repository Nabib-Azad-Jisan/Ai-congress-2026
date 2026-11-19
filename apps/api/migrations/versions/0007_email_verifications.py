"""Persist email verification challenges without changing existing accounts."""
from alembic import op
from app.db import EmailVerification

revision = '0007'
down_revision = '0006'


def upgrade():
    EmailVerification.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Preserve auth state when application code is rolled back.
    pass
