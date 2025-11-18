"""
Post-processing validator for meal plan outputs.
Enforces numeric provenance, schema validation, and safety constraints.
"""
from typing import Dict, List, Any, Set, Tuple, Optional
from src.models.schemas import MealPlan, NutritionTargets, RecipeCandidate
from src.config import settings
from src.utils.logging_config import logger


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


class MealPlanValidator:
    """
    Validates LLM-generated meal plans for safety and correctness.
    Ensures all numeric nutrition values are traceable to input sources.
    """
    
    def __init__(self):
        """Initialize validator."""
        self.tolerance = 0.1  # 10% tolerance for nutrition sums
    
    def _build_provenance_map(
        self,
        nutrition_targets: NutritionTargets,
        meal_candidates: Dict[str, List[RecipeCandidate]]
    ) -> Dict[str, Set[float]]:
        """
        Build a map of all valid numeric nutrition values from input context.
        
        Args:
            nutrition_targets: Calculated nutrition targets
            meal_candidates: Recipe candidates for each meal
            
        Returns:
            Dict mapping field names to sets of valid values
        """
        provenance = {
            "kcal": set(),
            "protein_g": set(),
            "carbs_g": set(),
            "fat_g": set()
        }
        
        # Add nutrition targets
        provenance["kcal"].add(round(nutrition_targets.target_kcal, 2))
        provenance["protein_g"].add(round(nutrition_targets.protein_g, 2))
        provenance["carbs_g"].add(round(nutrition_targets.carbs_g, 2))
        provenance["fat_g"].add(round(nutrition_targets.fat_g, 2))
        
        # Add meal split values
        for meal_kcal in nutrition_targets.meal_splits.values():
            provenance["kcal"].add(round(meal_kcal, 2))
        
        # Add all recipe candidate values
        for candidates in meal_candidates.values():
            for candidate in candidates:
                provenance["kcal"].add(round(candidate.kcal_total, 2))
                provenance["protein_g"].add(round(candidate.protein_g_total, 2))
                provenance["carbs_g"].add(round(candidate.carbs_g_total, 2))
                provenance["fat_g"].add(round(candidate.fat_g_total, 2))
        
        logger.debug(f"Built provenance map with {sum(len(v) for v in provenance.values())} values")
        
        return provenance
    
    def _check_value_provenance(
        self,
        value: float,
        field: str,
        provenance_map: Dict[str, Set[float]],
        tolerance: float = 0.01
    ) -> bool:
        """
        Check if a numeric value exists in the provenance map.
        
        Args:
            value: Value to check
            field: Field name (kcal, protein_g, etc.)
            provenance_map: Map of valid values
            tolerance: Tolerance for floating point comparison
            
        Returns:
            True if value is valid
        """
        if field not in provenance_map:
            return False
        
        rounded_value = round(value, 2)
        valid_values = provenance_map[field]
        
        # Check exact match
        if rounded_value in valid_values:
            return True
        
        # Check with tolerance for floating point errors
        for valid_value in valid_values:
            if abs(rounded_value - valid_value) <= tolerance:
                return True
        
        return False
    
    def validate_numeric_provenance(
        self,
        meal_plan: Dict[str, Any],
        nutrition_targets: NutritionTargets,
        meal_candidates: Dict[str, List[RecipeCandidate]]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all numeric nutrition values come from input context.
        
        Args:
            meal_plan: Generated meal plan dictionary
            nutrition_targets: Nutrition targets used for generation
            meal_candidates: Recipe candidates used for generation
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Build provenance map
        provenance_map = self._build_provenance_map(nutrition_targets, meal_candidates)
        
        # Check each meal's nutrition values
        meals = meal_plan.get("meals", [])
        for i, meal in enumerate(meals):
            meal_type = meal.get("meal_type", f"meal_{i}")
            
            # Skip if marked as MISSING_NUTRITION
            if meal.get("nutrition_status") == "MISSING_NUTRITION":
                continue
            
            # Check kcal
            kcal = meal.get("kcal")
            if kcal is not None:
                if not self._check_value_provenance(kcal, "kcal", provenance_map):
                    errors.append(f"Meal {meal_type}: kcal value {kcal} not found in input context")
            
            # Check protein
            protein = meal.get("protein_g")
            if protein is not None:
                if not self._check_value_provenance(protein, "protein_g", provenance_map):
                    errors.append(f"Meal {meal_type}: protein_g value {protein} not found in input context")
            
            # Check carbs
            carbs = meal.get("carbs_g")
            if carbs is not None:
                if not self._check_value_provenance(carbs, "carbs_g", provenance_map):
                    errors.append(f"Meal {meal_type}: carbs_g value {carbs} not found in input context")
            
            # Check fat
            fat = meal.get("fat_g")
            if fat is not None:
                if not self._check_value_provenance(fat, "fat_g", provenance_map):
                    errors.append(f"Meal {meal_type}: fat_g value {fat} not found in input context")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.error(f"Numeric provenance validation failed with {len(errors)} errors")
            for error in errors:
                logger.error(f"  - {error}")
        
        return is_valid, errors
    
    def validate_schema(self, meal_plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate meal plan JSON structure.
        
        Args:
            meal_plan: Generated meal plan dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required top-level fields
        required_fields = ["plan_id", "user_id", "date", "meals", "total_nutrition", 
                          "nutrition_provenance", "plan_version", "sources"]
        
        for field in required_fields:
            if field not in meal_plan:
                errors.append(f"Missing required field: {field}")
        
        # Check meals array
        if "meals" in meal_plan:
            meals = meal_plan["meals"]
            if not isinstance(meals, list):
                errors.append("'meals' must be an array")
            else:
                # Check each meal structure
                required_meal_fields = ["meal_type", "recipe_id", "recipe_title", 
                                       "portion_size", "ingredients", "instructions",
                                       "kcal", "protein_g", "carbs_g", "fat_g", 
                                       "nutrition_status"]
                
                for i, meal in enumerate(meals):
                    for field in required_meal_fields:
                        if field not in meal:
                            errors.append(f"Meal {i}: missing field '{field}'")
        
        # Check total_nutrition structure
        if "total_nutrition" in meal_plan:
            total_nutrition = meal_plan["total_nutrition"]
            if not isinstance(total_nutrition, dict):
                errors.append("'total_nutrition' must be an object")
            else:
                required_nutrition_fields = ["kcal", "protein_g", "carbs_g", "fat_g"]
                for field in required_nutrition_fields:
                    if field not in total_nutrition:
                        errors.append(f"total_nutrition: missing field '{field}'")
        
        # Check sources array
        if "sources" in meal_plan:
            sources = meal_plan["sources"]
            if not isinstance(sources, list):
                errors.append("'sources' must be an array")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.error(f"Schema validation failed with {len(errors)} errors")
        
        return is_valid, errors
    
    def validate_safety_constraints(
        self,
        meal_plan: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate safety constraints (minimum calories, nutrition sums, etc.).
        
        Args:
            meal_plan: Generated meal plan dictionary
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check minimum daily calories
        total_nutrition = meal_plan.get("total_nutrition", {})
        total_kcal = total_nutrition.get("kcal", 0)
        
        if total_kcal < settings.MIN_DAILY_CALORIES:
            errors.append(f"Total calories {total_kcal} below minimum {settings.MIN_DAILY_CALORIES}")
        
        # Check that meal nutrition sums match total nutrition
        meals = meal_plan.get("meals", [])
        
        meal_sum_kcal = sum(meal.get("kcal", 0) for meal in meals 
                           if meal.get("nutrition_status") != "MISSING_NUTRITION")
        meal_sum_protein = sum(meal.get("protein_g", 0) for meal in meals 
                              if meal.get("nutrition_status") != "MISSING_NUTRITION")
        meal_sum_carbs = sum(meal.get("carbs_g", 0) for meal in meals 
                            if meal.get("nutrition_status") != "MISSING_NUTRITION")
        meal_sum_fat = sum(meal.get("fat_g", 0) for meal in meals 
                          if meal.get("nutrition_status") != "MISSING_NUTRITION")
        
        # Check with tolerance
        if abs(meal_sum_kcal - total_kcal) > total_kcal * self.tolerance:
            errors.append(f"Meal kcal sum {meal_sum_kcal:.1f} doesn't match total {total_kcal:.1f}")
        
        if abs(meal_sum_protein - total_nutrition.get("protein_g", 0)) > total_nutrition.get("protein_g", 0) * self.tolerance:
            errors.append(f"Meal protein sum {meal_sum_protein:.1f}g doesn't match total {total_nutrition.get('protein_g', 0):.1f}g")
        
        if abs(meal_sum_carbs - total_nutrition.get("carbs_g", 0)) > total_nutrition.get("carbs_g", 0) * self.tolerance:
            errors.append(f"Meal carbs sum {meal_sum_carbs:.1f}g doesn't match total {total_nutrition.get('carbs_g', 0):.1f}g")
        
        if abs(meal_sum_fat - total_nutrition.get("fat_g", 0)) > total_nutrition.get("fat_g", 0) * self.tolerance:
            errors.append(f"Meal fat sum {meal_sum_fat:.1f}g doesn't match total {total_nutrition.get('fat_g', 0):.1f}g")
        
        is_valid = len(errors) == 0
        
        if not is_valid:
            logger.error(f"Safety constraint validation failed with {len(errors)} errors")
        
        return is_valid, errors
    
    def validate_meal_plan(
        self,
        meal_plan: Dict[str, Any],
        nutrition_targets: NutritionTargets,
        meal_candidates: Dict[str, List[RecipeCandidate]]
    ) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Perform complete validation of meal plan.
        
        Args:
            meal_plan: Generated meal plan dictionary
            nutrition_targets: Nutrition targets used for generation
            meal_candidates: Recipe candidates used for generation
            
        Returns:
            Tuple of (is_valid, dict_of_errors_by_category)
        """
        logger.info("Validating meal plan")
        
        all_errors = {
            "schema": [],
            "provenance": [],
            "safety": []
        }
        
        # Schema validation
        schema_valid, schema_errors = self.validate_schema(meal_plan)
        all_errors["schema"] = schema_errors
        
        # Numeric provenance validation
        provenance_valid, provenance_errors = self.validate_numeric_provenance(
            meal_plan, nutrition_targets, meal_candidates
        )
        all_errors["provenance"] = provenance_errors
        
        # Safety constraints validation
        safety_valid, safety_errors = self.validate_safety_constraints(meal_plan)
        all_errors["safety"] = safety_errors
        
        is_valid = schema_valid and provenance_valid and safety_valid
        
        if is_valid:
            logger.info("Meal plan validation passed")
        else:
            total_errors = sum(len(errors) for errors in all_errors.values())
            logger.error(f"Meal plan validation failed with {total_errors} total errors")
        
        return is_valid, all_errors
