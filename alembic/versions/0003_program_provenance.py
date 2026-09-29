"""Program provenance for the official-data collector

Revision ID: 0003_provenance
Revises: 0002_eligibility
Create Date: 2026-09-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0003_provenance'
down_revision: Union[str, None] = '0002_eligibility'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('support_programs', sa.Column('source', sa.String(length=50), nullable=True))
    op.add_column('support_programs', sa.Column('external_id', sa.String(length=255), nullable=True))
    op.add_column('support_programs', sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column('support_programs', sa.Column('is_relevant', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.add_column('support_programs', sa.Column('ends_at', sa.Date(), nullable=True))
    op.add_column('support_programs', sa.Column('content_hash', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_support_programs_is_active'), 'support_programs', ['is_active'], unique=False)
    op.create_unique_constraint(
        'uq_support_programs_source_external', 'support_programs', ['source', 'external_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_support_programs_source_external', 'support_programs', type_='unique')
    op.drop_index(op.f('ix_support_programs_is_active'), table_name='support_programs')
    op.drop_column('support_programs', 'content_hash')
    op.drop_column('support_programs', 'ends_at')
    op.drop_column('support_programs', 'is_relevant')
    op.drop_column('support_programs', 'is_active')
    op.drop_column('support_programs', 'external_id')
    op.drop_column('support_programs', 'source')
