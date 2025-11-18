"""
Weekly Meal Planner Service.
Generates 7-day meal plans with recipe variety and activity-based adjustments.
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import uuid

from sqlalchemy.orm import Session

from src.core.nutrition_engine import NutritionEngine
from src.core.rag_module import RAGModule
from src.services.simple_planner import SimplePlanner
from src.models.schemas import UserProfile, ActivityLevel
from src.utils.logging_config import logger


class WeeklyPlanner:
    """
    Generates weekly meal plans with recipe variety and activity-based adjustments.
    """
    
    def __init__(
        self,
        nutrition_engine: NutritionEngine = None,
        rag_module: RAGModule = None,
        simple_planner: SimplePlanner = None,
        db_session: Optional[Session] = None
    ):
        """
        Initialize weekly planner.
        
        Args:
            nutrition_engine: Nutrition calculation engine
            rag_module: RAG retrieval module
            simple_planner: Simple meal planner
            db_session: Optional database session for persistence
        """
        self.nutrition_engine = nutrition_engine or NutritionEngine()
        self.rag_module = rag_module or RAGModule()
        self.simple_planner = simple_planner or SimplePlanner()
        
        # Initialize repository if database session provided
        self.repository = None
        if db_session:
            from src.data.repositories import WeeklyPlanRepository
            self.repository = WeeklyPlanRepository(db_session)
        
        # Activity level multipliers for macro adjustment
        self.activity_multipliers = {
            "rest": {"carbs": 0.85, "protein": 1.0, "fat": 1.15},
            "light": {"carbs": 0.95, "protein": 1.0, "fat": 1.05},
            "moderate": {"carbs": 1.0, "protein": 1.0, "fat": 1.0},
            "active": {"carbs": 1.15, "protein": 1.05, "fat": 0.95},
            "very_active": {"carbs": 1.25, "protein": 1.10, "fat": 0.90}
        }
        
        logger.info("Weekly Planner initialized")
    
    def generate_weekly_plan(
        self,
        user_profile: UserProfile,
        activity_pattern: Dict[str, str] = None,
        start_date: datetime = None,
        max_recipe_repeats: int = 2
    ) -> Dict:
        """
        Generate a 7-day meal plan with recipe variety.
        
        Args:
            user_profile: User profile information
            activity_pattern: Dict mapping day names to activity levels
                             e.g., {"monday": "active", "tuesday": "rest", ...}
            start_date: Start date for the week (defaults to today)
            max_recipe_repeats: Maximum times a recipe can repeat in the week
            
        Returns:
            Weekly meal plan dictionary
        """
        logger.info(f"Generating weekly meal plan for user: {user_profile.user_id}")
        
        # Default activity pattern if not provided
        if activity_pattern is None:
            activity_pattern = {
                "monday": "moderate",
                "tuesday": "moderate",
                "wednesday": "moderate",
                "thursday": "moderate",
                "friday": "moderate",
                "saturday": "light",
                "sunday": "rest"
            }
        
        # Default start date to today
        if start_date is None:
            start_date = datetime.now()
        
        week_plan_id = f"week_{uuid.uuid4().hex[:12]}"
        days = []
        recipe_usage = Counter()  # Track recipe usage across the week
        
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        
        for day_index, day_name in enumerate(day_names):
            day_date = start_date + timedelta(days=day_index)
            activity_level = activity_pattern.get(day_name, "moderate")
            
            logger.info(f"Generating plan for {day_name} (day {day_index + 1}) - activity: {activity_level}")
            
            # Adjust user profile for this day's activity
            adjusted_profile = self._adjust_profile_for_activity(
                user_profile, 
                activity_level
            )
            
            # Calculate nutrition targets for this day
            nutrition_targets = self.nutrition_engine.calculate_nutrition_targets(adjusted_profile)
            
            # Retrieve recipe candidates with variety constraints
            meal_candidates = {}
            for meal_type, target_kcal in nutrition_targets.meal_splits.items():
                candidates = self.rag_module.retrieve_candidates(
                    meal_type=meal_type,
                    target_kcal=target_kcal,
                    diet_pref=adjusted_profile.diet_pref,
                    allergens=adjusted_profile.allergies,
                    top_k=10  # Get more candidates for variety
                )
                
                # Filter out overused recipes
                filtered_candidates = self._filter_overused_recipes(
                    candidates,
                    recipe_usage,
                    max_recipe_repeats
                )
                
                meal_candidates[meal_type] = filtered_candidates[:3]  # Top 3 after filtering
            
            # Generate daily meal plan
            daily_plan = self.simple_planner.generate_plan(
                user_id=user_profile.user_id,
                meal_candidates=meal_candidates,
                meal_targets=nutrition_targets.meal_splits
            )
            
            # Update recipe usage counter
            for meal in daily_plan["meals"]:
                recipe_id = meal["recipe_id"]
                recipe_usage[recipe_id] += 1
            
            # Add day information
            day_plan = {
                "day_index": day_index,
                "day_name": day_name,
                "date": day_date.strftime("%Y-%m-%d"),
                "activity_level": activity_level,
                "meal_plan": daily_plan,
                "nutrition_targets": {
                    "target_kcal": nutrition_targets.target_kcal,
                    "protein_g": nutrition_targets.protein_g,
                    "carbs_g": nutrition_targets.carbs_g,
                    "fat_g": nutrition_targets.fat_g
                }
            }
            
            days.append(day_plan)
        
        # Calculate weekly totals and variety metrics
        weekly_stats = self._calculate_weekly_stats(days, recipe_usage)
        
        weekly_plan = {
            "week_plan_id": week_plan_id,
            "user_id": user_profile.user_id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": (start_date + timedelta(days=6)).strftime("%Y-%m-%d"),
            "days": days,
            "weekly_stats": weekly_stats,
            "activity_pattern": activity_pattern,
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"Generated weekly plan {week_plan_id} with {len(days)} days")
        logger.info(f"Recipe variety: {weekly_stats['unique_recipes']} unique recipes used")
        
        return weekly_plan
    
    def _adjust_profile_for_activity(
        self,
        base_profile: UserProfile,
        activity_level: str
    ) -> UserProfile:
        """
        Create adjusted profile for specific day's activity level.
        
        Args:
            base_profile: Base user profile
            activity_level: Activity level for the day
            
        Returns:
            Adjusted user profile
        """
        # Map activity string to ActivityLevel enum
        activity_map = {
            "rest": ActivityLevel.SEDENTARY,
            "light": ActivityLevel.LIGHT,
            "moderate": ActivityLevel.MODERATE,
            "active": ActivityLevel.ACTIVE,
            "very_active": ActivityLevel.VERY_ACTIVE
        }
        
        # Create a copy of the profile with adjusted activity
        adjusted_profile = UserProfile(
            user_id=base_profile.user_id,
            age=base_profile.age,
            sex=base_profile.sex,
            weight_kg=base_profile.weight_kg,
            height_cm=base_profile.height_cm,
            activity_level=activity_map.get(activity_level, base_profile.activity_level),
            goal=base_profile.goal,
            goal_rate_kg_per_week=base_profile.goal_rate_kg_per_week,
            diet_pref=base_profile.diet_pref,
            allergies=base_profile.allergies,
            wake_time=base_profile.wake_time,
            lunch_time=base_profile.lunch_time,
            dinner_time=base_profile.dinner_time,
            cooking_skill=base_profile.cooking_skill,
            budget_per_week=base_profile.budget_per_week
        )
        
        return adjusted_profile
    
    def _filter_overused_recipes(
        self,
        candidates: List,
        recipe_usage: Counter,
        max_repeats: int
    ) -> List:
        """
        Filter out recipes that have been used too many times.
        
        Args:
            candidates: List of recipe candidates
            recipe_usage: Counter tracking recipe usage
            max_repeats: Maximum allowed repeats
            
        Returns:
            Filtered list of candidates
        """
        filtered = []
        for candidate in candidates:
            if recipe_usage[candidate.recipe_id] < max_repeats:
                filtered.append(candidate)
        
        # If all recipes are overused, return original list (better than no recipes)
        if not filtered:
            logger.warning("All candidates overused, returning original list")
            return candidates
        
        return filtered
    
    def _calculate_weekly_stats(
        self,
        days: List[Dict],
        recipe_usage: Counter
    ) -> Dict:
        """
        Calculate weekly statistics and variety metrics.
        
        Args:
            days: List of daily meal plans
            recipe_usage: Counter of recipe usage
            
        Returns:
            Dictionary of weekly statistics
        """
        total_kcal = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        
        for day in days:
            total_nutrition = day["meal_plan"]["total_nutrition"]
            total_kcal += total_nutrition["kcal"]
            total_protein += total_nutrition["protein_g"]
            total_carbs += total_nutrition["carbs_g"]
            total_fat += total_nutrition["fat_g"]
        
        unique_recipes = len(recipe_usage)
        total_meals = sum(recipe_usage.values())
        variety_score = unique_recipes / total_meals if total_meals > 0 else 0
        
        # Find most and least used recipes
        most_common = recipe_usage.most_common(3)
        
        stats = {
            "total_kcal": round(total_kcal, 1),
            "total_protein_g": round(total_protein, 1),
            "total_carbs_g": round(total_carbs, 1),
            "total_fat_g": round(total_fat, 1),
            "avg_daily_kcal": round(total_kcal / 7, 1),
            "unique_recipes": unique_recipes,
            "total_meals": total_meals,
            "variety_score": round(variety_score, 2),
            "most_used_recipes": [
                {"recipe_id": recipe_id, "count": count}
                for recipe_id, count in most_common
            ]
        }
        
        return stats
    
    def regenerate_day(
        self,
        weekly_plan: Dict,
        day_index: int,
        recipe_usage: Counter = None
    ) -> Dict:
        """
        Regenerate a specific day in the weekly plan.
        
        Args:
            weekly_plan: Existing weekly plan
            day_index: Index of day to regenerate (0-6)
            recipe_usage: Optional recipe usage counter
            
        Returns:
            Updated weekly plan
        """
        logger.info(f"Regenerating day {day_index} in weekly plan")
        
        # Get the day to regenerate
        day_to_regenerate = weekly_plan["days"][day_index]
        
        # Reconstruct user profile (simplified - in production, fetch from DB)
        user_id = weekly_plan["user_id"]
        activity_level = day_to_regenerate["activity_level"]
        
        # TODO: Fetch actual user profile from database
        # For now, we'll need to pass it as a parameter or store it in the weekly plan
        
        logger.warning("Day regeneration requires user profile - implement DB fetch")
        
        return weekly_plan
    
    def regenerate_meal(
        self,
        weekly_plan: Dict,
        day_index: int,
        meal_type: str
    ) -> Dict:
        """
        Regenerate a specific meal in a specific day.
        
        Args:
            weekly_plan: Existing weekly plan
            day_index: Index of day (0-6)
            meal_type: Type of meal to regenerate
            
        Returns:
            Updated weekly plan
        """
        logger.info(f"Regenerating {meal_type} for day {day_index}")
        
        # TODO: Implement meal regeneration logic
        # Similar to swap functionality but within weekly context
        
        logger.warning("Meal regeneration not yet implemented")
        
        return weekly_plan

    
    def generate_and_save_weekly_plan(
        self,
        user_profile: UserProfile,
        activity_pattern: Dict[str, str] = None,
        start_date: datetime = None,
        max_recipe_repeats: int = 2
    ) -> Dict:
        """
        Generate weekly plan and save to database.
        
        Args:
            user_profile: User profile information
            activity_pattern: Dict mapping day names to activity levels
            start_date: Start date for the week
            max_recipe_repeats: Maximum times a recipe can repeat
            
        Returns:
            Generated weekly meal plan dictionary
        """
        # Generate the plan
        weekly_plan = self.generate_weekly_plan(
            user_profile=user_profile,
            activity_pattern=activity_pattern,
            start_date=start_date,
            max_recipe_repeats=max_recipe_repeats
        )
        
        # Save to database if repository available
        if self.repository:
            try:
                # Transform plan to match database schema
                db_plan_dict = self._transform_plan_for_db(weekly_plan)
                self.repository.create_weekly_plan(db_plan_dict)
                logger.info(f"Saved weekly plan {weekly_plan['week_plan_id']} to database")
            except Exception as e:
                logger.error(f"Failed to save weekly plan to database: {e}")
                # Continue without saving - plan is still returned
        
        return weekly_plan
    
    def regenerate_and_update_day(
        self,
        week_plan_id: str,
        day_index: int,
        user_profile: UserProfile,
        constraints: Optional[Dict] = None
    ) -> Dict:
        """
        Regenerate a day and update in database.
        
        Args:
            week_plan_id: Weekly plan identifier
            day_index: Day to regenerate (0-6)
            user_profile: User profile for regeneration
            constraints: Optional constraints
            
        Returns:
            Updated weekly plan dictionary
        """
        if not self.repository:
            raise ValueError("Database repository not available")
        
        # Load existing plan from database
        db_plan = self.repository.get_weekly_plan(week_plan_id)
        if not db_plan:
            raise ValueError(f"Weekly plan {week_plan_id} not found")
        
        # Convert to dict format
        weekly_plan = self._model_to_dict(db_plan)
        
        # Get the day to regenerate
        day_to_regenerate = weekly_plan['daily_plans'][day_index]
        activity_level = day_to_regenerate['activity_level']
        
        # Adjust profile for this day's activity
        adjusted_profile = self._adjust_profile_for_activity(user_profile, activity_level)
        
        # Calculate nutrition targets
        nutrition_targets = self.nutrition_engine.calculate_nutrition_targets(adjusted_profile)
        
        # Build recipe usage tracker (excluding this day)
        recipe_usage = Counter()
        for i, day_plan in enumerate(weekly_plan['daily_plans']):
            if i != day_index:  # Skip the day we're regenerating
                for meal in day_plan['meals']:
                    recipe_usage[meal['recipe_id']] += 1
        
        # Get meal candidates with variety constraints
        meal_candidates = {}
        for meal_type, target_kcal in nutrition_targets.meal_splits.items():
            candidates = self.rag_module.retrieve_candidates(
                meal_type=meal_type,
                target_kcal=target_kcal,
                diet_pref=adjusted_profile.diet_pref,
                allergens=adjusted_profile.allergies,
                top_k=10
            )
            
            filtered_candidates = self._filter_overused_recipes(
                candidates,
                recipe_usage,
                weekly_plan.get('max_recipe_repeats', 2)
            )
            
            meal_candidates[meal_type] = filtered_candidates[:3]
        
        # Generate new daily plan
        new_daily_plan = self.simple_planner.generate_plan(
            user_id=user_profile.user_id,
            meal_candidates=meal_candidates,
            meal_targets=nutrition_targets.meal_splits
        )
        
        # Update the day in weekly plan
        weekly_plan['daily_plans'][day_index]['meals'] = new_daily_plan['meals']
        weekly_plan['daily_plans'][day_index]['total_nutrition'] = new_daily_plan['total_nutrition']
        
        # Update in database
        day_plan_id = day_to_regenerate.get('day_plan_id')
        if day_plan_id:
            self.repository.update_daily_plan(day_plan_id, new_daily_plan['meals'])
        
        # Recalculate variety score
        all_recipe_ids = []
        for day_plan in weekly_plan['daily_plans']:
            for meal in day_plan['meals']:
                all_recipe_ids.append(meal['recipe_id'])
        
        unique_recipes = len(set(all_recipe_ids))
        total_meals = len(all_recipe_ids)
        weekly_plan['recipe_variety_score'] = unique_recipes / total_meals if total_meals > 0 else 0
        
        logger.info(f"Regenerated day {day_index} in weekly plan {week_plan_id}")
        
        return weekly_plan
    
    def _transform_plan_for_db(self, weekly_plan: Dict) -> Dict:
        """
        Transform weekly plan to match database schema.
        
        Args:
            weekly_plan: Weekly plan from generate_weekly_plan
            
        Returns:
            Transformed plan dictionary for database
        """
        # Transform days to daily_plans format
        daily_plans = []
        for day in weekly_plan['days']:
            meal_plan = day['meal_plan']
            
            daily_plan = {
                'plan_id': f"day_{uuid.uuid4().hex[:12]}",
                'day_index': day['day_index'],
                'date': day['date'],
                'day_name': day['day_name'],
                'activity_level': day['activity_level'],
                'adjusted_targets': day['nutrition_targets'],
                'total_nutrition': meal_plan['total_nutrition'],
                'nutrition_provenance': meal_plan.get('nutrition_provenance', 'calculated'),
                'plan_version': meal_plan.get('plan_version', 'v1.0'),
                'sources': meal_plan.get('sources', []),
                'meals': meal_plan['meals']
            }
            
            daily_plans.append(daily_plan)
        
        # Transform to database format
        db_plan = {
            'week_plan_id': weekly_plan['week_plan_id'],
            'user_id': weekly_plan['user_id'],
            'start_date': weekly_plan['start_date'],
            'end_date': weekly_plan['end_date'],
            'activity_pattern': weekly_plan['activity_pattern'],
            'recipe_variety_score': weekly_plan['weekly_stats']['variety_score'],
            'max_recipe_repeats': 2,  # Default value
            'variety_preference': 0.8,  # Default value
            'daily_plans': daily_plans,
            'generated_at': weekly_plan['created_at']
        }
        
        return db_plan
    
    def _model_to_dict(self, db_plan) -> Dict:
        """
        Convert database model to dictionary format.
        
        Args:
            db_plan: WeeklyPlanModel from database
            
        Returns:
            Dictionary representation
        """
        daily_plans = []
        for db_day in db_plan.daily_plans:
            meals = []
            for db_meal in db_day.meals:
                meal = {
                    'meal_type': db_meal.meal_type,
                    'recipe_id': db_meal.recipe_id,
                    'recipe_title': db_meal.recipe_title,
                    'servings': db_meal.servings,
                    'nutrition_per_serving': {
                        'kcal': db_meal.kcal_per_serving,
                        'protein_g': db_meal.protein_g_per_serving,
                        'carbs_g': db_meal.carbs_g_per_serving,
                        'fat_g': db_meal.fat_g_per_serving
                    },
                    'total_nutrition': {
                        'kcal': db_meal.total_kcal,
                        'protein_g': db_meal.total_protein_g,
                        'carbs_g': db_meal.total_carbs_g,
                        'fat_g': db_meal.total_fat_g
                    },
                    'ingredients': db_meal.ingredients,
                    'instructions': db_meal.instructions,
                    'prep_time_min': db_meal.prep_time_min,
                    'cook_time_min': db_meal.cook_time_min
                }
                meals.append(meal)
            
            daily_plan = {
                'day_plan_id': db_day.day_plan_id,
                'day_index': db_day.day_index,
                'date': db_day.date.isoformat(),
                'day_name': db_day.day_name,
                'activity_level': db_day.activity_level,
                'adjusted_targets': {
                    'target_kcal': db_day.target_kcal,
                    'protein_g': db_day.target_protein_g,
                    'carbs_g': db_day.target_carbs_g,
                    'fat_g': db_day.target_fat_g
                },
                'total_nutrition': {
                    'kcal': db_day.total_kcal,
                    'protein_g': db_day.total_protein_g,
                    'carbs_g': db_day.total_carbs_g,
                    'fat_g': db_day.total_fat_g
                },
                'meals': meals
            }
            daily_plans.append(daily_plan)
        
        weekly_plan = {
            'week_plan_id': db_plan.week_plan_id,
            'user_id': db_plan.user_id,
            'start_date': db_plan.start_date.isoformat(),
            'end_date': db_plan.end_date.isoformat(),
            'activity_pattern': db_plan.activity_pattern,
            'recipe_variety_score': db_plan.variety_score,
            'max_recipe_repeats': db_plan.max_recipe_repeats,
            'daily_plans': daily_plans
        }
        
        return weekly_plan
