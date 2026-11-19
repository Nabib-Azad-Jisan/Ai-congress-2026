"""Retain dated price observations and order-time marketplace provenance."""
from alembic import op

from app.district_evidence_schema import ensure_district_evidence_schema

revision = '0008'
down_revision = '0007'


def upgrade():
    ensure_district_evidence_schema(op.get_bind())


def downgrade():
    # Earlier app versions ignore these additive fields. Preserve the price snapshots.
    pass
