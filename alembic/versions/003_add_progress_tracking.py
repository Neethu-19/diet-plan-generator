"""Add progress tracking tables

Revision ID: 003
Revises: 002
Create Date: 2025-11-19

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers
revision = '003_progress_tracking'
down_revision = '002_weekly_plans'
branch_labels = None
depends_on = None


def upgrade():
    # Create progress_logs table
    op.create_table(
        'progress_logs',
        sa.Column('log_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('log_date', sa.Date(), nullable=False),
        sa.Column('actual_weight_kg', sa.Float(), nullable=False),
        sa.Column('adherence_score', sa.Float(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('energy_level', sa.Integer(), nullable=True),
        sa.Column('hunger_level', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('log_id'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'])
    )
    
    # Create indexes for progress_logs
    op.create_index('ix_progress_logs_user_id', 'progress_logs', ['user_id'])
    op.create_index('ix_progress_logs_log_date', 'progress_logs', ['log_date'])
    op.create_index('ix_progress_logs_user_date', 'progress_logs', ['user_id', 'log_date'], unique=True)
    
    # Create calorie_adjustments table
    op.create_table(
        'calorie_adjustments',
        sa.Column('adjustment_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('adjustment_date', sa.DateTime(), nullable=False),
        sa.Column('previous_target_kcal', sa.Float(), nullable=False),
        sa.Column('new_target_kcal', sa.Float(), nullable=False),
        sa.Column('adjustment_amount', sa.Float(), nullable=False),
        sa.Column('reason', sa.String(), nullable=False),
        sa.Column('actual_progress_rate', sa.Float(), nullable=True),
        sa.Column('expected_progress_rate', sa.Float(), nullable=True),
        sa.Column('average_adherence', sa.Float(), nullable=True),
        sa.Column('analysis_start_date', sa.Date(), nullable=True),
        sa.Column('analysis_end_date', sa.Date(), nullable=True),
        sa.Column('num_logs_analyzed', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('adjustment_id'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'])
    )
    
    # Create indexes for calorie_adjustments
    op.create_index('ix_calorie_adjustments_user_id', 'calorie_adjustments', ['user_id'])
    op.create_index('ix_calorie_adjustments_adjustment_date', 'calorie_adjustments', ['adjustment_date'])


def downgrade():
    op.drop_table('calorie_adjustments')
    op.drop_table('progress_logs')
