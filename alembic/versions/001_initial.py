"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create user_profiles table (if it doesn't exist)
    op.create_table(
        'user_profiles',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('sex', sa.String(), nullable=False),
        sa.Column('weight_kg', sa.Float(), nullable=False),
        sa.Column('height_cm', sa.Float(), nullable=False),
        sa.Column('activity_level', sa.String(), nullable=False),
        sa.Column('goal', sa.String(), nullable=False),
        sa.Column('goal_rate_kg_per_week', sa.Float(), nullable=False),
        sa.Column('diet_pref', sa.String(), nullable=False),
        sa.Column('allergies', sa.JSON(), nullable=True),
        sa.Column('wake_time', sa.String(), nullable=False),
        sa.Column('lunch_time', sa.String(), nullable=False),
        sa.Column('dinner_time', sa.String(), nullable=False),
        sa.Column('cooking_skill', sa.Integer(), nullable=False),
        sa.Column('budget_per_week', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('user_id')
    )
    
    # Create meal_plans table (if it doesn't exist)
    op.create_table(
        'meal_plans',
        sa.Column('plan_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('plan_data', sa.JSON(), nullable=False),
        sa.Column('total_kcal', sa.Float(), nullable=False),
        sa.Column('total_protein_g', sa.Float(), nullable=False),
        sa.Column('total_carbs_g', sa.Float(), nullable=False),
        sa.Column('total_fat_g', sa.Float(), nullable=False),
        sa.Column('nutrition_provenance', sa.String(), nullable=False),
        sa.Column('plan_version', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('plan_id'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'])
    )
    
    # Create indexes
    op.create_index('ix_user_profiles_user_id', 'user_profiles', ['user_id'], unique=False)
    op.create_index('ix_meal_plans_plan_id', 'meal_plans', ['plan_id'], unique=False)
    op.create_index('ix_meal_plans_user_id', 'meal_plans', ['user_id'], unique=False)
    op.create_index('ix_meal_plans_date', 'meal_plans', ['date'], unique=False)


def downgrade():
    op.drop_table('meal_plans')
    op.drop_table('user_profiles')