"""Add weekly plan tables

Revision ID: 002_weekly_plans
Revises: 001_initial
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_weekly_plans'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Create weekly_plans table
    op.create_table(
        'weekly_plans',
        sa.Column('week_plan_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('activity_pattern', sa.JSON(), nullable=False),
        sa.Column('variety_score', sa.Float(), nullable=False),
        sa.Column('max_recipe_repeats', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('variety_preference', sa.Float(), nullable=False, server_default='0.8'),
        sa.Column('is_archived', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('week_plan_id'),
        sa.ForeignKeyConstraint(['user_id'], ['user_profiles.user_id'], ondelete='CASCADE')
    )
    
    # Create indexes for weekly_plans
    op.create_index('idx_weekly_plans_user_date', 'weekly_plans', ['user_id', 'start_date'], unique=False)
    op.create_index('idx_weekly_plans_archived', 'weekly_plans', ['is_archived'], unique=False)
    op.create_index('ix_weekly_plans_week_plan_id', 'weekly_plans', ['week_plan_id'], unique=False)
    op.create_index('ix_weekly_plans_user_id', 'weekly_plans', ['user_id'], unique=False)
    op.create_index('ix_weekly_plans_start_date', 'weekly_plans', ['start_date'], unique=False)
    
    # Create daily_plans table
    op.create_table(
        'daily_plans',
        sa.Column('day_plan_id', sa.String(), nullable=False),
        sa.Column('week_plan_id', sa.String(), nullable=False),
        sa.Column('day_index', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('day_name', sa.String(), nullable=False),
        sa.Column('activity_level', sa.String(), nullable=False),
        sa.Column('target_kcal', sa.Float(), nullable=False),
        sa.Column('target_protein_g', sa.Float(), nullable=False),
        sa.Column('target_carbs_g', sa.Float(), nullable=False),
        sa.Column('target_fat_g', sa.Float(), nullable=False),
        sa.Column('total_kcal', sa.Float(), nullable=False),
        sa.Column('total_protein_g', sa.Float(), nullable=False),
        sa.Column('total_carbs_g', sa.Float(), nullable=False),
        sa.Column('total_fat_g', sa.Float(), nullable=False),
        sa.Column('nutrition_provenance', sa.String(), nullable=False),
        sa.Column('plan_version', sa.String(), nullable=False),
        sa.Column('sources', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('day_plan_id'),
        sa.ForeignKeyConstraint(['week_plan_id'], ['weekly_plans.week_plan_id'], ondelete='CASCADE')
    )
    
    # Create indexes for daily_plans
    op.create_index('idx_daily_plans_week', 'daily_plans', ['week_plan_id'], unique=False)
    op.create_index('idx_daily_plans_date', 'daily_plans', ['date'], unique=False)
    op.create_index('ix_daily_plans_day_plan_id', 'daily_plans', ['day_plan_id'], unique=False)
    op.create_index('ix_daily_plans_week_plan_id', 'daily_plans', ['week_plan_id'], unique=False)
    
    # Create plan_meals table
    op.create_table(
        'plan_meals',
        sa.Column('meal_id', sa.String(), nullable=False),
        sa.Column('day_plan_id', sa.String(), nullable=False),
        sa.Column('meal_type', sa.String(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('recipe_id', sa.String(), nullable=False),
        sa.Column('recipe_title', sa.String(), nullable=False),
        sa.Column('servings', sa.Float(), nullable=False),
        sa.Column('kcal_per_serving', sa.Float(), nullable=False),
        sa.Column('protein_g_per_serving', sa.Float(), nullable=False),
        sa.Column('carbs_g_per_serving', sa.Float(), nullable=False),
        sa.Column('fat_g_per_serving', sa.Float(), nullable=False),
        sa.Column('total_kcal', sa.Float(), nullable=False),
        sa.Column('total_protein_g', sa.Float(), nullable=False),
        sa.Column('total_carbs_g', sa.Float(), nullable=False),
        sa.Column('total_fat_g', sa.Float(), nullable=False),
        sa.Column('ingredients', sa.JSON(), nullable=False, server_default='[]'),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('prep_time_min', sa.Integer(), nullable=True),
        sa.Column('cook_time_min', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('meal_id'),
        sa.ForeignKeyConstraint(['day_plan_id'], ['daily_plans.day_plan_id'], ondelete='CASCADE')
    )
    
    # Create indexes for plan_meals
    op.create_index('idx_plan_meals_day', 'plan_meals', ['day_plan_id'], unique=False)
    op.create_index('idx_plan_meals_recipe', 'plan_meals', ['recipe_id'], unique=False)
    op.create_index('ix_plan_meals_meal_id', 'plan_meals', ['meal_id'], unique=False)
    op.create_index('ix_plan_meals_day_plan_id', 'plan_meals', ['day_plan_id'], unique=False)


def downgrade():
    # Drop tables in reverse order (due to foreign key constraints)
    op.drop_table('plan_meals')
    op.drop_table('daily_plans')
    op.drop_table('weekly_plans')
