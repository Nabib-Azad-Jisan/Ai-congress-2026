"""Add encrypted private signup identity records."""
from alembic import op

from app.db import SignupIdentity

revision = '0006'
down_revision = '0005'


def upgrade():
    SignupIdentity.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    # Keep encrypted account data if the application is rolled back.
    pass
