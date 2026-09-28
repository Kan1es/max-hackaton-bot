"""Program eligibility/presentation fields, array doc_checklist, dedup constraints

Revision ID: 0002_eligibility
Revises: 0001_initial
Create Date: 2026-09-25 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0002_eligibility'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- support_programs: fields that were dropped when the mini-app's
    # catalog was converted to the backend schema, plus the two
    # presentation-only fields the mini-app used to hardcode by index.
    op.add_column('support_programs', sa.Column('short_title', sa.String(length=255), nullable=True))
    op.add_column('support_programs', sa.Column('eligible_status', sa.Text(), nullable=True))
    op.add_column('support_programs', sa.Column('highlight', sa.String(length=255), nullable=True))
    op.add_column('support_programs', sa.Column('checked_at', sa.String(length=32), nullable=True))

    # doc_checklist was JSON while the equally list-shaped `industries` was
    # text[]; unify on text[] so both read back as plain Python lists.
    # Postgres forbids a subquery in ALTER COLUMN ... USING, so the values
    # are converted through a temporary column instead.
    op.add_column('support_programs', sa.Column('doc_checklist_arr', sa.ARRAY(sa.String()), nullable=True))
    op.execute(
        "UPDATE support_programs "
        "SET doc_checklist_arr = ARRAY(SELECT json_array_elements_text(doc_checklist)) "
        "WHERE doc_checklist IS NOT NULL"
    )
    op.drop_column('support_programs', 'doc_checklist')
    op.alter_column('support_programs', 'doc_checklist_arr', new_column_name='doc_checklist')

    # --- applications: checklist progress, so "Мои заявки" is more than a
    # bookmark list and the marks survive a device change.
    op.add_column('applications', sa.Column('checked_docs', sa.ARRAY(sa.String()), nullable=True))

    # --- collapse pre-existing duplicates before the constraints land.
    op.execute(
        "DELETE FROM matches a USING matches b "
        "WHERE a.id < b.id AND a.profile_id = b.profile_id AND a.program_id = b.program_id"
    )
    op.execute(
        "DELETE FROM applications a USING applications b "
        "WHERE a.id < b.id AND a.profile_id = b.profile_id AND a.program_id = b.program_id"
    )
    op.create_unique_constraint(
        'uq_matches_profile_program', 'matches', ['profile_id', 'program_id']
    )
    op.create_unique_constraint(
        'uq_applications_profile_program', 'applications', ['profile_id', 'program_id']
    )


def downgrade() -> None:
    op.drop_constraint('uq_applications_profile_program', 'applications', type_='unique')
    op.drop_column('applications', 'checked_docs')
    op.drop_constraint('uq_matches_profile_program', 'matches', type_='unique')
    op.execute(
        "ALTER TABLE support_programs "
        "ALTER COLUMN doc_checklist TYPE JSON "
        "USING CASE WHEN doc_checklist IS NULL THEN NULL "
        "ELSE array_to_json(doc_checklist) END"
    )
    op.drop_column('support_programs', 'checked_at')
    op.drop_column('support_programs', 'highlight')
    op.drop_column('support_programs', 'eligible_status')
    op.drop_column('support_programs', 'short_title')
