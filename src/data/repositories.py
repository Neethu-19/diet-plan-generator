"""
Repository pattern for data access.
Provides CRUD operations for database models.
"""
from typing import List, Optional, Dict
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, date, timedelta
import json
import uuid

from src.data.models import (
    UserProfileModel, MealPlanModel, SwapHistoryModel,
    WeeklyPlanModel, DailyPlanModel, PlanMealModel
)
from src.models.schemas import UserProfile, MealPlan
from src.utils.logging_config import logger


class UserProfileRepository:
    """Repository for user profile operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, user_profile: UserProfile) -> UserProfileModel:
        """
        Create a new user profile.
        
        Args:
            user_profile: UserProfile schema
            
        Returns:
            Created UserProfileModel
        """
        db_user = UserProfileModel(
            user_id=user_profile.user_id,
            age=user_profile.age,
            sex=user_profile.sex.value,
            weight_kg=user_profile.weight_kg,
            height_cm=user_profile.height_cm,
            activity_level=user_profile.activity_level.value,
            goal=user_profile.goal.value,
            goal_rate_kg_per_week=user_profile.goal_rate_kg_per_week,
            diet_pref=user_profile.diet_pref.value,
            allergies=user_profile.allergies,
            wake_time=user_profile.wake_time.isoformat(),
            lunch_time=user_profile.lunch_time.isoformat(),
            dinner_time=user_profile.dinner_time.isoformat(),
            cooking_skill=user_profile.cooking_skill,
            budget_per_week=user_profile.budget_per_week
        )
        
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Created user profile: {db_user.user_id}")
        return db_user
    
    def get(self, user_id: str) -> Optional[UserProfileModel]:
        """
        Get user profile by ID.
        
        Args:
            user_id: User identifier
            
        Returns:
            UserProfileModel or None
        """
        return self.db.query(UserProfileModel).filter(
            UserProfileModel.user_id == user_id
        ).first()
    
    def update(self, user_id: str, user_profile: UserProfile) -> Optional[UserProfileModel]:
        """
        Update user profile.
        
        Args:
            user_id: User identifier
            user_profile: Updated UserProfile schema
            
        Returns:
            Updated UserProfileModel or None
        """
        db_user = self.get(user_id)
        if db_user is None:
            return None
        
        # Update fields
        db_user.age = user_profile.age
        db_user.sex = user_profile.sex.value
        db_user.weight_kg = user_profile.weight_kg
        db_user.height_cm = user_profile.height_cm
        db_user.activity_level = user_profile.activity_level.value
        db_user.goal = user_profile.goal.value
        db_user.goal_rate_kg_per_week = user_profile.goal_rate_kg_per_week
        db_user.diet_pref = user_profile.diet_pref.value
        db_user.allergies = user_profile.allergies
        db_user.wake_time = user_profile.wake_time.isoformat()
        db_user.lunch_time = user_profile.lunch_time.isoformat()
        db_user.dinner_time = user_profile.dinner_time.isoformat()
        db_user.cooking_skill = user_profile.cooking_skill
        db_user.budget_per_week = user_profile.budget_per_week
        db_user.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(db_user)
        
        logger.info(f"Updated user profile: {user_id}")
        return db_user
    
    def delete(self, user_id: str) -> bool:
        """
        Delete user profile.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if deleted, False if not found
        """
        db_user = self.get(user_id)
        if db_user is None:
            return False
        
        self.db.delete(db_user)
        self.db.commit()
        
        logger.info(f"Deleted user profile: {user_id}")
        return True


class MealPlanRepository:
    """Repository for meal plan operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, meal_plan: MealPlan) -> MealPlanModel:
        """
        Create a new meal plan.
        
        Args:
            meal_plan: MealPlan schema
            
        Returns:
            Created MealPlanModel
        """
        # Convert meal plan to dict for JSON storage
        plan_data = meal_plan.dict()
        
        db_plan = MealPlanModel(
            plan_id=meal_plan.plan_id,
            user_id=meal_plan.user_id,
            date=meal_plan.date,
            plan_data=plan_data,
            total_kcal=meal_plan.total_nutrition.get("kcal", 0),
            total_protein_g=meal_plan.total_nutrition.get("protein_g", 0),
            total_carbs_g=meal_plan.total_nutrition.get("carbs_g", 0),
            total_fat_g=meal_plan.total_nutrition.get("fat_g", 0),
            nutrition_provenance=meal_plan.nutrition_provenance,
            plan_version=meal_plan.plan_version
        )
        
        self.db.add(db_plan)
        self.db.commit()
        self.db.refresh(db_plan)
        
        logger.info(f"Created meal plan: {db_plan.plan_id}")
        return db_plan
    
    def get(self, plan_id: str) -> Optional[MealPlanModel]:
        """
        Get meal plan by ID.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            MealPlanModel or None
        """
        return self.db.query(MealPlanModel).filter(
            MealPlanModel.plan_id == plan_id
        ).first()
    
    def get_by_user(self, user_id: str, limit: int = 10) -> List[MealPlanModel]:
        """
        Get meal plans for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of plans to return
            
        Returns:
            List of MealPlanModel
        """
        return self.db.query(MealPlanModel).filter(
            MealPlanModel.user_id == user_id
        ).order_by(MealPlanModel.created_at.desc()).limit(limit).all()
    
    def update(self, plan_id: str, meal_plan: MealPlan) -> Optional[MealPlanModel]:
        """
        Update meal plan.
        
        Args:
            plan_id: Plan identifier
            meal_plan: Updated MealPlan schema
            
        Returns:
            Updated MealPlanModel or None
        """
        db_plan = self.get(plan_id)
        if db_plan is None:
            return None
        
        # Update fields
        plan_data = meal_plan.dict()
        db_plan.plan_data = plan_data
        db_plan.total_kcal = meal_plan.total_nutrition.get("kcal", 0)
        db_plan.total_protein_g = meal_plan.total_nutrition.get("protein_g", 0)
        db_plan.total_carbs_g = meal_plan.total_nutrition.get("carbs_g", 0)
        db_plan.total_fat_g = meal_plan.total_nutrition.get("fat_g", 0)
        
        self.db.commit()
        self.db.refresh(db_plan)
        
        logger.info(f"Updated meal plan: {plan_id}")
        return db_plan
    
    def delete(self, plan_id: str) -> bool:
        """
        Delete meal plan.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            True if deleted, False if not found
        """
        db_plan = self.get(plan_id)
        if db_plan is None:
            return False
        
        self.db.delete(db_plan)
        self.db.commit()
        
        logger.info(f"Deleted meal plan: {plan_id}")
        return True


class SwapHistoryRepository:
    """Repository for swap history operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(
        self,
        plan_id: str,
        meal_type: str,
        original_recipe_id: str,
        new_recipe_id: str,
        swap_reason: Optional[str] = None,
        constraints: Optional[dict] = None
    ) -> SwapHistoryModel:
        """
        Create a swap history record.
        
        Args:
            plan_id: Plan identifier
            meal_type: Type of meal swapped
            original_recipe_id: Original recipe ID
            new_recipe_id: New recipe ID
            swap_reason: Optional reason for swap
            constraints: Optional swap constraints
            
        Returns:
            Created SwapHistoryModel
        """
        db_swap = SwapHistoryModel(
            plan_id=plan_id,
            meal_type=meal_type,
            original_recipe_id=original_recipe_id,
            new_recipe_id=new_recipe_id,
            swap_reason=swap_reason,
            constraints=constraints or {}
        )
        
        self.db.add(db_swap)
        self.db.commit()
        self.db.refresh(db_swap)
        
        logger.info(f"Created swap history for plan {plan_id}, meal {meal_type}")
        return db_swap
    
    def get_by_plan(self, plan_id: str) -> List[SwapHistoryModel]:
        """
        Get swap history for a plan.
        
        Args:
            plan_id: Plan identifier
            
        Returns:
            List of SwapHistoryModel
        """
        return self.db.query(SwapHistoryModel).filter(
            SwapHistoryModel.plan_id == plan_id
        ).order_by(SwapHistoryModel.swapped_at.desc()).all()



class WeeklyPlanRepository:
    """Repository for weekly meal plan operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_weekly_plan(self, weekly_plan_dict: Dict) -> WeeklyPlanModel:
        """
        Store a complete weekly plan with all daily plans and meals.
        
        Args:
            weekly_plan_dict: Weekly plan dictionary from WeeklyPlanner service
            
        Returns:
            Created WeeklyPlanModel
        """
        try:
            # Parse dates
            start_date = datetime.fromisoformat(weekly_plan_dict['start_date']).date()
            end_date = datetime.fromisoformat(weekly_plan_dict['end_date']).date()
            
            # Create weekly plan
            db_weekly_plan = WeeklyPlanModel(
                week_plan_id=weekly_plan_dict['week_plan_id'],
                user_id=weekly_plan_dict['user_id'],
                start_date=start_date,
                end_date=end_date,
                activity_pattern=weekly_plan_dict['activity_pattern'],
                variety_score=weekly_plan_dict['recipe_variety_score'],
                max_recipe_repeats=weekly_plan_dict.get('max_recipe_repeats', 2),
                variety_preference=weekly_plan_dict.get('variety_preference', 0.8),
                is_archived=False
            )
            
            self.db.add(db_weekly_plan)
            
            # Create daily plans
            for daily_plan_dict in weekly_plan_dict['daily_plans']:
                day_date = datetime.fromisoformat(daily_plan_dict['date']).date()
                
                db_daily_plan = DailyPlanModel(
                    day_plan_id=daily_plan_dict.get('plan_id', f"day_{uuid.uuid4().hex[:12]}"),
                    week_plan_id=weekly_plan_dict['week_plan_id'],
                    day_index=daily_plan_dict['day_index'],
                    date=day_date,
                    day_name=daily_plan_dict['day_name'],
                    activity_level=daily_plan_dict['activity_level'],
                    target_kcal=daily_plan_dict['adjusted_targets']['target_kcal'],
                    target_protein_g=daily_plan_dict['adjusted_targets']['protein_g'],
                    target_carbs_g=daily_plan_dict['adjusted_targets']['carbs_g'],
                    target_fat_g=daily_plan_dict['adjusted_targets']['fat_g'],
                    total_kcal=daily_plan_dict['total_nutrition']['kcal'],
                    total_protein_g=daily_plan_dict['total_nutrition']['protein_g'],
                    total_carbs_g=daily_plan_dict['total_nutrition']['carbs_g'],
                    total_fat_g=daily_plan_dict['total_nutrition']['fat_g'],
                    nutrition_provenance=daily_plan_dict.get('nutrition_provenance', 'calculated'),
                    plan_version=daily_plan_dict.get('plan_version', 'v1.0'),
                    sources=daily_plan_dict.get('sources', [])
                )
                
                self.db.add(db_daily_plan)
                
                # Create meals for this day
                for sequence, meal_dict in enumerate(daily_plan_dict['meals']):
                    # Extract servings from portion_size string (e.g., "1.5x serving" -> 1.5)
                    portion_size = meal_dict.get('portion_size', '1 serving')
                    try:
                        if 'x serving' in portion_size:
                            servings = float(portion_size.split('x')[0])
                        else:
                            servings = 1.0
                    except:
                        servings = 1.0
                    
                    # Calculate per-serving nutrition
                    total_kcal = meal_dict.get('kcal', 0)
                    total_protein = meal_dict.get('protein_g', 0)
                    total_carbs = meal_dict.get('carbs_g', 0)
                    total_fat = meal_dict.get('fat_g', 0)
                    
                    kcal_per_serving = total_kcal / servings if servings > 0 else 0
                    protein_per_serving = total_protein / servings if servings > 0 else 0
                    carbs_per_serving = total_carbs / servings if servings > 0 else 0
                    fat_per_serving = total_fat / servings if servings > 0 else 0
                    
                    db_meal = PlanMealModel(
                        meal_id=f"meal_{uuid.uuid4().hex[:12]}",
                        day_plan_id=db_daily_plan.day_plan_id,
                        meal_type=meal_dict['meal_type'],
                        sequence=sequence,
                        recipe_id=meal_dict['recipe_id'],
                        recipe_title=meal_dict['recipe_title'],
                        servings=servings,
                        kcal_per_serving=kcal_per_serving,
                        protein_g_per_serving=protein_per_serving,
                        carbs_g_per_serving=carbs_per_serving,
                        fat_g_per_serving=fat_per_serving,
                        total_kcal=total_kcal,
                        total_protein_g=total_protein,
                        total_carbs_g=total_carbs,
                        total_fat_g=total_fat,
                        ingredients=meal_dict.get('ingredients', []),
                        instructions=meal_dict.get('instructions'),
                        prep_time_min=meal_dict.get('prep_time_min'),
                        cook_time_min=meal_dict.get('cook_time_min')
                    )
                    
                    self.db.add(db_meal)
            
            self.db.commit()
            self.db.refresh(db_weekly_plan)
            
            logger.info(f"Created weekly plan: {db_weekly_plan.week_plan_id}")
            return db_weekly_plan
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating weekly plan: {e}")
            raise
    
    def get_weekly_plan(self, week_plan_id: str) -> Optional[WeeklyPlanModel]:
        """
        Retrieve a weekly plan by ID with all related data.
        
        Args:
            week_plan_id: Weekly plan identifier
            
        Returns:
            WeeklyPlanModel or None
        """
        return self.db.query(WeeklyPlanModel).options(
            joinedload(WeeklyPlanModel.daily_plans).joinedload(DailyPlanModel.meals)
        ).filter(
            WeeklyPlanModel.week_plan_id == week_plan_id
        ).first()
    
    def get_weekly_plan_by_date(self, user_id: str, target_date: date) -> Optional[WeeklyPlanModel]:
        """
        Find the weekly plan containing a specific date.
        
        Args:
            user_id: User identifier
            target_date: Date to search for
            
        Returns:
            WeeklyPlanModel or None
        """
        return self.db.query(WeeklyPlanModel).options(
            joinedload(WeeklyPlanModel.daily_plans).joinedload(DailyPlanModel.meals)
        ).filter(
            WeeklyPlanModel.user_id == user_id,
            WeeklyPlanModel.start_date <= target_date,
            WeeklyPlanModel.end_date >= target_date,
            WeeklyPlanModel.is_archived == False
        ).first()
    
    def get_user_weekly_plans(
        self,
        user_id: str,
        limit: int = 10,
        include_archived: bool = False
    ) -> List[WeeklyPlanModel]:
        """
        Get all weekly plans for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of plans to return
            include_archived: Whether to include archived plans
            
        Returns:
            List of WeeklyPlanModel
        """
        query = self.db.query(WeeklyPlanModel).filter(
            WeeklyPlanModel.user_id == user_id
        )
        
        if not include_archived:
            query = query.filter(WeeklyPlanModel.is_archived == False)
        
        return query.order_by(
            WeeklyPlanModel.start_date.desc()
        ).limit(limit).all()
    
    def update_daily_plan(self, day_plan_id: str, updated_meals: List[Dict]) -> Optional[DailyPlanModel]:
        """
        Update a specific day's meals.
        
        Args:
            day_plan_id: Daily plan identifier
            updated_meals: List of updated meal dictionaries
            
        Returns:
            Updated DailyPlanModel or None
        """
        try:
            db_daily_plan = self.db.query(DailyPlanModel).filter(
                DailyPlanModel.day_plan_id == day_plan_id
            ).first()
            
            if db_daily_plan is None:
                return None
            
            # Delete existing meals
            self.db.query(PlanMealModel).filter(
                PlanMealModel.day_plan_id == day_plan_id
            ).delete()
            
            # Create new meals
            total_kcal = 0
            total_protein = 0
            total_carbs = 0
            total_fat = 0
            
            for sequence, meal_dict in enumerate(updated_meals):
                # Extract servings from portion_size string
                portion_size = meal_dict.get('portion_size', '1 serving')
                try:
                    if 'x serving' in portion_size:
                        servings = float(portion_size.split('x')[0])
                    else:
                        servings = 1.0
                except:
                    servings = 1.0
                
                # Calculate per-serving nutrition
                total_kcal = meal_dict.get('kcal', 0)
                total_protein = meal_dict.get('protein_g', 0)
                total_carbs = meal_dict.get('carbs_g', 0)
                total_fat = meal_dict.get('fat_g', 0)
                
                kcal_per_serving = total_kcal / servings if servings > 0 else 0
                protein_per_serving = total_protein / servings if servings > 0 else 0
                carbs_per_serving = total_carbs / servings if servings > 0 else 0
                fat_per_serving = total_fat / servings if servings > 0 else 0
                
                db_meal = PlanMealModel(
                    meal_id=f"meal_{uuid.uuid4().hex[:12]}",
                    day_plan_id=day_plan_id,
                    meal_type=meal_dict['meal_type'],
                    sequence=sequence,
                    recipe_id=meal_dict['recipe_id'],
                    recipe_title=meal_dict['recipe_title'],
                    servings=servings,
                    kcal_per_serving=kcal_per_serving,
                    protein_g_per_serving=protein_per_serving,
                    carbs_g_per_serving=carbs_per_serving,
                    fat_g_per_serving=fat_per_serving,
                    total_kcal=total_kcal,
                    total_protein_g=total_protein,
                    total_carbs_g=total_carbs,
                    total_fat_g=total_fat,
                    ingredients=meal_dict.get('ingredients', []),
                    instructions=meal_dict.get('instructions'),
                    prep_time_min=meal_dict.get('prep_time_min'),
                    cook_time_min=meal_dict.get('cook_time_min')
                )
                
                self.db.add(db_meal)
                
                total_kcal += meal_dict['total_nutrition']['kcal']
                total_protein += meal_dict['total_nutrition']['protein_g']
                total_carbs += meal_dict['total_nutrition']['carbs_g']
                total_fat += meal_dict['total_nutrition']['fat_g']
            
            # Update daily plan totals
            db_daily_plan.total_kcal = total_kcal
            db_daily_plan.total_protein_g = total_protein
            db_daily_plan.total_carbs_g = total_carbs
            db_daily_plan.total_fat_g = total_fat
            db_daily_plan.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(db_daily_plan)
            
            logger.info(f"Updated daily plan: {day_plan_id}")
            return db_daily_plan
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating daily plan: {e}")
            raise
    
    def archive_weekly_plan(self, week_plan_id: str) -> bool:
        """
        Soft delete a weekly plan.
        
        Args:
            week_plan_id: Weekly plan identifier
            
        Returns:
            True if archived, False if not found
        """
        db_plan = self.db.query(WeeklyPlanModel).filter(
            WeeklyPlanModel.week_plan_id == week_plan_id
        ).first()
        
        if db_plan is None:
            return False
        
        db_plan.is_archived = True
        db_plan.updated_at = datetime.utcnow()
        
        self.db.commit()
        
        logger.info(f"Archived weekly plan: {week_plan_id}")
        return True
    
    def delete_weekly_plan(self, week_plan_id: str) -> bool:
        """
        Permanently delete a weekly plan.
        
        Args:
            week_plan_id: Weekly plan identifier
            
        Returns:
            True if deleted, False if not found
        """
        db_plan = self.db.query(WeeklyPlanModel).filter(
            WeeklyPlanModel.week_plan_id == week_plan_id
        ).first()
        
        if db_plan is None:
            return False
        
        self.db.delete(db_plan)
        self.db.commit()
        
        logger.info(f"Deleted weekly plan: {week_plan_id}")
        return True
    
    def get_daily_plan(self, week_plan_id: str, day_index: int) -> Optional[DailyPlanModel]:
        """
        Get a specific day from a weekly plan.
        
        Args:
            week_plan_id: Weekly plan identifier
            day_index: Day index (0-6)
            
        Returns:
            DailyPlanModel or None
        """
        return self.db.query(DailyPlanModel).options(
            joinedload(DailyPlanModel.meals)
        ).filter(
            DailyPlanModel.week_plan_id == week_plan_id,
            DailyPlanModel.day_index == day_index
        ).first()
    
    def get_today_plan(self, user_id: str) -> Optional[DailyPlanModel]:
        """
        Get today's meal plan for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            DailyPlanModel or None
        """
        today = date.today()
        
        return self.db.query(DailyPlanModel).options(
            joinedload(DailyPlanModel.meals)
        ).join(WeeklyPlanModel).filter(
            WeeklyPlanModel.user_id == user_id,
            DailyPlanModel.date == today,
            WeeklyPlanModel.is_archived == False
        ).first()
    
    def get_tomorrow_plan(self, user_id: str) -> Optional[DailyPlanModel]:
        """
        Get tomorrow's meal plan for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            DailyPlanModel or None
        """
        tomorrow = date.today() + timedelta(days=1)
        
        return self.db.query(DailyPlanModel).options(
            joinedload(DailyPlanModel.meals)
        ).join(WeeklyPlanModel).filter(
            WeeklyPlanModel.user_id == user_id,
            DailyPlanModel.date == tomorrow,
            WeeklyPlanModel.is_archived == False
        ).first()
