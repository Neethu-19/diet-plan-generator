"""
Prompt templates for LLM meal plan generation.
Includes strict numeric provenance rules and JSON schema enforcement.
"""
from typing import Dict, List, Any
from src.models.schemas import UserProfile, NutritionTargets, RecipeCandidate


SYSTEM_MESSAGE = """You are a meal planning assistant. Your role is to select recipes from provided candidates and format them into a daily meal plan.

CRITICAL RULES:
1. You MUST NOT compute, estimate, or invent ANY numeric nutrition values (kcal, protein, carbs, fat).
2. ALL numeric nutrition values MUST come EXACTLY from the provided recipe candidates or nutrition targets.
3. You MUST select ONE recipe from the provided candidates for each meal.
4. If a recipe lacks complete nutrition data, mark it as "MISSING_NUTRITION" and do NOT fill in numbers.
5. You MUST output ONLY valid JSON matching the exact schema provided.
6. Do NOT add explanations, comments, or text outside the JSON structure.

Your output will be validated to ensure all numbers are traceable to the input data."""


def create_user_message(
    user_profile: UserProfile,
    nutrition_targets: NutritionTargets,
    meal_candidates: Dict[str, List[RecipeCandidate]]
) -> str:
    """
    Create user message with profile, targets, and recipe candidates.
    
    Args:
        user_profile: User profile information
        nutrition_targets: Calculated nutrition targets
        meal_candidates: Dict mapping meal_type to list of RecipeCandidate objects
        
    Returns:
        Formatted user message string
    """
    message_parts = []
    
    # Simplified targets
    message_parts.append(f"TARGETS: {nutrition_targets.target_kcal:.0f}kcal, P:{nutrition_targets.protein_g:.0f}g, C:{nutrition_targets.carbs_g:.0f}g, F:{nutrition_targets.fat_g:.0f}g")
    message_parts.append("")
    
    # Recipe candidates for each meal (only top 2 to save tokens)
    for meal_type, candidates in meal_candidates.items():
        target_kcal = nutrition_targets.meal_splits.get(meal_type, 0)
        message_parts.append(f"{meal_type.upper()} ({target_kcal:.0f}kcal):")
        
        for i, candidate in enumerate(candidates[:2], 1):  # Only use top 2 candidates
            ing_str = ', '.join(candidate.ingredients[:3])  # Only first 3 ingredients
            message_parts.append(f"{i}. {candidate.recipe_id}: {candidate.title} - {candidate.kcal_total}kcal, P:{candidate.protein_g_total}g, C:{candidate.carbs_g_total}g, F:{candidate.fat_g_total}g")
        
        message_parts.append("")
    
    message_parts.append("Select 1 recipe per meal. Use ONLY provided nutrition values.")
    
    return "\n".join(message_parts)


ASSISTANT_SCHEMA_MESSAGE = """Output JSON:
{
  "meals": [
    {"meal_type": "breakfast", "recipe_id": "...", "recipe_title": "...", "kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
  ],
  "total_nutrition": {"kcal": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
}
Use ONLY provided values. Include breakfast, lunch, dinner, snacks."""


def create_cursor_messages(
    user_profile: UserProfile,
    nutrition_targets: NutritionTargets,
    meal_candidates: Dict[str, List[RecipeCandidate]]
) -> List[Dict[str, str]]:
    """
    Create cursor-style message array for LLM.
    
    Args:
        user_profile: User profile information
        nutrition_targets: Calculated nutrition targets
        meal_candidates: Recipe candidates for each meal
        
    Returns:
        List of message dictionaries
    """
    messages = [
        {
            "role": "system",
            "content": SYSTEM_MESSAGE
        },
        {
            "role": "user",
            "content": create_user_message(user_profile, nutrition_targets, meal_candidates)
        },
        {
            "role": "assistant",
            "content": ASSISTANT_SCHEMA_MESSAGE
        }
    ]
    
    return messages


def create_swap_prompt(
    original_meal: Dict[str, Any],
    meal_type: str,
    candidates: List[RecipeCandidate],
    constraints: Dict[str, bool]
) -> List[Dict[str, str]]:
    """
    Create prompt for meal swap request.
    
    Args:
        original_meal: Original meal data
        meal_type: Type of meal to swap
        candidates: Alternative recipe candidates
        constraints: Swap constraints (different_protein, different_cuisine, faster_prep)
        
    Returns:
        List of message dictionaries
    """
    system_msg = SYSTEM_MESSAGE
    
    user_msg_parts = [
        f"SWAP REQUEST FOR {meal_type.upper()}:",
        f"\nOriginal Recipe: {original_meal.get('recipe_title', 'Unknown')}",
        f"Original Calories: {original_meal.get('kcal', 0)} kcal",
        ""
    ]
    
    if constraints:
        user_msg_parts.append("CONSTRAINTS:")
        if constraints.get("different_protein"):
            user_msg_parts.append("- Must use different protein source")
        if constraints.get("different_cuisine"):
            user_msg_parts.append("- Must be different cuisine")
        if constraints.get("faster_prep"):
            user_msg_parts.append("- Must have faster preparation time")
        user_msg_parts.append("")
    
    user_msg_parts.append("ALTERNATIVE RECIPE CANDIDATES:")
    for i, candidate in enumerate(candidates, 1):
        user_msg_parts.append(f"\nCandidate {i}:")
        user_msg_parts.append(f"  recipe_id: {candidate.recipe_id}")
        user_msg_parts.append(f"  title: {candidate.title}")
        user_msg_parts.append(f"  kcal_total: {candidate.kcal_total}")
        user_msg_parts.append(f"  protein_g_total: {candidate.protein_g_total}")
        user_msg_parts.append(f"  carbs_g_total: {candidate.carbs_g_total}")
        user_msg_parts.append(f"  fat_g_total: {candidate.fat_g_total}")
        user_msg_parts.append(f"  prep_time_min: {candidate.prep_time_min}")
    
    user_msg_parts.append("\nSelect the best alternative recipe and output as JSON with the same meal structure.")
    
    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": "\n".join(user_msg_parts)},
        {"role": "assistant", "content": "Output the replacement meal as JSON:"}
    ]
    
    return messages
