"""
End-to-end integration test script.
Tests the complete flow from user input to meal plan generation.
"""
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.nutrition_engine import NutritionEngine
from src.core.rag_module import RAGModule
from src.services.llm_service import LLMOrchestrator
from src.services.prompt_templates import create_cursor_messages
from src.core.validator import MealPlanValidator
from src.models.schemas import UserProfile
from src.utils.logging_config import logger


def load_test_profile(profile_index=0):
    """Load a test profile from test_profiles.json."""
    profiles_file = Path(__file__).parent.parent / "data" / "test_profiles.json"
    
    with open(profiles_file, 'r') as f:
        profiles = json.load(f)
    
    if profile_index >= len(profiles):
        profile_index = 0
    
    test_case = profiles[profile_index]
    logger.info(f"Using test profile: {test_case['name']}")
    
    return UserProfile(**test_case['profile'])


def test_nutrition_engine(user_profile):
    """Test nutrition engine calculations."""
    logger.info("\n=== Testing Nutrition Engine ===")
    
    engine = NutritionEngine()
    nutrition_targets = engine.calculate_nutrition_targets(user_profile)
    
    logger.info(f"BMR: {nutrition_targets.bmr:.2f} kcal/day")
    logger.info(f"TDEE: {nutrition_targets.tdee:.2f} kcal/day")
    logger.info(f"Target Calories: {nutrition_targets.target_kcal:.2f} kcal/day")
    logger.info(f"Protein: {nutrition_targets.protein_g:.2f}g")
    logger.info(f"Carbs: {nutrition_targets.carbs_g:.2f}g")
    logger.info(f"Fat: {nutrition_targets.fat_g:.2f}g")
    logger.info(f"Meal Splits: {nutrition_targets.meal_splits}")
    
    return nutrition_targets


def test_rag_module(user_profile, nutrition_targets):
    """Test RAG retrieval module."""
    logger.info("\n=== Testing RAG Module ===")
    
    rag = RAGModule()
    meal_candidates = {}
    
    for meal_type, target_kcal in nutrition_targets.meal_splits.items():
        logger.info(f"\nRetrieving candidates for {meal_type} ({target_kcal:.0f} kcal)...")
        
        candidates = rag.retrieve_candidates(
            meal_type=meal_type,
            target_kcal=target_kcal,
            diet_pref=user_profile.diet_pref,
            allergens=user_profile.allergies,
            top_k=3
        )
        
        meal_candidates[meal_type] = candidates
        
        for i, candidate in enumerate(candidates, 1):
            logger.info(f"  {i}. {candidate.title} - {candidate.kcal_total} kcal (score: {candidate.score:.3f})")
    
    return meal_candidates


def test_llm_generation(user_profile, nutrition_targets, meal_candidates):
    """Test LLM meal plan generation."""
    logger.info("\n=== Testing LLM Generation ===")
    
    llm = LLMOrchestrator()
    
    # Create cursor messages
    cursor_messages = create_cursor_messages(
        user_profile=user_profile,
        nutrition_targets=nutrition_targets,
        meal_candidates=meal_candidates
    )
    
    logger.info("Calling LLM (this may take 30-60 seconds)...")
    
    # Generate meal plan
    generated_text = llm.call_llm(cursor_messages)
    
    logger.info(f"Generated {len(generated_text)} characters")
    
    # Parse JSON
    meal_plan_dict = llm.parse_json_output(generated_text)
    
    if meal_plan_dict is None:
        logger.error("Failed to parse JSON from LLM output")
        logger.debug(f"Raw output: {generated_text[:500]}")
        return None
    
    logger.info("Successfully parsed meal plan JSON")
    
    return meal_plan_dict


def test_validator(meal_plan_dict, nutrition_targets, meal_candidates):
    """Test meal plan validator."""
    logger.info("\n=== Testing Validator ===")
    
    validator = MealPlanValidator()
    
    is_valid, errors = validator.validate_meal_plan(
        meal_plan=meal_plan_dict,
        nutrition_targets=nutrition_targets,
        meal_candidates=meal_candidates
    )
    
    if is_valid:
        logger.info("✓ Meal plan validation PASSED")
    else:
        logger.error("✗ Meal plan validation FAILED")
        for category, error_list in errors.items():
            if error_list:
                logger.error(f"\n{category.upper()} errors:")
                for error in error_list:
                    logger.error(f"  - {error}")
    
    return is_valid


def main():
    """Run end-to-end integration test."""
    logger.info("=" * 60)
    logger.info("STARTING END-TO-END INTEGRATION TEST")
    logger.info("=" * 60)
    
    try:
        # Load test profile
        profile_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
        user_profile = load_test_profile(profile_index)
        
        # Test nutrition engine
        nutrition_targets = test_nutrition_engine(user_profile)
        
        # Test RAG module
        meal_candidates = test_rag_module(user_profile, nutrition_targets)
        
        # Test LLM generation
        meal_plan_dict = test_llm_generation(user_profile, nutrition_targets, meal_candidates)
        
        if meal_plan_dict is None:
            logger.error("Integration test FAILED: LLM generation failed")
            sys.exit(1)
        
        # Test validator
        is_valid = test_validator(meal_plan_dict, nutrition_targets, meal_candidates)
        
        if is_valid:
            logger.info("\n" + "=" * 60)
            logger.info("INTEGRATION TEST PASSED ✓")
            logger.info("=" * 60)
            
            # Print meal plan summary
            logger.info("\nGenerated Meal Plan:")
            logger.info(f"Plan ID: {meal_plan_dict.get('plan_id')}")
            logger.info(f"Total Nutrition: {meal_plan_dict.get('total_nutrition')}")
            logger.info(f"Number of Meals: {len(meal_plan_dict.get('meals', []))}")
            
            for meal in meal_plan_dict.get('meals', []):
                logger.info(f"\n{meal.get('meal_type').upper()}: {meal.get('recipe_title')}")
                logger.info(f"  Calories: {meal.get('kcal')} kcal")
                logger.info(f"  Protein: {meal.get('protein_g')}g")
            
            sys.exit(0)
        else:
            logger.error("\n" + "=" * 60)
            logger.error("INTEGRATION TEST FAILED ✗")
            logger.error("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\nIntegration test FAILED with exception: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
