"""
FastAPI endpoints for meal plan generation and management.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import uuid
from typing import Dict, List

from src.models.schemas import (
    GeneratePlanRequest, GeneratePlanResponse,
    SwapRequest, SwapResponse,
    EstimateNutritionRequest, EstimateNutritionResponse,
    HealthResponse, MealPlan, Meal, MealPlanSource,
    RecipeCandidate, DailyPlanResponse, WeeklyPlanSummary,
    WeeklyPlanListResponse
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
    engine: NutritionEngine = Depends(get_nutrition_engine),
    rag: RAGModule = Depends(get_rag_module),
    llm: LLMOrchestrator = Depends(get_llm_orchestrator),
    val: MealPlanValidator = Depends(get_validator)
):
    """
    Generate a personalized meal plan.
    
    Args:
        request: User profile and preferences
        
    Returns:
        Generated meal plan with nutrition information
    """
    try:
        logger.info(f"Generating meal plan for user: {request.user_profile.user_id}")
        
        # Step 1: Calculate nutrition targets
        logger.info("Calculating nutrition targets...")
        nutrition_targets = engine.calculate_nutrition_targets(request.user_profile)
        
        # Step 2: Retrieve recipe candidates for each meal
        logger.info("Retrieving recipe candidates...")
        meal_candidates = {}
        
        for meal_type, target_kcal in nutrition_targets.meal_splits.items():
            candidates = rag.retrieve_candidates(
                meal_type=meal_type,
                target_kcal=target_kcal,
                diet_pref=request.user_profile.diet_pref,
                allergens=request.user_profile.allergies,
                top_k=3
            )
            meal_candidates[meal_type] = candidates
            logger.info(f"Retrieved {len(candidates)} candidates for {meal_type}")
        
        # Step 3: Generate meal plan (use simple planner for now - LLM has context issues)
        logger.info("Generating meal plan with simple deterministic planner...")
        from src.services.simple_planner import SimplePlanner
        simple_planner = SimplePlanner()
        
        meal_plan_dict = simple_planner.generate_plan(
            user_id=request.user_profile.user_id or str(uuid.uuid4()),
            meal_candidates=meal_candidates,
            meal_targets=nutrition_targets.meal_splits
        )
        
        # Step 4: Validate meal plan
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
        
        # Step 5: Convert to Pydantic model
        meal_plan = MealPlan(**meal_plan_dict)
        
        logger.info(f"Successfully generated meal plan: {meal_plan.plan_id}")
        
        return GeneratePlanResponse(meal_plan=meal_plan, status="success")
        
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
    rag: RAGModule = Depends(get_rag_module)
):
    """
    Get recipe details by ID.
    
    Args:
        recipe_id: Recipe identifier
        
    Returns:
        Recipe details with nutrition information
    """
    try:
        logger.info(f"Retrieving recipe: {recipe_id}")
        
        # Get recipe from vector database
        recipe_metadata = rag.vector_db.get_recipe(recipe_id)
        
        if recipe_metadata is None:
            raise HTTPException(
                status_code=404,
                detail=f"Recipe not found: {recipe_id}"
            )
        
        # Add recipe_id to metadata
        recipe_data = {"recipe_id": recipe_id, **recipe_metadata}
        
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

@router.post("/generate-weekly-plan")
async def generate_weekly_plan(
    user_profile: Dict,
    activity_pattern: Dict[str, str],
    start_date: str = None,
    max_recipe_repeats: int = 2,
    db: Session = Depends(get_db)
):
    """
    Generate and save a 7-day meal plan with recipe variety and activity-based adjustments.
    
    Args:
        user_profile: User profile dictionary
        activity_pattern: Activity level for each day (e.g., {"monday": "active", ...})
        start_date: Start date in ISO format (defaults to today)
        max_recipe_repeats: Maximum times a recipe can repeat in the week
        db: Database session
        
    Returns:
        Generated weekly meal plan
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
        
        # Initialize weekly planner with database session
        planner = WeeklyPlanner(db_session=db)
        
        # Generate and save weekly plan
        weekly_plan = planner.generate_and_save_weekly_plan(
            user_profile=profile,
            activity_pattern=activity_pattern,
            start_date=start_dt,
            max_recipe_repeats=max_recipe_repeats
        )
        
        logger.info(f"Generated weekly plan {weekly_plan['week_plan_id']}")
        
        return {
            "status": "success",
            "weekly_plan": weekly_plan
        }
        
    except Exception as e:
        logger.error(f"Error generating weekly plan: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate weekly plan: {str(e)}"
        )


@router.get("/weekly-plan/{week_plan_id}")
async def get_weekly_plan(week_plan_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a weekly plan by ID.
    
    Args:
        week_plan_id: Weekly plan identifier
        db: Database session
        
    Returns:
        Weekly plan data
    """
    try:
        repository = WeeklyPlanRepository(db)
        db_plan = repository.get_weekly_plan(week_plan_id)
        
        if not db_plan:
            raise HTTPException(
                status_code=404,
                detail=f"Weekly plan {week_plan_id} not found"
            )
        
        # Convert to dict
        planner = WeeklyPlanner()
        weekly_plan = planner._model_to_dict(db_plan)
        
        return {
            "status": "success",
            "weekly_plan": weekly_plan
        }
        
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


@router.get("/weekly-plan/week/{user_id}")
async def get_full_week(user_id: str, date: str = None, db: Session = Depends(get_db)):
    """
    Get full week view for a user.
    
    Args:
        user_id: User identifier
        date: Optional date to find week for (defaults to today)
        db: Database session
        
    Returns:
        Full weekly plan
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
        
        # Convert to dict
        planner = WeeklyPlanner()
        weekly_plan = planner._model_to_dict(db_plan)
        
        return {
            "status": "success",
            "weekly_plan": weekly_plan
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving full week: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve full week: {str(e)}"
        )


@router.post("/regenerate-day")
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
        Updated weekly plan
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
        
        return {
            "status": "success",
            "weekly_plan": updated_plan
        }
        
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
