"""
Meal Plan Presentation Service
Generates enhanced, audience-specific meal plan presentations
"""
from typing import Dict, List, Optional
from src.models.schemas import (
    MealPlan, Meal, TargetAudience, MealPlanSection, 
    EnhancedMealPlanResponse
)
from src.utils.logging_config import logger


class MealPresentationService:
    """Service for generating audience-specific meal plan presentations."""
    
    def __init__(self):
        """Initialize presentation service."""
        self.audience_configs = {
            "student": {
                "focus": ["quick", "budget-friendly", "minimal cooking"],
                "tips_style": "practical and time-saving",
                "tone": "casual and encouraging"
            },
            "working_professional": {
                "focus": ["batch cooking", "meal prep", "office-friendly"],
                "tips_style": "efficiency-focused",
                "tone": "professional and organized"
            },
            "gym_goer": {
                "focus": ["high protein", "workout timing", "muscle recovery"],
                "tips_style": "performance-oriented",
                "tone": "motivational and fitness-focused"
            },
            "beginner_cook": {
                "focus": ["simple recipes", "basic techniques", "step-by-step"],
                "tips_style": "educational and supportive",
                "tone": "patient and instructive"
            },
            "general": {
                "focus": ["balanced nutrition", "variety", "health"],
                "tips_style": "informative",
                "tone": "friendly and helpful"
            }
        }
    
    def generate_enhanced_presentation(
        self,
        meal_plan: MealPlan,
        target_audience: TargetAudience,
        include_tips: bool = False
    ) -> EnhancedMealPlanResponse:
        """
        Generate enhanced meal plan presentation.
        
        Args:
            meal_plan: Base meal plan
            target_audience: Target audience type
            include_tips: Whether to include tips
            
        Returns:
            Enhanced presentation with sections and tips
        """

        logger.info(f"Generating enhanced presentation for {target_audience.value}")
        
        # Generate summary
        summary = self._generate_summary(meal_plan, target_audience)
        
        # Generate sections for each meal
        sections = []
        for meal in meal_plan.meals:
            section = self._generate_meal_section(
                meal, 
                target_audience, 
                include_tips
            )
            sections.append(section)
        
        # Add nutrition overview section
        nutrition_section = self._generate_nutrition_section(
            meal_plan.total_nutrition
        )
        sections.append(nutrition_section)
        
        # Generate audience-specific notes
        audience_notes = self._generate_audience_notes(
            meal_plan,
            target_audience
        )
        
        return EnhancedMealPlanResponse(
            summary=summary,
            sections=sections,
            nutrition_overview=meal_plan.total_nutrition,
            target_audience_notes=audience_notes
        )
    
    def _generate_summary(
        self,
        meal_plan: MealPlan,
        target_audience: TargetAudience
    ) -> str:
        """Generate audience-specific summary."""
        total_kcal = meal_plan.total_nutrition.get("kcal", 0)
        protein = meal_plan.total_nutrition.get("protein_g", 0)
        
        summaries = {
            "student": f"Quick and budget-friendly meal plan with {total_kcal:.0f} calories. Perfect for busy student life with minimal cooking time!",
            "working_professional": f"Efficient meal plan with {total_kcal:.0f} calories. Designed for meal prep and office-friendly lunches.",
            "gym_goer": f"Performance-focused meal plan with {total_kcal:.0f} calories and {protein:.0f}g protein. Optimized for muscle recovery and workout fuel.",
            "beginner_cook": f"Simple and easy meal plan with {total_kcal:.0f} calories. All recipes are beginner-friendly with clear instructions.",
            "general": f"Balanced meal plan with {total_kcal:.0f} calories. Nutritious and varied meals for your health goals."
        }
        
        return summaries.get(target_audience.value, summaries["general"])
    
    def _generate_meal_section(
        self,
        meal: Meal,
        target_audience: TargetAudience,
        include_tips: bool
    ) -> MealPlanSection:
        """Generate section for a single meal."""
        meal_type = meal.meal_type.title()
        recipe_title = meal.recipe_title
        portion = meal.portion_size
        kcal = meal.kcal
        protein = meal.protein_g
        
        # Build markdown body
        body_parts = [
            f"**{recipe_title}**",
            f"",
            f"📊 Nutrition: {kcal:.0f} kcal | {protein:.0f}g protein",
            f"🍽️ Portion: {portion}",
            f"",
            f"**Ingredients:**"
        ]
        
        ingredients = meal.ingredients
        for ing in ingredients[:5]:
            body_parts.append(f"- {ing}")
        
        if len(ingredients) > 5:
            body_parts.append(f"- ...and {len(ingredients) - 5} more")
        
        body_markdown = "\n".join(body_parts)
        
        # Generate tips if requested
        tips = None
        if include_tips:
            tips = self._generate_meal_tips(meal, target_audience)
        
        return MealPlanSection(
            title=f"{meal_type}",
            body_markdown=body_markdown,
            tips=tips
        )

    
    def _generate_meal_tips(
        self,
        meal: Meal,
        target_audience: TargetAudience
    ) -> List[str]:
        """Generate audience-specific tips for a meal."""
        meal_type = meal.meal_type
        prep_time = getattr(meal, 'prep_time_min', 30)
        
        tips_map = {
            "student": [
                f"💡 Prep time: ~{prep_time} minutes - perfect between classes!",
                "💰 Budget tip: Buy ingredients in bulk to save money",
                "⏰ Can be prepared the night before"
            ],
            "working_professional": [
                f"📦 Meal prep: Make 3-4 servings on Sunday",
                "🏢 Office-friendly: Stores well and reheats easily",
                f"⏱️ Quick prep: Only {prep_time} minutes needed"
            ],
            "gym_goer": [
                f"💪 Protein boost: {meal.protein_g:.0f}g for muscle recovery",
                "⏰ Best timing: 1-2 hours before/after workout" if meal_type == "lunch" else "🌙 Great for overnight recovery" if meal_type == "dinner" else "🔋 Fuel up for your workout",
                "🥤 Pair with water for optimal hydration"
            ],
            "beginner_cook": [
                "👨‍🍳 Skill level: Beginner-friendly",
                f"⏲️ Takes about {prep_time} minutes - don't rush!",
                "📝 Follow instructions step-by-step for best results"
            ],
            "general": [
                f"⏰ Preparation time: {prep_time} minutes",
                "🥗 Balanced and nutritious",
                "❄️ Can be stored for later"
            ]
        }
        
        return tips_map.get(target_audience.value, tips_map["general"])
    
    def _generate_nutrition_section(
        self,
        total_nutrition: Dict[str, float]
    ) -> MealPlanSection:
        """Generate nutrition overview section."""
        kcal = total_nutrition.get("kcal", 0)
        protein = total_nutrition.get("protein_g", 0)
        carbs = total_nutrition.get("carbs_g", 0)
        fat = total_nutrition.get("fat_g", 0)
        
        body = f"""
**Daily Nutrition Summary**

| Nutrient | Amount |
|----------|--------|
| Calories | {kcal:.0f} kcal |
| Protein | {protein:.0f}g |
| Carbs | {carbs:.0f}g |
| Fat | {fat:.0f}g |

✅ Nutritionally balanced and aligned with your goals
"""
        
        return MealPlanSection(
            title="📊 Nutrition Overview",
            body_markdown=body.strip()
        )
    
    def _generate_audience_notes(
        self,
        meal_plan: MealPlan,
        target_audience: TargetAudience
    ) -> str:
        """Generate audience-specific notes."""
        notes_map = {
            "student": "💡 **Student Tips**: All meals are budget-friendly and quick to prepare. Consider batch cooking on weekends to save time during busy weekdays!",
            "working_professional": "💼 **Professional Tips**: This plan is optimized for meal prep. Prepare lunches on Sunday evening and store in containers. Breakfasts can be prepped 2-3 days ahead.",
            "gym_goer": "💪 **Fitness Tips**: Protein is distributed throughout the day for optimal muscle recovery. Time your meals around workouts for best results. Stay hydrated!",
            "beginner_cook": "👨‍🍳 **Cooking Tips**: All recipes are beginner-friendly. Don't be intimidated! Start with breakfast and work your way up. Practice makes perfect!",
            "general": "🌟 **General Tips**: Follow the meal plan consistently for best results. Feel free to swap meals within the same category if needed."
        }
        
        return notes_map.get(target_audience.value, notes_map["general"])
