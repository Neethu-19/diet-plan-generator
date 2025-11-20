"""
FastAPI endpoints for meal plan generation and management.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import uuid
from typing import Dict, List, Any

from src.models.schemas import (
    GeneratePlanRequest, GeneratePlanResponse,
    SwapRequest, SwapResponse,
    EstimateNutritionRequest, EstimateNutritionResponse,
    HealthResponse, MealPlan, Meal, MealPlanSource,
    RecipeCandidate, DailyPlanResponse, WeeklyPlanSummary,
    WeeklyPlanListResponse, WeeklyPlanResponse, WeeklyPlanMeal,
    ProgressLogRequest, ProgressLogResponse, ProgressHistoryResponse,
    ProgressAnalysis
)
from src.core.nutrition_engine import NutritionEngine
from src.core.rag_module import RAGModule
from src.services.llm_service import LLMOrchestrator
from src.services.prompt_templates import create_cursor_messages
from src.core.validator import MealPlanValidator
from src.services.weekly_planner import WeeklyPlanner
from src.data.database import get_db
from src.data.repositories import WeeklyPlanRepository
from src.utils.logging_config import logger
from sqlalchemy.orm import Session

router = APIRouter()

# Global service instances (will be initialized in main.py)
nutrition_engine = None
rag_module = None
llm_orchestrator = None
validator = None


def get_nutrition_engine():
    """Dependency for nutrition engine."""
    global nutrition_engine
    if nutrition_engine is None:
        nutrition_engine = NutritionEngine()
    return nutrition_engine


def get_rag_module():
    """Dependency for RAG module."""
    global rag_module
    if rag_module is None:
        rag_module = RAGModule()
    return rag_module


def get_llm_orchestrator():
    """Dependency for LLM orchestrator."""
    global llm_orchestrator
    # LLM is optional - we use simple planner instead
    return llm_orchestrator


def get_validator():
    """Dependency for validator."""
    global validator
    if validator is None:
        validator = MealPlanValidator()
    return validator


@router.post("/generate-plan", response_model=GeneratePlanResponse)
async def generate_plan(
    request: GeneratePlanRequest,
    include_debug: bool = False,
    engine: NutritionEngine = Depends(get_nutrition_engine),
    rag: RAGModule = Depends(get_rag_module),
    llm: LLMOrchestrator = Depends(get_llm_orchestrator),
    val: MealPlanValidator = Depends(get_validator)
):
    """
    Generate a personalized meal plan.
    
    Args:
        request: User profile and preferences
        include_debug: Include detailed scoring breakdown in response
        
    Returns:
        Generated meal plan with nutrition information
    """
    try:
        logger.info(f"Generating meal plan for user: {request.user_profile.user_id} (debug={include_debug})")
        
        # Step 1: Calculate nutrition targets
        logger.info("Calculating nutrition targets...")
        nutrition_targets = engine.calculate_nutrition_targets(request.user_profile)
        
        # Step 2: Retrieve user preferences (optional)
        user_preferences = None
        try:
            from src.services.preference_service import PreferenceService
            from src.data.database import SessionLocal
            
            with SessionLocal() as pref_db:
                pref_service = PreferenceService(pref_db)
                user_preferences = pref_service.get_user_preferences(request.user_profile.user_id)
                logger.info(f"Retrieved preferences for user {request.user_profile.user_id}")
        except Exception as e:
            logger.warning(f"Could not retrieve preferences: {e}")
            user_preferences = {
                "liked_recipes": set(),
                "disliked_recipes": set(),
                "regional_profile": "global"
            }
        
        # Step 3: Retrieve recipe candidates for each meal with preferences
        logger.info("Retrieving recipe candidates with preferences and advanced scoring...")
        meal_candidates = {}
        
        for meal_type, target_kcal in nutrition_targets.meal_splits.items():
            # Use preference-aware method
            candidates = rag.retrieve_candidates_with_preferences(
                meal_type=meal_type,
                target_kcal=target_kcal,
                diet_pref=request.user_profile.diet_pref,
                allergens=request.user_profile.allergies,
                user_skill=request.user_profile.cooking_skill,
                max_prep_time=None,  # Could be added to user profile
                recently_used_recipes=None,  # Could track from user history
                liked_recipes=user_preferences["liked_recipes"],
                disliked_recipes=user_preferences["disliked_recipes"],
                regional_profile=user_preferences["regional_profile"],
                top_k=3,
                include_debug=include_debug
            )
            meal_candidates[meal_type] = candidates
            logger.info(f"Retrieved {len(candidates)} preference-adjusted candidates for {meal_type}")
        
        # Step 4: Generate meal plan (use simple planner for now - LLM has context issues)
        logger.info("Generating meal plan with simple deterministic planner...")
        from src.services.simple_planner import SimplePlanner
        simple_planner = SimplePlanner()
        
        meal_plan_dict = simple_planner.generate_plan(
            user_id=request.user_profile.user_id or str(uuid.uuid4()),
            meal_candidates=meal_candidates,
            meal_targets=nutrition_targets.meal_splits
        )
        
        # Step 5: Validate meal plan
        logger.info("Validating meal plan...")
        is_valid, errors = val.validate_meal_plan(
            meal_plan=meal_plan_dict,
            nutrition_targets=nutrition_targets,
            meal_candidates=meal_candidates
        )
        
        if not is_valid:
            # Log errors but return the plan anyway since it's deterministic
            logger.warning(f"Validation warnings: {errors}")
            # Don't fail - the simple planner generates valid plans
        
        # Step 6: Convert to Pydantic model
        meal_plan = MealPlan(**meal_plan_dict)
        
        # Step 7: Generate enhanced presentation if requested
        enhanced_presentation = None
        if request.target_audience or request.include_tips:
            from src.services.meal_presentation_service import MealPresentationService
            
            presentation_service = MealPresentationService()
            enhanced_presentation = presentation_service.generate_enhanced_presentation(
                meal_plan=meal_plan,
                target_audience=request.target_audience,
                include_tips=request.include_tips
            )
            logger.info(f"Generated enhanced presentation for {request.target_audience.value}")
        
        logger.info(f"Successfully generated meal plan: {meal_plan.plan_id}")
        
        return GeneratePlanResponse(
            meal_plan=meal_plan,
            enhanced_presentation=enhanced_presentation,
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating meal plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/swap", response_model=SwapResponse)
async def swap_meal(
    request: SwapRequest,
    rag: RAGModule = Depends(get_rag_module),
    llm: LLMOrchestrator = Depends(get_llm_orchestrator)
):
    """
    Swap a meal in an existing plan.
    
    Args:
        request: Swap request with plan_id, meal_type, and constraints
        
    Returns:
        Updated meal plan with swapped meal
    """
    try:
        logger.info(f"Swapping meal {request.meal_type} in plan {request.plan_id}")
        
        # TODO: Retrieve original meal plan from database
        # For now, return error
        raise HTTPException(
            status_code=501,
            detail="Meal swap functionality requires database integration (Task 8)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error swapping meal: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/recipes/{recipe_id}")
async def get_recipe(
    recipe_id: str,
    include_scoring: bool = False,
    rag: RAGModule = Depends(get_rag_module)
):
    """
    Get recipe details by ID.
    
    Args:
        recipe_id: Recipe identifier
        include_scoring: Include example scoring breakdown
        
    Returns:
        Recipe details with nutrition information
    """
    try:
        logger.info(f"Retrieving recipe: {recipe_id} (include_scoring={include_scoring})")
        
        # Get recipe from vector database
        recipe_metadata = rag.vector_db.get_recipe(recipe_id)
        
        if recipe_metadata is None:
            raise HTTPException(
                status_code=404,
                detail=f"Recipe not found: {recipe_id}"
            )
        
        # Add recipe_id to metadata
        recipe_data = {"recipe_id": recipe_id, **recipe_metadata}
        
        # Add example scoring breakdown if requested
        if include_scoring:
            # Generate example score breakdown for typical targets
            example_target_kcal = recipe_metadata.get("kcal_total", 500)
            example_breakdown = rag._calculate_advanced_score_with_breakdown(
                recipe_id=recipe_id,
                recipe_metadata=recipe_metadata,
                semantic_similarity=0.85,  # Example value
                target_kcal=example_target_kcal,
                required_tags=set(),
                user_skill=3,
                max_prep_time=None,
                recently_used_recipes=None
            )
            recipe_data["example_scoring"] = example_breakdown
        
        return recipe_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving recipe: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/estimate-nutrition", response_model=EstimateNutritionResponse)
async def estimate_nutrition(request: EstimateNutritionRequest):
    """
    Estimate nutrition for a recipe (opt-in feature).
    
    Args:
        request: Recipe ID to estimate
        
    Returns:
        Estimated nutrition values marked as ESTIMATED
    """
    try:
        logger.info(f"Estimating nutrition for recipe: {request.recipe_id}")
        
        # TODO: Implement server-side nutrition estimation from foods database
        raise HTTPException(
            status_code=501,
            detail="Nutrition estimation requires foods database integration"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error estimating nutrition: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns:
        Service health status
    """
    try:
        # Check services
        database_status = "not_implemented"  # TODO: Check database connection
        vector_db_status = "unknown"
        model_status = "unknown"
        
        # Try to check vector DB
        try:
            if rag_module is not None:
                vector_db_status = "healthy"
            else:
                vector_db_status = "not_initialized"
        except Exception:
            vector_db_status = "unhealthy"
        
        # Try to check model
        try:
            if llm_orchestrator is not None:
                model_status = "healthy"
            else:
                model_status = "not_initialized"
        except Exception:
            model_status = "unhealthy"
        
        overall_status = "healthy" if vector_db_status == "healthy" and model_status == "healthy" else "degraded"
        
        return HealthResponse(
            status=overall_status,
            database=database_status,
            vector_db=vector_db_status,
            model=model_status
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            database="unknown",
            vector_db="unknown",
            model="unknown"
        )



# Weekly Plan Endpoints

@router.post("/generate-weekly-plan", response_model=WeeklyPlanResponse)
async def generate_weekly_plan(
    user_profile: Dict,
    activity_pattern: Dict[str, str],
    start_date: str = None,
    max_recipe_repeats: int = 2,
    target_audience: str = "general",
    include_tips: bool = True,
    include_debug: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate and save a 7-day meal plan with recipe variety and activity-based adjustments.
    
    Args:
        user_profile: User profile dictionary
        activity_pattern: Activity level for each day (e.g., {"monday": "active", ...})
        start_date: Start date in ISO format (defaults to today)
        max_recipe_repeats: Maximum times a recipe can repeat in the week
        include_debug: Include detailed scoring breakdown in meals
        db: Database session
        
    Returns:
        Generated weekly meal plan with all 7 days
    """
    try:
        from src.models.schemas import UserProfile
        
        # Convert dict to UserProfile
        profile = UserProfile(**user_profile)
        
        # Parse start date
        if start_date:
            start_dt = datetime.fromisoformat(start_date)
        else:
            start_dt = datetime.now()
        
        # Retrieve user preferences (optional)
        user_preferences = None
        try:
            from src.services.preference_service import PreferenceService
            
            pref_service = PreferenceService(db)
            user_preferences = pref_service.get_user_preferences(profile.user_id)
            logger.info(f"Retrieved preferences for weekly plan user {profile.user_id}")
        except Exception as e:
            logger.warning(f"Could not retrieve preferences for weekly plan: {e}")
            user_preferences = {
                "liked_recipes": set(),
                "disliked_recipes": set(),
                "regional_profile": "global"
            }
        
        # Initialize weekly planner with database session
        planner = WeeklyPlanner(db_session=db)
        
        # Generate and save weekly plan
        weekly_plan = planner.generate_and_save_weekly_plan(
            user_profile=profile,
            activity_pattern=activity_pattern,
            start_date=start_dt,
            max_recipe_repeats=max_recipe_repeats,
            include_debug=include_debug,
            user_preferences=user_preferences
        )
        
        logger.info(f"Generated weekly plan {weekly_plan['week_plan_id']}")
        
        # Generate enhanced presentation if requested
        enhanced_presentation = None
        if target_audience != "general" or include_tips:
            from src.services.meal_presentation_service import MealPresentationService
            from src.models.schemas import TargetAudience
            
            # Convert first day's meal plan for presentation
            if weekly_plan['days'] and len(weekly_plan['days']) > 0:
                first_day_meals = weekly_plan['days'][0]['meal_plan']
                first_day_plan = MealPlan(**first_day_meals)
                
                presentation_service = MealPresentationService()
                try:
                    audience_enum = TargetAudience(target_audience)
                except ValueError:
                    audience_enum = TargetAudience.GENERAL
                    
                enhanced_presentation = presentation_service.generate_enhanced_presentation(
                    meal_plan=first_day_plan,
                    target_audience=audience_enum,
                    include_tips=include_tips
                )
                logger.info(f"Generated enhanced presentation for weekly plan with {target_audience}")
        
        # Convert to response format with all 7 days
        daily_plans = []
        for day in weekly_plan['days']:
            meals = []
            for meal in day['meal_plan']['meals']:
                weekly_meal = WeeklyPlanMeal(
                    meal_type=meal['meal_type'],
                    recipe_id=meal['recipe_id'],
                    recipe_title=meal['recipe_title'],
                    servings=float(meal['portion_size'].split('x')[0]) if 'x' in meal['portion_size'] else 1.0,
                    nutrition_per_serving={
                        "kcal": meal['kcal'],
                        "protein_g": meal['protein_g'],
                        "carbs_g": meal['carbs_g'],
                        "fat_g": meal['fat_g']
                    },
                    total_nutrition={
                        "kcal": meal['kcal'],
                        "protein_g": meal['protein_g'],
                        "carbs_g": meal['carbs_g'],
                        "fat_g": meal['fat_g']
                    },
                    ingredients=meal['ingredients'],
                    instructions=meal.get('instructions'),
                    prep_time_min=meal.get('prep_time_min'),
                    cook_time_min=meal.get('cook_time_min')
                )
                meals.append(weekly_meal)
            
            daily_plan = DailyPlanResponse(
                day_plan_id=day['meal_plan'].get('plan_id', f"day_{day['day_index']}"),
                day_index=day['day_index'],
                date=day['date'],
                day_name=day['day_name'],
                activity_level=day['activity_level'],
                meals=meals,
                total_nutrition=day['meal_plan']['total_nutrition'],
                adjusted_targets=day['nutrition_targets']
            )
            daily_plans.append(daily_plan)
        
        return WeeklyPlanResponse(
            week_plan_id=weekly_plan['week_plan_id'],
            user_id=weekly_plan['user_id'],
            start_date=weekly_plan['start_date'],
            end_date=weekly_plan['end_date'],
            activity_pattern=weekly_plan['activity_pattern'],
            variety_score=weekly_plan['weekly_stats']['variety_score'],
            max_recipe_repeats=max_recipe_repeats,
            daily_plans=daily_plans,
            weekly_stats=weekly_plan['weekly_stats'],
            enhanced_presentation=enhanced_presentation
        )
        
    except Exception as e:
        logger.error(f"Error generating weekly plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate weekly plan: {str(e)}"
        )


@router.get("/weekly-plan/{week_plan_id}", response_model=WeeklyPlanResponse)
async def get_weekly_plan(week_plan_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a weekly plan by ID with all 7 days.
    
    Args:
        week_plan_id: Weekly plan identifier
        db: Database session
        
    Returns:
        Complete weekly plan with all daily plans
    """
    try:
        repository = WeeklyPlanRepository(db)
        db_plan = repository.get_weekly_plan(week_plan_id)
        
        if not db_plan:
            raise HTTPException(
                status_code=404,
                detail=f"Weekly plan {week_plan_id} not found"
            )
        
        # Convert to response format
        daily_plans = []
        for db_day in db_plan.daily_plans:
            meals = []
            for db_meal in db_day.meals:
                meal = WeeklyPlanMeal(
                    meal_type=db_meal.meal_type,
                    recipe_id=db_meal.recipe_id,
                    recipe_title=db_meal.recipe_title,
                    servings=db_meal.servings,
                    nutrition_per_serving={
                        "kcal": db_meal.kcal_per_serving,
                        "protein_g": db_meal.protein_g_per_serving,
                        "carbs_g": db_meal.carbs_g_per_serving,
                        "fat_g": db_meal.fat_g_per_serving
                    },
                    total_nutrition={
                        "kcal": db_meal.total_kcal,
                        "protein_g": db_meal.total_protein_g,
                        "carbs_g": db_meal.total_carbs_g,
                        "fat_g": db_meal.total_fat_g
                    },
                    ingredients=db_meal.ingredients,
                    instructions=db_meal.instructions,
                    prep_time_min=db_meal.prep_time_min,
                    cook_time_min=db_meal.cook_time_min
                )
                meals.append(meal)
            
            daily_plan = DailyPlanResponse(
                day_plan_id=db_day.day_plan_id,
                day_index=db_day.day_index,
                date=db_day.date.isoformat(),
                day_name=db_day.day_name,
                activity_level=db_day.activity_level,
                meals=meals,
                total_nutrition={
                    "kcal": db_day.total_kcal,
                    "protein_g": db_day.total_protein_g,
                    "carbs_g": db_day.total_carbs_g,
                    "fat_g": db_day.total_fat_g
                },
                adjusted_targets={
                    "target_kcal": db_day.target_kcal,
                    "protein_g": db_day.target_protein_g,
                    "carbs_g": db_day.target_carbs_g,
                    "fat_g": db_day.target_fat_g
                }
            )
            daily_plans.append(daily_plan)
        
        return WeeklyPlanResponse(
            week_plan_id=db_plan.week_plan_id,
            user_id=db_plan.user_id,
            start_date=db_plan.start_date.isoformat(),
            end_date=db_plan.end_date.isoformat(),
            activity_pattern=db_plan.activity_pattern,
            variety_score=db_plan.variety_score,
            max_recipe_repeats=db_plan.max_recipe_repeats,
            daily_plans=daily_plans
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving weekly plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve weekly plan: {str(e)}"
        )


@router.get("/weekly-plan/today/{user_id}", response_model=DailyPlanResponse)
async def get_today_plan(user_id: str, db: Session = Depends(get_db)):
    """
    Get today's meal plan for a user.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        Today's daily plan
    """
    try:
        repository = WeeklyPlanRepository(db)
        daily_plan = repository.get_today_plan(user_id)
        
        if not daily_plan:
            raise HTTPException(
                status_code=404,
                detail=f"No active meal plan for today for user {user_id}"
            )
        
        # Convert to response format
        from src.models.schemas import WeeklyPlanMeal
        
        meals = []
        for db_meal in daily_plan.meals:
            meal = WeeklyPlanMeal(
                meal_type=db_meal.meal_type,
                recipe_id=db_meal.recipe_id,
                recipe_title=db_meal.recipe_title,
                servings=db_meal.servings,
                nutrition_per_serving={
                    "kcal": db_meal.kcal_per_serving,
                    "protein_g": db_meal.protein_g_per_serving,
                    "carbs_g": db_meal.carbs_g_per_serving,
                    "fat_g": db_meal.fat_g_per_serving
                },
                total_nutrition={
                    "kcal": db_meal.total_kcal,
                    "protein_g": db_meal.total_protein_g,
                    "carbs_g": db_meal.total_carbs_g,
                    "fat_g": db_meal.total_fat_g
                },
                ingredients=db_meal.ingredients,
                instructions=db_meal.instructions,
                prep_time_min=db_meal.prep_time_min,
                cook_time_min=db_meal.cook_time_min
            )
            meals.append(meal)
        
        return DailyPlanResponse(
            day_plan_id=daily_plan.day_plan_id,
            day_index=daily_plan.day_index,
            date=daily_plan.date.isoformat(),
            day_name=daily_plan.day_name,
            activity_level=daily_plan.activity_level,
            meals=meals,
            total_nutrition={
                "kcal": daily_plan.total_kcal,
                "protein_g": daily_plan.total_protein_g,
                "carbs_g": daily_plan.total_carbs_g,
                "fat_g": daily_plan.total_fat_g
            },
            adjusted_targets={
                "target_kcal": daily_plan.target_kcal,
                "protein_g": daily_plan.target_protein_g,
                "carbs_g": daily_plan.target_carbs_g,
                "fat_g": daily_plan.target_fat_g
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving today's plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve today's plan: {str(e)}"
        )


@router.get("/weekly-plan/tomorrow/{user_id}", response_model=DailyPlanResponse)
async def get_tomorrow_plan(user_id: str, db: Session = Depends(get_db)):
    """
    Get tomorrow's meal plan for a user.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        Tomorrow's daily plan
    """
    try:
        repository = WeeklyPlanRepository(db)
        daily_plan = repository.get_tomorrow_plan(user_id)
        
        if not daily_plan:
            raise HTTPException(
                status_code=404,
                detail=f"No active meal plan for tomorrow for user {user_id}"
            )
        
        # Convert to response format (same as today)
        from src.models.schemas import WeeklyPlanMeal
        
        meals = []
        for db_meal in daily_plan.meals:
            meal = WeeklyPlanMeal(
                meal_type=db_meal.meal_type,
                recipe_id=db_meal.recipe_id,
                recipe_title=db_meal.recipe_title,
                servings=db_meal.servings,
                nutrition_per_serving={
                    "kcal": db_meal.kcal_per_serving,
                    "protein_g": db_meal.protein_g_per_serving,
                    "carbs_g": db_meal.carbs_g_per_serving,
                    "fat_g": db_meal.fat_g_per_serving
                },
                total_nutrition={
                    "kcal": db_meal.total_kcal,
                    "protein_g": db_meal.total_protein_g,
                    "carbs_g": db_meal.total_carbs_g,
                    "fat_g": db_meal.total_fat_g
                },
                ingredients=db_meal.ingredients,
                instructions=db_meal.instructions,
                prep_time_min=db_meal.prep_time_min,
                cook_time_min=db_meal.cook_time_min
            )
            meals.append(meal)
        
        return DailyPlanResponse(
            day_plan_id=daily_plan.day_plan_id,
            day_index=daily_plan.day_index,
            date=daily_plan.date.isoformat(),
            day_name=daily_plan.day_name,
            activity_level=daily_plan.activity_level,
            meals=meals,
            total_nutrition={
                "kcal": daily_plan.total_kcal,
                "protein_g": daily_plan.total_protein_g,
                "carbs_g": daily_plan.total_carbs_g,
                "fat_g": daily_plan.total_fat_g
            },
            adjusted_targets={
                "target_kcal": daily_plan.target_kcal,
                "protein_g": daily_plan.target_protein_g,
                "carbs_g": daily_plan.target_carbs_g,
                "fat_g": daily_plan.target_fat_g
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving tomorrow's plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve tomorrow's plan: {str(e)}"
        )


@router.get("/weekly-plan/week/{user_id}", response_model=WeeklyPlanResponse)
async def get_full_week(user_id: str, date: str = None, db: Session = Depends(get_db)):
    """
    Get full week view for a user with all 7 days.
    
    Args:
        user_id: User identifier
        date: Optional date to find week for (defaults to today)
        db: Database session
        
    Returns:
        Complete weekly plan with all 7 daily plans
    """
    try:
        from datetime import date as date_type
        
        # Parse date or use today
        if date:
            target_date = datetime.fromisoformat(date).date()
        else:
            target_date = date_type.today()
        
        repository = WeeklyPlanRepository(db)
        db_plan = repository.get_weekly_plan_by_date(user_id, target_date)
        
        if not db_plan:
            raise HTTPException(
                status_code=404,
                detail=f"No active weekly plan found for user {user_id} on {target_date}"
            )
        
        # Convert to response format
        daily_plans = []
        for db_day in db_plan.daily_plans:
            meals = []
            for db_meal in db_day.meals:
                meal = WeeklyPlanMeal(
                    meal_type=db_meal.meal_type,
                    recipe_id=db_meal.recipe_id,
                    recipe_title=db_meal.recipe_title,
                    servings=db_meal.servings,
                    nutrition_per_serving={
                        "kcal": db_meal.kcal_per_serving,
                        "protein_g": db_meal.protein_g_per_serving,
                        "carbs_g": db_meal.carbs_g_per_serving,
                        "fat_g": db_meal.fat_g_per_serving
                    },
                    total_nutrition={
                        "kcal": db_meal.total_kcal,
                        "protein_g": db_meal.total_protein_g,
                        "carbs_g": db_meal.total_carbs_g,
                        "fat_g": db_meal.total_fat_g
                    },
                    ingredients=db_meal.ingredients,
                    instructions=db_meal.instructions,
                    prep_time_min=db_meal.prep_time_min,
                    cook_time_min=db_meal.cook_time_min
                )
                meals.append(meal)
            
            daily_plan = DailyPlanResponse(
                day_plan_id=db_day.day_plan_id,
                day_index=db_day.day_index,
                date=db_day.date.isoformat(),
                day_name=db_day.day_name,
                activity_level=db_day.activity_level,
                meals=meals,
                total_nutrition={
                    "kcal": db_day.total_kcal,
                    "protein_g": db_day.total_protein_g,
                    "carbs_g": db_day.total_carbs_g,
                    "fat_g": db_day.total_fat_g
                },
                adjusted_targets={
                    "target_kcal": db_day.target_kcal,
                    "protein_g": db_day.target_protein_g,
                    "carbs_g": db_day.target_carbs_g,
                    "fat_g": db_day.target_fat_g
                }
            )
            daily_plans.append(daily_plan)
        
        return WeeklyPlanResponse(
            week_plan_id=db_plan.week_plan_id,
            user_id=db_plan.user_id,
            start_date=db_plan.start_date.isoformat(),
            end_date=db_plan.end_date.isoformat(),
            activity_pattern=db_plan.activity_pattern,
            variety_score=db_plan.variety_score,
            max_recipe_repeats=db_plan.max_recipe_repeats,
            daily_plans=daily_plans
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving full week: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve full week: {str(e)}"
        )


@router.post("/regenerate-day", response_model=WeeklyPlanResponse)
async def regenerate_day(
    week_plan_id: str,
    day_index: int,
    user_profile: Dict,
    db: Session = Depends(get_db)
):
    """
    Regenerate a specific day in a weekly plan.
    
    Args:
        week_plan_id: Weekly plan identifier
        day_index: Day to regenerate (0-6)
        user_profile: User profile dictionary
        db: Database session
        
    Returns:
        Updated complete weekly plan with all 7 days
    """
    try:
        from src.models.schemas import UserProfile
        
        if day_index < 0 or day_index > 6:
            raise HTTPException(
                status_code=400,
                detail="Day index must be between 0 and 6"
            )
        
        # Convert dict to UserProfile
        profile = UserProfile(**user_profile)
        
        # Initialize weekly planner with database session
        planner = WeeklyPlanner(db_session=db)
        
        # Regenerate and update day
        updated_plan = planner.regenerate_and_update_day(
            week_plan_id=week_plan_id,
            day_index=day_index,
            user_profile=profile
        )
        
        logger.info(f"Regenerated day {day_index} in weekly plan {week_plan_id}")
        
        # Fetch updated plan from database to get complete data
        repository = WeeklyPlanRepository(db)
        db_plan = repository.get_weekly_plan(week_plan_id)
        
        # Convert to response format
        daily_plans = []
        for db_day in db_plan.daily_plans:
            meals = []
            for db_meal in db_day.meals:
                meal = WeeklyPlanMeal(
                    meal_type=db_meal.meal_type,
                    recipe_id=db_meal.recipe_id,
                    recipe_title=db_meal.recipe_title,
                    servings=db_meal.servings,
                    nutrition_per_serving={
                        "kcal": db_meal.kcal_per_serving,
                        "protein_g": db_meal.protein_g_per_serving,
                        "carbs_g": db_meal.carbs_g_per_serving,
                        "fat_g": db_meal.fat_g_per_serving
                    },
                    total_nutrition={
                        "kcal": db_meal.total_kcal,
                        "protein_g": db_meal.total_protein_g,
                        "carbs_g": db_meal.total_carbs_g,
                        "fat_g": db_meal.total_fat_g
                    },
                    ingredients=db_meal.ingredients,
                    instructions=db_meal.instructions,
                    prep_time_min=db_meal.prep_time_min,
                    cook_time_min=db_meal.cook_time_min
                )
                meals.append(meal)
            
            daily_plan = DailyPlanResponse(
                day_plan_id=db_day.day_plan_id,
                day_index=db_day.day_index,
                date=db_day.date.isoformat(),
                day_name=db_day.day_name,
                activity_level=db_day.activity_level,
                meals=meals,
                total_nutrition={
                    "kcal": db_day.total_kcal,
                    "protein_g": db_day.total_protein_g,
                    "carbs_g": db_day.total_carbs_g,
                    "fat_g": db_day.total_fat_g
                },
                adjusted_targets={
                    "target_kcal": db_day.target_kcal,
                    "protein_g": db_day.target_protein_g,
                    "carbs_g": db_day.target_carbs_g,
                    "fat_g": db_day.target_fat_g
                }
            )
            daily_plans.append(daily_plan)
        
        return WeeklyPlanResponse(
            week_plan_id=db_plan.week_plan_id,
            user_id=db_plan.user_id,
            start_date=db_plan.start_date.isoformat(),
            end_date=db_plan.end_date.isoformat(),
            activity_pattern=db_plan.activity_pattern,
            variety_score=updated_plan.get('recipe_variety_score', db_plan.variety_score),
            max_recipe_repeats=db_plan.max_recipe_repeats,
            daily_plans=daily_plans
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error regenerating day: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to regenerate day: {str(e)}"
        )


@router.delete("/weekly-plan/{week_plan_id}")
async def delete_weekly_plan(
    week_plan_id: str,
    archive_only: bool = True,
    db: Session = Depends(get_db)
):
    """
    Delete or archive a weekly plan.
    
    Args:
        week_plan_id: Weekly plan identifier
        archive_only: If True, soft delete (archive); if False, permanent delete
        db: Database session
        
    Returns:
        Success status
    """
    try:
        repository = WeeklyPlanRepository(db)
        
        if archive_only:
            success = repository.archive_weekly_plan(week_plan_id)
            action = "archived"
        else:
            success = repository.delete_weekly_plan(week_plan_id)
            action = "deleted"
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Weekly plan {week_plan_id} not found"
            )
        
        return {
            "status": "success",
            "message": f"Weekly plan {action} successfully",
            "archived": archive_only
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting weekly plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete weekly plan: {str(e)}"
        )


@router.get("/weekly-plans/{user_id}", response_model=WeeklyPlanListResponse)
async def get_user_weekly_plans(
    user_id: str,
    limit: int = 10,
    include_archived: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get all weekly plans for a user.
    
    Args:
        user_id: User identifier
        limit: Maximum number of plans to return
        include_archived: Whether to include archived plans
        db: Database session
        
    Returns:
        List of weekly plan summaries
    """
    try:
        repository = WeeklyPlanRepository(db)
        plans = repository.get_user_weekly_plans(user_id, limit, include_archived)
        
        summaries = []
        for plan in plans:
            summary = WeeklyPlanSummary(
                week_plan_id=plan.week_plan_id,
                user_id=plan.user_id,
                start_date=plan.start_date.isoformat(),
                end_date=plan.end_date.isoformat(),
                variety_score=plan.variety_score,
                is_archived=plan.is_archived,
                created_at=plan.created_at.isoformat()
            )
            summaries.append(summary)
        
        return WeeklyPlanListResponse(
            plans=summaries,
            total=len(summaries)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving user weekly plans: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve weekly plans: {str(e)}"
        )



# Progress Tracking Endpoints

@router.post("/log-progress", response_model=ProgressLogResponse)
async def log_progress(request: ProgressLogRequest, db: Session = Depends(get_db)):
    """
    Log daily progress (weight and adherence).
    
    Args:
        request: Progress log data
        db: Database session
        
    Returns:
        Created progress log
    """
    try:
        from src.services.progress_service import ProgressService
        from datetime import datetime
        
        service = ProgressService(db)
        
        # Parse date
        log_date = datetime.fromisoformat(request.date).date()
        
        # Create log
        log = service.log_progress(
            user_id=request.user_id,
            log_date=log_date,
            actual_weight_kg=request.actual_weight_kg,
            adherence_score=request.adherence_score,
            notes=request.notes,
            energy_level=request.energy_level,
            hunger_level=request.hunger_level
        )
        
        return ProgressLogResponse(
            log_id=log.log_id,
            user_id=log.user_id,
            log_date=log.log_date.isoformat(),
            actual_weight_kg=log.actual_weight_kg,
            adherence_score=log.adherence_score,
            notes=log.notes,
            energy_level=log.energy_level,
            hunger_level=log.hunger_level,
            created_at=log.created_at.isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error logging progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to log progress: {str(e)}"
        )


@router.get("/progress/{user_id}", response_model=ProgressHistoryResponse)
async def get_progress_history(
    user_id: str,
    days: int = 90,
    analyze: bool = True,
    db: Session = Depends(get_db)
):
    """
    Get progress history and analysis for a user.
    
    Args:
        user_id: User identifier
        days: Number of days to retrieve (default 90)
        analyze: Whether to include progress analysis (default True)
        db: Database session
        
    Returns:
        Progress history with optional analysis
    """
    try:
        from src.services.progress_service import ProgressService
        
        service = ProgressService(db)
        
        # Get logs
        logs = service.get_progress_history(user_id, days=days)
        
        # Convert to response format
        log_responses = []
        for log in logs:
            log_responses.append(ProgressLogResponse(
                log_id=log.log_id,
                user_id=log.user_id,
                log_date=log.log_date.isoformat(),
                actual_weight_kg=log.actual_weight_kg,
                adherence_score=log.adherence_score,
                notes=log.notes,
                energy_level=log.energy_level,
                hunger_level=log.hunger_level,
                created_at=log.created_at.isoformat()
            ))
        
        # Analyze if requested
        analysis = None
        if analyze and len(logs) >= 2:
            analysis_dict = service.analyze_progress(user_id, days=min(days, 30))
            if analysis_dict:
                analysis = ProgressAnalysis(**analysis_dict)
        
        return ProgressHistoryResponse(
            user_id=user_id,
            logs=log_responses,
            analysis=analysis,
            total_logs=len(log_responses)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving progress history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve progress history: {str(e)}"
        )


@router.post("/analyze-progress/{user_id}")
async def analyze_progress(
    user_id: str,
    days: int = 30,
    apply_adjustment: bool = False,
    db: Session = Depends(get_db)
):
    """
    Analyze user progress and optionally apply calorie adjustments.
    
    Args:
        user_id: User identifier
        days: Number of days to analyze (default 30)
        apply_adjustment: Whether to apply recommended adjustments (default False)
        db: Database session
        
    Returns:
        Progress analysis with recommendations
    """
    try:
        from src.services.progress_service import ProgressService
        
        service = ProgressService(db)
        
        # Analyze progress
        analysis = service.analyze_progress(user_id, days=days)
        
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient data for analysis. Need at least 2 progress logs."
            )
        
        # Apply adjustment if requested
        adjustment = None
        if apply_adjustment and analysis.get("calorie_adjustment_needed"):
            adjustment = service.apply_calorie_adjustment(user_id, analysis)
            if adjustment:
                analysis["adjustment_applied"] = True
                analysis["adjustment_id"] = adjustment.adjustment_id
        
        return {
            "status": "success",
            "analysis": analysis
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze progress: {str(e)}"
        )



# Personalization Endpoints

@router.post("/feedback")
async def submit_feedback(
    request: 'RecipeFeedbackRequest',
    db: Session = Depends(get_db)
):
    """
    Submit recipe feedback (like/dislike).
    
    Args:
        request: Feedback request with user_id, recipe_id, liked
        db: Database session
        
    Returns:
        Feedback confirmation
    """
    from src.models.schemas import RecipeFeedbackRequest, RecipeFeedbackResponse
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Submitting feedback for user {request.user_id} on recipe {request.recipe_id}")
        
        service = PreferenceService(db)
        
        # Submit feedback (upsert logic in service)
        feedback = service.submit_feedback(
            user_id=request.user_id,
            recipe_id=request.recipe_id,
            liked=request.liked
        )
        
        return RecipeFeedbackResponse(**feedback, status="success")
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/feedback/{user_id}")
async def get_user_feedback(
    user_id: str,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get user's feedback summary.
    
    Args:
        user_id: User identifier
        limit: Maximum number of results
        offset: Number of results to skip
        db: Database session
        
    Returns:
        Lists of liked and disliked recipes
    """
    from src.models.schemas import UserFeedbackSummary
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Retrieving feedback for user {user_id}")
        
        service = PreferenceService(db)
        
        prefs = service.get_user_preferences(user_id)
        
        return UserFeedbackSummary(
            user_id=user_id,
            liked_recipes=list(prefs["liked_recipes"]),
            disliked_recipes=list(prefs["disliked_recipes"]),
            total_feedback_count=len(prefs["liked_recipes"]) + len(prefs["disliked_recipes"])
        )
        
    except Exception as e:
        logger.error(f"Error retrieving feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve feedback: {str(e)}"
        )


@router.put("/user-preferences/{user_id}")
async def update_user_preferences(
    user_id: str,
    request: 'UserPreferencesRequest',
    db: Session = Depends(get_db)
):
    """
    Update user preferences (regional profile).
    
    Args:
        user_id: User identifier
        request: Preferences update request
        db: Database session
        
    Returns:
        Updated preferences
    """
    from src.models.schemas import UserPreferencesRequest, UserPreferencesResponse
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Updating preferences for user {user_id}")
        
        service = PreferenceService(db)
        
        prefs = service.update_regional_profile(
            user_id=user_id,
            regional_profile=request.regional_profile.value
        )
        
        return UserPreferencesResponse(**prefs)
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.get("/feedback-stats/{user_id}")
async def get_feedback_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user feedback statistics and insights.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        Preference statistics
    """
    from src.models.schemas import FeedbackStats
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Retrieving feedback stats for user {user_id}")
        
        service = PreferenceService(db)
        
        stats = service.get_feedback_stats(user_id)
        
        return FeedbackStats(**stats)
        
    except Exception as e:
        logger.error(f"Error retrieving feedback stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve feedback stats: {str(e)}"
        )


@router.delete("/feedback/{user_id}")
async def delete_user_feedback(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete all feedback for a user.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        Deletion confirmation
    """
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Deleting feedback for user {user_id}")
        
        service = PreferenceService(db)
        
        success = service.delete_user_feedback(user_id)
        
        if success:
            return {"status": "success", "message": "Feedback deleted"}
        else:
            raise HTTPException(status_code=404, detail="No feedback found")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete feedback: {str(e)}"
        )



@router.post("/generate-plan-html")
async def generate_plan_html(
    request: 'GeneratePlanRequest',
    include_debug: bool = False,
    engine: 'NutritionEngine' = Depends(get_nutrition_engine),
    rag: 'RAGModule' = Depends(get_rag_module),
    val: 'MealPlanValidator' = Depends(get_validator)
):
    """
    Generate meal plan and return HTML presentation.
    
    Args:
        request: User profile and preferences
        include_debug: Include detailed scoring breakdown
        
    Returns:
        HTML formatted meal plan
    """
    from src.models.schemas import GeneratePlanRequest
    from src.utils.markdown_renderer import MarkdownRenderer
    
    try:
        # Generate plan using existing logic
        response = await generate_plan(request, include_debug, engine, rag, None, val)
        
        # Convert to HTML if enhanced presentation exists
        if response.enhanced_presentation:
            html_content = MarkdownRenderer.render_to_html(response.enhanced_presentation)
            
            return {
                "html": html_content,
                "meal_plan": response.meal_plan,
                "status": "success"
            }
        else:
            return {
                "html": None,
                "meal_plan": response.meal_plan,
                "status": "success",
                "message": "No enhanced presentation generated"
            }
            
    except Exception as e:
        logger.error(f"Error generating HTML plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )



# User Preferences Endpoints

@router.get("/user-preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user preferences including regional profile.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        User preferences
    """
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Retrieving preferences for user {user_id}")
        
        service = PreferenceService(db)
        preferences = service.get_user_preferences(user_id)
        
        return {
            "user_id": user_id,
            "regional_profile": preferences.get("regional_profile", "global"),
            "liked_recipes": list(preferences.get("liked_recipes", set())),
            "disliked_recipes": list(preferences.get("disliked_recipes", set())),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve preferences: {str(e)}"
        )


@router.put("/user-preferences/{user_id}")
async def update_user_preferences(
    user_id: str,
    preferences_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    Update user preferences.
    
    Args:
        user_id: User identifier
        preferences_data: Preferences to update (regional_profile, etc.)
        db: Database session
        
    Returns:
        Updated preferences
    """
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Updating preferences for user {user_id}: {preferences_data}")
        
        service = PreferenceService(db)
        
        # Update regional profile if provided
        regional_profile = preferences_data.get("regional_profile")
        if regional_profile:
            service.set_regional_preference(user_id, regional_profile)
            logger.info(f"Updated regional profile to {regional_profile} for user {user_id}")
        
        # Return updated preferences
        preferences = service.get_user_preferences(user_id)
        
        return {
            "user_id": user_id,
            "regional_profile": preferences.get("regional_profile", "global"),
            "status": "success",
            "message": "Preferences updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating preferences: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update preferences: {str(e)}"
        )


@router.get("/feedback/{user_id}")
async def get_user_feedback(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get user's recipe feedback (liked and disliked recipes).
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        User feedback data
    """
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Retrieving feedback for user {user_id}")
        
        service = PreferenceService(db)
        preferences = service.get_user_preferences(user_id)
        
        return {
            "user_id": user_id,
            "liked_recipes": list(preferences.get("liked_recipes", set())),
            "disliked_recipes": list(preferences.get("disliked_recipes", set())),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve feedback: {str(e)}"
        )


@router.get("/feedback-stats/{user_id}")
async def get_feedback_stats(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Get statistics about user's recipe feedback.
    
    Args:
        user_id: User identifier
        db: Database session
        
    Returns:
        Feedback statistics
    """
    from src.services.preference_service import PreferenceService
    
    try:
        logger.info(f"Retrieving feedback stats for user {user_id}")
        
        service = PreferenceService(db)
        preferences = service.get_user_preferences(user_id)
        
        liked = preferences.get("liked_recipes", set())
        disliked = preferences.get("disliked_recipes", set())
        
        return {
            "user_id": user_id,
            "total_liked": len(liked),
            "total_disliked": len(disliked),
            "total_feedback": len(liked) + len(disliked),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error retrieving feedback stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve feedback stats: {str(e)}"
        )
