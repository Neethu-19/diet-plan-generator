"""add personalization tables

Revision ID: 004
Revises: 003
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index, UniqueConstraint


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    """Create recipe_feedback and user_preferences tables."""
    
    # Create recipe_feedback table
    op.create_table(
        'recipe_feedback',
        sa.Column('feedback_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('recipe_id', sa.String(), nullable=False),
        sa.Column('liked', sa.Boolean(), nullable=False),
        sa.Column('feedback_date', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'], ),
        sa.PrimaryKeyConstraint('feedback_id'),
        sa.UniqueConstraint('user_id', 'recipe_id', name='uq_user_recipe')
    )
    
    # Create indexes for recipe_feedback
    op.create_index('ix_recipe_feedback_feedback_id', 'recipe_feedback', ['feedback_id'])
    op.create_index('ix_recipe_feedback_user_id', 'recipe_feedback', ['user_id'])
    op.create_index('ix_recipe_feedback_recipe_id', 'recipe_feedback', ['recipe_id'])
    op.create_index('ix_recipe_feedback_user_liked', 'recipe_feedback', ['user_id', 'liked'])
    
    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('regional_profile', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'], ),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Create index for user_preferences
    op.create_index('ix_user_preferences_user_id', 'user_preferences', ['user_id'])


def downgrade():
    """Drop recipe_feedback and user_preferences tables."""
    
    # Drop indexes first
    op.drop_index('ix_user_preferences_user_id', table_name='user_preferences')
    op.drop_index('ix_recipe_feedback_user_liked', table_name='recipe_feedback')
    op.drop_index('ix_recipe_feedback_recipe_id', table_name='recipe_feedback')
    op.drop_index('ix_recipe_feedback_user_id', table_name='recipe_feedback')
    op.drop_index('ix_recipe_feedback_feedback_id', table_name='recipe_feedback')
    
    # Drop tables
    op.drop_table('user_preferences')
    op.drop_table('recipe_feedback')
