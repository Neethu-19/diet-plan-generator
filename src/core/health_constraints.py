"""
Health Condition Constraints Module.
Implements rule-based dietary constraints for common health conditions.

MEDICAL DISCLAIMER:
This system is NOT a medical device and should NOT replace professional medical advice.
Constraints are based on general dietary guidelines and may not be appropriate for all individuals.
Always consult with a healthcare provider before making dietary changes.
"""
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from src.utils.logging_config import logger


@dataclass
class HealthConstraintRule:
    """Rule for a specific health condition."""
    condition: str
    max_sugar_per_meal_g: Optional[float] = None
    max_sodium_per_day_mg: Optional[float] = None
    max_saturated_fat_per_day_g: Optional[float] = None
    prefer_tags: List[str] = None
    avoid_tags: List[str] = None
    prefer_low_gi: bool = False
    description: str = ""


# Clinical guidelines-based constraints
CONDITION_RULES = {
    "diabetes": HealthConstraintRule(
        condition="diabetes",
        max_sugar_per_meal_g=15.0,
        prefer_low_gi=True,
        prefer_tags=["low_gi", "whole_grain", "high_fiber"],
        avoid_tags=["high_sugar", "refined_carbs", "sweetened"],
        description="Diabetes management: Focus on low-GI foods, limit added sugars, prefer whole grains"
    ),
    
    "hypertension": HealthConstraintRule(
        condition="hypertension",
        max_sodium_per_day_mg=2000.0,
        max_saturated_fat_per_day_g=13.0,
        prefer_tags=["low_sodium", "heart_healthy", "potassium_rich"],
        avoid_tags=["high_sodium", "processed", "cured_meats"],
        description="Hypertension management: Limit sodium, avoid processed foods, focus on heart-healthy options"
    ),
    
    "high_cholesterol": HealthConstraintRule(
        condition="high_cholesterol",
        max_saturated_fat_per_day_g=13.0,
        prefer_tags=["heart_healthy", "omega3", "high_fiber"],
        avoid_tags=["high_saturated_fat", "trans_fat", "fried"],
        description="Cholesterol management: Limit saturated fats, avoid trans fats, increase fiber and omega-3"
    ),
    
    "pcos": HealthConstraintRule(
        condition="pcos",
        max_sugar_per_meal_g=20.0,
        prefer_low_gi=True,
        prefer_tags=["low_gi", "high_fiber", "anti_inflammatory"],
        avoid_tags=["high_sugar", "refined_carbs", "processed"],
        description="PCOS management: Low-GI diet, anti-inflammatory foods, balanced macros"
    ),
    
    "ckd_stage_3": HealthConstraintRule(
        condition="ckd_stage_3",
        max_sodium_per_day_mg=2000.0,
        prefer_tags=["low_sodium", "low_potassium", "low_phosphorus"],
        avoid_tags=["high_sodium", "high_potassium", "high_phosphorus", "processed"],
        description="CKD Stage 3: Limit sodium, potassium, and phosphorus. Requires medical supervision."
    )
}


class HealthConstraintsEngine:
    """
    Engine for applying health condition constraints to meal planning.
    """
    
    def __init__(self):
        """Initialize health constraints engine."""
        self.rules = CONDITION_RULES
        logger.info("Health Constraints Engine initialized")
    
    def get_applicable_rules(self, health_conditions: List[str]) -> List[HealthConstraintRule]:
        """
        Get applicable rules for given health conditions.
        
        Args:
            health_conditions: List of health condition identifiers
            
        Returns:
            List of applicable constraint rules
        """
        applicable = []
        for condition in health_conditions:
            condition_lower = condition.lower().strip()
            if condition_lower in self.rules:
                applicable.append(self.rules[condition_lower])
                logger.info(f"Applied constraints for: {condition}")
            else:
                logger.warning(f"Unknown health condition: {condition}")
        
        return applicable
    
    def filter_recipes(
        self,
        recipes: List[Dict],
        health_conditions: List[str]
    ) -> List[Dict]:
        """
        Filter recipes based on health condition constraints.
        
        Args:
            recipes: List of recipe dictionaries
            health_conditions: List of health conditions
            
        Returns:
            Filtered list of recipes
        """
        if not health_conditions:
            return recipes
        
        applicable_rules = self.get_applicable_rules(health_conditions)
        if not applicable_rules:
            return recipes
        
        filtered = []
        for recipe in recipes:
            if self._recipe_meets_constraints(recipe, applicable_rules):
                filtered.append(recipe)
            else:
                logger.debug(f"Filtered out recipe {recipe.get('recipe_id')} due to health constraints")
        
        logger.info(f"Filtered {len(recipes)} recipes to {len(filtered)} based on health conditions")
        return filtered
    
    def _recipe_meets_constraints(
        self,
        recipe: Dict,
        rules: List[HealthConstraintRule]
    ) -> bool:
        """
        Check if recipe meets all applicable health constraints.
        
        Args:
            recipe: Recipe dictionary
            rules: List of applicable constraint rules
            
        Returns:
            True if recipe meets all constraints
        """
        recipe_tags = set(recipe.get("dietary_tags", []))
        
        for rule in rules:
            # Check avoid tags
            if rule.avoid_tags:
                avoid_set = set(rule.avoid_tags)
                if recipe_tags & avoid_set:
                    logger.debug(f"Recipe has avoided tags: {recipe_tags & avoid_set}")
                    return False
            
            # Check sugar limit (per meal)
            if rule.max_sugar_per_meal_g is not None:
                recipe_sugar = recipe.get("sugar_g", 0)
                if recipe_sugar > rule.max_sugar_per_meal_g:
                    logger.debug(f"Recipe exceeds sugar limit: {recipe_sugar}g > {rule.max_sugar_per_meal_g}g")
                    return False
            
            # Check low-GI preference (strict for diabetes/PCOS)
            if rule.prefer_low_gi:
                gi_level = recipe.get("gi_level", "medium")
                if gi_level == "high":
                    logger.debug(f"Recipe has high GI, not suitable for {rule.condition}")
                    return False
        
        return True
    
    def score_recipe_for_conditions(
        self,
        recipe: Dict,
        health_conditions: List[str]
    ) -> float:
        """
        Calculate a preference score for recipe based on health conditions.
        Higher score = better match for health conditions.
        
        Args:
            recipe: Recipe dictionary
            health_conditions: List of health conditions
            
        Returns:
            Preference score (0.0 to 1.5, where 1.0 is neutral)
        """
        if not health_conditions:
            return 1.0
        
        applicable_rules = self.get_applicable_rules(health_conditions)
        if not applicable_rules:
            return 1.0
        
        recipe_tags = set(recipe.get("dietary_tags", []))
        score = 1.0
        
        for rule in rules:
            # Boost for preferred tags
            if rule.prefer_tags:
                prefer_set = set(rule.prefer_tags)
                matching_preferred = recipe_tags & prefer_set
                if matching_preferred:
                    # Boost by 0.1 for each matching preferred tag (max 0.5)
                    boost = min(0.5, len(matching_preferred) * 0.1)
                    score += boost
                    logger.debug(f"Recipe boosted by {boost} for preferred tags: {matching_preferred}")
        
        return min(1.5, score)  # Cap at 1.5x boost
    
    def validate_daily_plan(
        self,
        meal_plan: Dict,
        health_conditions: List[str]
    ) -> Dict[str, any]:
        """
        Validate entire daily meal plan against health constraints.
        
        Args:
            meal_plan: Complete meal plan dictionary
            health_conditions: List of health conditions
            
        Returns:
            Validation result with warnings and recommendations
        """
        if not health_conditions:
            return {
                "is_safe": True,
                "warnings": [],
                "recommendations": []
            }
        
        applicable_rules = self.get_applicable_rules(health_conditions)
        warnings = []
        recommendations = []
        
        # Calculate daily totals
        total_sodium = sum(meal.get("sodium_mg", 0) for meal in meal_plan.get("meals", []))
        total_saturated_fat = sum(meal.get("saturated_fat_g", 0) for meal in meal_plan.get("meals", []))
        
        for rule in applicable_rules:
            # Check daily sodium limit
            if rule.max_sodium_per_day_mg is not None:
                if total_sodium > rule.max_sodium_per_day_mg:
                    warnings.append(
                        f"{rule.condition.title()}: Daily sodium ({total_sodium:.0f}mg) exceeds "
                        f"recommended limit ({rule.max_sodium_per_day_mg:.0f}mg)"
                    )
                elif total_sodium > rule.max_sodium_per_day_mg * 0.8:
                    recommendations.append(
                        f"Consider lower-sodium options to stay well below {rule.max_sodium_per_day_mg:.0f}mg limit"
                    )
            
            # Check daily saturated fat limit
            if rule.max_saturated_fat_per_day_g is not None:
                if total_saturated_fat > rule.max_saturated_fat_per_day_g:
                    warnings.append(
                        f"{rule.condition.title()}: Daily saturated fat ({total_saturated_fat:.1f}g) exceeds "
                        f"recommended limit ({rule.max_saturated_fat_per_day_g:.1f}g)"
                    )
        
        is_safe = len(warnings) == 0
        
        return {
            "is_safe": is_safe,
            "warnings": warnings,
            "recommendations": recommendations,
            "conditions_checked": [rule.condition for rule in applicable_rules]
        }
    
    def get_condition_info(self, condition: str) -> Optional[Dict]:
        """
        Get information about a specific health condition's constraints.
        
        Args:
            condition: Health condition identifier
            
        Returns:
            Dictionary with condition information or None
        """
        condition_lower = condition.lower().strip()
        if condition_lower not in self.rules:
            return None
        
        rule = self.rules[condition_lower]
        return {
            "condition": rule.condition,
            "description": rule.description,
            "constraints": {
                "max_sugar_per_meal_g": rule.max_sugar_per_meal_g,
                "max_sodium_per_day_mg": rule.max_sodium_per_day_mg,
                "max_saturated_fat_per_day_g": rule.max_saturated_fat_per_day_g,
                "prefer_low_gi": rule.prefer_low_gi
            },
            "prefer_tags": rule.prefer_tags or [],
            "avoid_tags": rule.avoid_tags or [],
            "disclaimer": "This is general guidance. Consult your healthcare provider for personalized advice."
        }
    
    def get_all_supported_conditions(self) -> List[str]:
        """
        Get list of all supported health conditions.
        
        Returns:
            List of condition identifiers
        """
        return list(self.rules.keys())


# Convenience function
def apply_health_constraints(
    recipes: List[Dict],
    health_conditions: List[str]
) -> List[Dict]:
    """
    Convenience function to filter recipes by health constraints.
    
    Args:
        recipes: List of recipe dictionaries
        health_conditions: List of health conditions
        
    Returns:
        Filtered list of recipes
    """
    engine = HealthConstraintsEngine()
    return engine.filter_recipes(recipes, health_conditions)
