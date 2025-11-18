"""
Deterministic Nutrition Engine for calculating BMR, TDEE, macros, and meal splits.
All calculations use scientifically validated formulas with no estimation or randomness.
"""
from typing import Dict
from src.models.schemas import UserProfile, NutritionTargets, Sex, ActivityLevel, Goal
from src.config import settings
from src.utils.logging_config import logger


class NutritionEngine:
    """
    Deterministic engine for nutrition calculations.
    Uses Mifflin-St Jeor equation for BMR and standard multipliers for TDEE.
    """
    
    # Activity level multipliers for TDEE calculation
    ACTIVITY_MULTIPLIERS = {
        ActivityLevel.SEDENTARY: 1.2,
        ActivityLevel.LIGHT: 1.375,
        ActivityLevel.MODERATE: 1.55,
        ActivityLevel.ACTIVE: 1.725,
        ActivityLevel.VERY_ACTIVE: 1.9
    }
    
    # Sex constants for Mifflin-St Jeor equation
    SEX_CONSTANTS = {
        Sex.MALE: 5,
        Sex.FEMALE: -161,
        Sex.OTHER: -78  # Average of male and female
    }
    
    # Default meal split ratios
    DEFAULT_MEAL_SPLITS = {
        "breakfast": 0.25,
        "lunch": 0.35,
        "dinner": 0.30,
        "snacks": 0.10
    }
    
    # Caloric value per gram of macronutrients
    PROTEIN_KCAL_PER_G = 4
    CARBS_KCAL_PER_G = 4
    FAT_KCAL_PER_G = 9
    
    def calculate_bmr(self, age: int, sex: Sex, weight_kg: float, height_cm: float) -> float:
        """
        Calculate Basal Metabolic Rate using Mifflin-St Jeor equation.
        
        Formula: BMR = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + sex_constant
        
        Args:
            age: Age in years
            sex: Sex (male, female, other)
            weight_kg: Weight in kilograms
            height_cm: Height in centimeters
            
        Returns:
            BMR in kcal/day
        """
        sex_constant = self.SEX_CONSTANTS[sex]
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + sex_constant
        
        logger.debug(f"BMR calculation: age={age}, sex={sex}, weight={weight_kg}kg, "
                    f"height={height_cm}cm -> BMR={bmr:.2f} kcal/day")
        
        return bmr
    
    def calculate_tdee(self, bmr: float, activity_level: ActivityLevel) -> float:
        """
        Calculate Total Daily Energy Expenditure.
        
        Formula: TDEE = BMR × activity_multiplier
        
        Args:
            bmr: Basal Metabolic Rate in kcal/day
            activity_level: Activity level enum
            
        Returns:
            TDEE in kcal/day
        """
        multiplier = self.ACTIVITY_MULTIPLIERS[activity_level]
        tdee = bmr * multiplier
        
        logger.debug(f"TDEE calculation: BMR={bmr:.2f}, activity={activity_level}, "
                    f"multiplier={multiplier} -> TDEE={tdee:.2f} kcal/day")
        
        return tdee
    
    def calculate_target_calories(
        self, 
        tdee: float, 
        goal: Goal, 
        goal_rate_kg_per_week: float
    ) -> float:
        """
        Calculate target daily calories based on goal and goal rate.
        
        Formula: target = TDEE + (goal_rate_kg_per_week × 7700 / 7)
        Note: 7700 kcal ≈ 1 kg of body weight
        Safety floor: minimum 1200 kcal/day
        
        Args:
            tdee: Total Daily Energy Expenditure
            goal: Goal (lose, maintain, gain)
            goal_rate_kg_per_week: Desired rate of weight change (negative for loss)
            
        Returns:
            Target daily calories in kcal/day
        """
        # Calculate caloric adjustment
        # For weight loss, goal_rate should be negative
        # For weight gain, goal_rate should be positive
        caloric_adjustment = (goal_rate_kg_per_week * 7700) / 7
        
        target_kcal = tdee + caloric_adjustment
        
        # Apply safety floor
        target_kcal = max(target_kcal, settings.MIN_DAILY_CALORIES)
        
        logger.debug(f"Target calories: TDEE={tdee:.2f}, goal={goal}, "
                    f"rate={goal_rate_kg_per_week}kg/week, adjustment={caloric_adjustment:.2f} "
                    f"-> target={target_kcal:.2f} kcal/day")
        
        return target_kcal
    
    def calculate_protein_target(self, weight_kg: float, target_kcal: float) -> float:
        """
        Calculate protein target in grams.
        
        Formula: max(1.6 g/kg body weight, 20% of target calories / 4)
        
        Args:
            weight_kg: Body weight in kilograms
            target_kcal: Target daily calories
            
        Returns:
            Protein target in grams
        """
        # Protein by body weight (1.6 g/kg)
        protein_by_weight = 1.6 * weight_kg
        
        # Protein by percentage of calories (20%)
        protein_by_percentage = (0.20 * target_kcal) / self.PROTEIN_KCAL_PER_G
        
        # Take the maximum
        protein_g = max(protein_by_weight, protein_by_percentage)
        
        logger.debug(f"Protein target: weight={weight_kg}kg, target_kcal={target_kcal:.2f}, "
                    f"by_weight={protein_by_weight:.2f}g, by_percentage={protein_by_percentage:.2f}g "
                    f"-> protein={protein_g:.2f}g")
        
        return protein_g
    
    def calculate_fat_target(self, target_kcal: float) -> float:
        """
        Calculate fat target in grams.
        
        Formula: 25% of target calories / 9
        
        Args:
            target_kcal: Target daily calories
            
        Returns:
            Fat target in grams
        """
        fat_g = (0.25 * target_kcal) / self.FAT_KCAL_PER_G
        
        logger.debug(f"Fat target: target_kcal={target_kcal:.2f} -> fat={fat_g:.2f}g")
        
        return fat_g
    
    def calculate_carbs_target(
        self, 
        target_kcal: float, 
        protein_g: float, 
        fat_g: float
    ) -> float:
        """
        Calculate carbohydrate target in grams.
        
        Formula: (target_kcal - protein*4 - fat*9) / 4
        
        Args:
            target_kcal: Target daily calories
            protein_g: Protein target in grams
            fat_g: Fat target in grams
            
        Returns:
            Carbohydrate target in grams
        """
        # Calculate remaining calories after protein and fat
        protein_kcal = protein_g * self.PROTEIN_KCAL_PER_G
        fat_kcal = fat_g * self.FAT_KCAL_PER_G
        remaining_kcal = target_kcal - protein_kcal - fat_kcal
        
        # Convert to grams
        carbs_g = remaining_kcal / self.CARBS_KCAL_PER_G
        
        logger.debug(f"Carbs target: target_kcal={target_kcal:.2f}, protein={protein_g:.2f}g, "
                    f"fat={fat_g:.2f}g, remaining_kcal={remaining_kcal:.2f} -> carbs={carbs_g:.2f}g")
        
        return carbs_g
    
    def calculate_meal_splits(
        self, 
        target_kcal: float,
        meal_split_ratios: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Distribute daily calorie target across meals.
        
        Args:
            target_kcal: Target daily calories
            meal_split_ratios: Optional custom meal split ratios
            
        Returns:
            Dictionary mapping meal type to calorie target
        """
        if meal_split_ratios is None:
            meal_split_ratios = self.DEFAULT_MEAL_SPLITS
        
        meal_splits = {
            meal_type: target_kcal * ratio
            for meal_type, ratio in meal_split_ratios.items()
        }
        
        logger.debug(f"Meal splits: {meal_splits}")
        
        return meal_splits
    
    def calculate_nutrition_targets(
        self, 
        user_profile: UserProfile,
        meal_split_ratios: Dict[str, float] = None
    ) -> NutritionTargets:
        """
        Calculate complete nutrition targets for a user profile.
        
        This is the main entry point that orchestrates all calculations.
        
        Args:
            user_profile: User profile with demographics and goals
            meal_split_ratios: Optional custom meal split ratios
            
        Returns:
            NutritionTargets with all calculated values
        """
        logger.info(f"Calculating nutrition targets for user: {user_profile.user_id}")
        
        # Step 1: Calculate BMR
        bmr = self.calculate_bmr(
            age=user_profile.age,
            sex=user_profile.sex,
            weight_kg=user_profile.weight_kg,
            height_cm=user_profile.height_cm
        )
        
        # Step 2: Calculate TDEE
        tdee = self.calculate_tdee(
            bmr=bmr,
            activity_level=user_profile.activity_level
        )
        
        # Step 3: Calculate target calories
        target_kcal = self.calculate_target_calories(
            tdee=tdee,
            goal=user_profile.goal,
            goal_rate_kg_per_week=user_profile.goal_rate_kg_per_week
        )
        
        # Step 4: Calculate macros
        protein_g = self.calculate_protein_target(
            weight_kg=user_profile.weight_kg,
            target_kcal=target_kcal
        )
        
        fat_g = self.calculate_fat_target(target_kcal=target_kcal)
        
        carbs_g = self.calculate_carbs_target(
            target_kcal=target_kcal,
            protein_g=protein_g,
            fat_g=fat_g
        )
        
        # Step 5: Calculate meal splits
        meal_splits = self.calculate_meal_splits(
            target_kcal=target_kcal,
            meal_split_ratios=meal_split_ratios
        )
        
        nutrition_targets = NutritionTargets(
            bmr=bmr,
            tdee=tdee,
            target_kcal=target_kcal,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            meal_splits=meal_splits
        )
        
        logger.info(f"Nutrition targets calculated: BMR={bmr:.2f}, TDEE={tdee:.2f}, "
                   f"target={target_kcal:.2f} kcal, P={protein_g:.2f}g, "
                   f"C={carbs_g:.2f}g, F={fat_g:.2f}g")
        
        return nutrition_targets
