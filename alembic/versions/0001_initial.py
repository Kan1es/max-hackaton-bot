"""Initial models: users, profiles, support_programs, matches, applications

Revision ID: 0001_initial
Revises:
Create Date: 2026-09-21 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('max_user_id', sa.BigInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_max_user_id'), 'users', ['max_user_id'], unique=True)

    # 2. profiles table
    op.create_table(
        'profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('region', sa.String(length=150), nullable=True),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_profiles_id'), 'profiles', ['id'], unique=False)
    op.create_index(op.f('ix_profiles_industry'), 'profiles', ['industry'], unique=False)
    op.create_index(op.f('ix_profiles_region'), 'profiles', ['region'], unique=False)
    op.create_index(op.f('ix_profiles_user_id'), 'profiles', ['user_id'], unique=True)

    # 3. support_programs table
    op.create_table(
        'support_programs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('region', sa.String(length=255), nullable=True),
        sa.Column('industries', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('conditions', sa.Text(), nullable=True),
        sa.Column('type', sa.String(length=255), nullable=True),
        sa.Column('amount', sa.String(length=500), nullable=True),
        sa.Column('deadline', sa.String(length=500), nullable=True),
        sa.Column('doc_checklist', sa.JSON(), nullable=True),
        sa.Column('source_url', sa.String(length=1000), nullable=True),
        sa.Column('is_mock', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_support_programs_id'), 'support_programs', ['id'], unique=False)
    op.create_index(op.f('ix_support_programs_name'), 'support_programs', ['name'], unique=False)

    # 4. matches table
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['support_programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_matches_id'), 'matches', ['id'], unique=False)
    op.create_index(op.f('ix_matches_profile_id'), 'matches', ['profile_id'], unique=False)
    op.create_index(op.f('ix_matches_program_id'), 'matches', ['program_id'], unique=False)

    # 5. applications table
    op.create_table(
        'applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='saved'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['profile_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['support_programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_applications_id'), 'applications', ['id'], unique=False)
    op.create_index(op.f('ix_applications_profile_id'), 'applications', ['profile_id'], unique=False)
    op.create_index(op.f('ix_applications_program_id'), 'applications', ['program_id'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)


def downgrade() -> None:
    op.drop_table('applications')
    op.drop_table('matches')
    op.drop_table('support_programs')
    op.drop_table('profiles')
    op.drop_table('users')
