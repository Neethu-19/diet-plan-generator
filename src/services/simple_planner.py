"""
Simple deterministic meal planner that doesn't rely on LLM.
Selects best matching recipes based on RAG scores.
"""
from typing import Dict, List
from datetime import datetime
import uuid

from src.models.schemas import RecipeCandidate, MealPlan, Meal, MealPlanSource
from src.utils.logging_config import logger


class SimplePlanner:
    """
    Deterministic meal planner that selects recipes based on RAG scores.
    """
    
    def generate_plan(
        self,
        user_id: str,
        meal_candidates: Dict[str, List[RecipeCandidate]],
        meal_targets: Dict[str, float] = None
    ) -> Dict:
        """
        Generate meal plan by selecting top candidate for each meal and scaling portions.
        
        Args:
            user_id: User ID
            meal_candidates: Dict mapping meal_type to list of RecipeCandidate objects
            meal_targets: Dict mapping meal_type to target calories (optional)
            
        Returns:
            Meal plan dictionary
        """
        logger.info("Generating meal plan using simple deterministic selection")
        
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        meals = []
        sources = []
        
        total_kcal = 0
        total_protein = 0
        total_carbs = 0
        total_fat = 0
        
        # Track used recipes to avoid repetition within the same day
        used_recipe_ids = set()
        
        # Select top candidate for each meal
        for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
            candidates = meal_candidates.get(meal_type, [])
            
            if not candidates:
                logger.warning(f"No candidates found for {meal_type}")
                continue
            
            # Select top candidate that hasn't been used yet
            # Add slight randomization to avoid always picking the same recipe
            import random
            
            selected = None
            available_candidates = [c for c in candidates if c.recipe_id not in used_recipe_ids]
            
            if available_candidates:
                # Pick from top candidates with slight preference for higher scores
                # This adds variety while still respecting quality
                if len(available_candidates) > 1:
                    # 70% chance to pick top candidate, 30% for others
                    if random.random() < 0.7:
                        selected = available_candidates[0]
                    else:
                        selected = random.choice(available_candidates[:min(3, len(available_candidates))])
                else:
                    selected = available_candidates[0]
                
                used_recipe_ids.add(selected.recipe_id)
            
            # If all candidates were used, use the top one anyway
            if selected is None:
                selected = candidates[0]
                logger.warning(f"All candidates for {meal_type} were already used, repeating recipe")
            
            # Calculate portion scaling if targets provided
            portion_multiplier = 1.0
            if meal_targets and meal_type in meal_targets:
                target_kcal = meal_targets[meal_type]
                if selected.kcal_total > 0:
                    portion_multiplier = target_kcal / selected.kcal_total
                    # Keep portions reasonable (0.5x to 2.0x)
                    portion_multiplier = max(0.5, min(2.0, portion_multiplier))
            
            # Scale nutrition values
            scaled_kcal = selected.kcal_total * portion_multiplier
            scaled_protein = selected.protein_g_total * portion_multiplier
            scaled_carbs = selected.carbs_g_total * portion_multiplier
            scaled_fat = selected.fat_g_total * portion_multiplier
            
            # Format portion size
            if abs(portion_multiplier - 1.0) < 0.1:
                portion_str = "1 serving"
            else:
                portion_str = f"{portion_multiplier:.1f}x serving"
            
            logger.info(f"{meal_type}: {selected.title} - {scaled_kcal:.0f}kcal (portion: {portion_str})")
            
            # Create meal with explainability
            meal = {
                "meal_type": meal_type,
                "recipe_id": selected.recipe_id,
                "recipe_title": selected.title,
                "portion_size": portion_str,
                "ingredients": selected.ingredients,
                "instructions": selected.instructions or "See recipe for details",
                "kcal": round(scaled_kcal, 1),
                "protein_g": round(scaled_protein, 1),
                "carbs_g": round(scaled_carbs, 1),
                "fat_g": round(scaled_fat, 1),
                "nutrition_status": "INDEXED_RECIPE"
            }
            
            # Add debug ranking if available (for explainability)
            if hasattr(selected, 'score_breakdown') and selected.score_breakdown:
                meal["debug_ranking"] = selected.score_breakdown
            
            meals.append(meal)
            
            # Add to totals
            total_kcal += scaled_kcal
            total_protein += scaled_protein
            total_carbs += scaled_carbs
            total_fat += scaled_fat
            
            # Add source
            source = {
                "meal_type": meal_type,
                "recipe_id": selected.recipe_id,
                "source_doc_id": selected.recipe_id,
                "source_snippet_excerpt": f"{selected.title}: {', '.join(selected.ingredients[:3])}"
            }
            sources.append(source)
        
        # Build meal plan
        meal_plan = {
            "plan_id": plan_id,
            "user_id": user_id,
            "date": datetime.now().isoformat(),
            "meals": meals,
            "total_nutrition": {
                "kcal": round(total_kcal, 1),
                "protein_g": round(total_protein, 1),
                "carbs_g": round(total_carbs, 1),
                "fat_g": round(total_fat, 1)
            },
            "nutrition_provenance": "DETERMINISTIC_ENGINE_AND_INDEXED_RECIPES",
            "plan_version": "1.0",
            "sources": sources
        }
        
        logger.info(f"Generated meal plan {plan_id} with {len(meals)} meals")
        logger.info(f"Total nutrition: {total_kcal:.0f}kcal, P:{total_protein:.0f}g, C:{total_carbs:.0f}g, F:{total_fat:.0f}g")
        
        return meal_plan
