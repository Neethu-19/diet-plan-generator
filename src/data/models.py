"""
SQLAlchemy ORM models for database tables.
"""
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Text, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from src.data.database import Base


class UserProfileModel(Base):
    """User profile table."""
    __tablename__ = "user_profiles"
    
    user_id = Column(String, primary_key=True, index=True)
    age = Column(Integer, nullable=False)
    sex = Column(String, nullable=False)
    weight_kg = Column(Float, nullable=False)
    height_cm = Column(Float, nullable=False)
    activity_level = Column(String, nullable=False)
    goal = Column(String, nullable=False)
    goal_rate_kg_per_week = Column(Float, nullable=False)
    diet_pref = Column(String, nullable=False)
    allergies = Column(JSON, default=list)
    wake_time = Column(String, nullable=False)
    lunch_time = Column(String, nullable=False)
    dinner_time = Column(String, nullable=False)
    cooking_skill = Column(Integer, nullable=False)
    budget_per_week = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    meal_plans = relationship("MealPlanModel", back_populates="user")
    weekly_plans = relationship("WeeklyPlanModel", back_populates="user")


class MealPlanModel(Base):
    """Meal plan table."""
    __tablename__ = "meal_plans"
    
    plan_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)
    plan_data = Column(JSON, nullable=False)  # Stores complete meal plan JSON
    total_kcal = Column(Float, nullable=False)
    total_protein_g = Column(Float, nullable=False)
    total_carbs_g = Column(Float, nullable=False)
    total_fat_g = Column(Float, nullable=False)
    nutrition_provenance = Column(String, nullable=False)
    plan_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("UserProfileModel", back_populates="meal_plans")
    swap_history = relationship("SwapHistoryModel", back_populates="meal_plan")


class SwapHistoryModel(Base):
    """Swap history table for tracking meal swaps."""
    __tablename__ = "swap_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(String, ForeignKey("meal_plans.plan_id"), nullable=False, index=True)
    meal_type = Column(String, nullable=False)
    original_recipe_id = Column(String, nullable=False)
    new_recipe_id = Column(String, nullable=False)
    swap_reason = Column(Text, nullable=True)
    constraints = Column(JSON, default=dict)
    swapped_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    meal_plan = relationship("MealPlanModel", back_populates="swap_history")


class WeeklyPlanModel(Base):
    """Weekly meal plan table."""
    __tablename__ = "weekly_plans"
    
    week_plan_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("user_profiles.user_id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False, index=True)
    end_date = Column(Date, nullable=False)
    activity_pattern = Column(JSON, nullable=False)  # {day_name: activity_level}
    variety_score = Column(Float, nullable=False)
    max_recipe_repeats = Column(Integer, default=2)
    variety_preference = Column(Float, default=0.8)
    is_archived = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("UserProfileModel", back_populates="weekly_plans")
    daily_plans = relationship("DailyPlanModel", back_populates="weekly_plan", cascade="all, delete-orphan")


class DailyPlanModel(Base):
    """Daily meal plan within a weekly plan."""
    __tablename__ = "daily_plans"
    
    day_plan_id = Column(String, primary_key=True, index=True)
    week_plan_id = Column(String, ForeignKey("weekly_plans.week_plan_id"), nullable=False, index=True)
    day_index = Column(Integer, nullable=False)  # 0-6
    date = Column(Date, nullable=False, index=True)
    day_name = Column(String, nullable=False)  # monday, tuesday, etc.
    activity_level = Column(String, nullable=False)
    
    # Adjusted nutrition targets
    target_kcal = Column(Float, nullable=False)
    target_protein_g = Column(Float, nullable=False)
    target_carbs_g = Column(Float, nullable=False)
    target_fat_g = Column(Float, nullable=False)
    
    # Actual nutrition totals
    total_kcal = Column(Float, nullable=False)
    total_protein_g = Column(Float, nullable=False)
    total_carbs_g = Column(Float, nullable=False)
    total_fat_g = Column(Float, nullable=False)
    
    nutrition_provenance = Column(String, nullable=False)
    plan_version = Column(String, nullable=False)
    sources = Column(JSON, default=list)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    weekly_plan = relationship("WeeklyPlanModel", back_populates="daily_plans")
    meals = relationship("PlanMealModel", back_populates="daily_plan", cascade="all, delete-orphan")


class PlanMealModel(Base):
    """Individual meal within a daily plan."""
    __tablename__ = "plan_meals"
    
    meal_id = Column(String, primary_key=True, index=True)
    day_plan_id = Column(String, ForeignKey("daily_plans.day_plan_id"), nullable=False, index=True)
    meal_type = Column(String, nullable=False)  # breakfast, lunch, dinner, snacks
    sequence = Column(Integer, nullable=False)  # Order within the day
    
    recipe_id = Column(String, nullable=False, index=True)
    recipe_title = Column(String, nullable=False)
    servings = Column(Float, nullable=False)
    
    # Nutrition per serving
    kcal_per_serving = Column(Float, nullable=False)
    protein_g_per_serving = Column(Float, nullable=False)
    carbs_g_per_serving = Column(Float, nullable=False)
    fat_g_per_serving = Column(Float, nullable=False)
    
    # Total nutrition (servings * per_serving)
    total_kcal = Column(Float, nullable=False)
    total_protein_g = Column(Float, nullable=False)
    total_carbs_g = Column(Float, nullable=False)
    total_fat_g = Column(Float, nullable=False)
    
    ingredients = Column(JSON, default=list)
    instructions = Column(Text, nullable=True)
    prep_time_min = Column(Integer, nullable=True)
    cook_time_min = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    daily_plan = relationship("DailyPlanModel", back_populates="meals")
