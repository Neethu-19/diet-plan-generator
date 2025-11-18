"""
Recipe data preprocessing and validation module.
Ensures all recipes have complete nutrition data before indexing.
"""
from typing import List, Dict, Any, Optional
import re
from src.utils.logging_config import logger


class RecipePreprocessor:
    """Preprocesses and validates recipe data for indexing."""
    
    # Standard dietary tags vocabulary
    STANDARD_DIETARY_TAGS = {
        "vegan", "vegetarian", "ovo-lacto", "pescatarian", "omnivore",
        "gluten-free", "dairy-free", "keto", "paleo", "low-carb",
        "high-protein", "mediterranean", "whole30"
    }
    
    # Standard allergen tags vocabulary
    STANDARD_ALLERGEN_TAGS = {
        "nuts", "peanuts", "tree-nuts", "dairy", "eggs", "soy",
        "wheat", "gluten", "fish", "shellfish", "sesame"
    }
    
    # Required nutrition fields
    REQUIRED_NUTRITION_FIELDS = [
        "kcal_total", "protein_g_total", "carbs_g_total", "fat_g_total"
    ]
    
    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text string
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s,.\-()]', '', text)
        
        return text
    
    def normalize_tag(self, tag: str) -> str:
        """
        Normalize a tag to lowercase and remove extra spaces.
        
        Args:
            tag: Raw tag string
            
        Returns:
            Normalized tag
        """
        return tag.lower().strip().replace(" ", "-")
    
    def normalize_dietary_tags(self, tags: List[str]) -> List[str]:
        """
        Normalize dietary tags to standard vocabulary.
        
        Args:
            tags: List of raw dietary tags
            
        Returns:
            List of normalized dietary tags
        """
        normalized = []
        for tag in tags:
            normalized_tag = self.normalize_tag(tag)
            if normalized_tag in self.STANDARD_DIETARY_TAGS:
                normalized.append(normalized_tag)
            else:
                logger.warning(f"Non-standard dietary tag: {tag}")
        
        return list(set(normalized))  # Remove duplicates
    
    def normalize_allergen_tags(self, tags: List[str]) -> List[str]:
        """
        Normalize allergen tags to standard vocabulary.
        
        Args:
            tags: List of raw allergen tags
            
        Returns:
            List of normalized allergen tags
        """
        normalized = []
        for tag in tags:
            normalized_tag = self.normalize_tag(tag)
            if normalized_tag in self.STANDARD_ALLERGEN_TAGS:
                normalized.append(normalized_tag)
            else:
                logger.warning(f"Non-standard allergen tag: {tag}")
        
        return list(set(normalized))  # Remove duplicates
    
    def validate_nutrition_data(self, recipe: Dict[str, Any]) -> bool:
        """
        Validate that recipe has complete nutrition data.
        
        Args:
            recipe: Recipe dictionary
            
        Returns:
            True if nutrition data is complete and valid
        """
        for field in self.REQUIRED_NUTRITION_FIELDS:
            if field not in recipe:
                logger.error(f"Recipe {recipe.get('recipe_id', 'unknown')} missing field: {field}")
                return False
            
            value = recipe[field]
            if not isinstance(value, (int, float)):
                logger.error(f"Recipe {recipe.get('recipe_id', 'unknown')} has non-numeric {field}: {value}")
                return False
            
            if value < 0:
                logger.error(f"Recipe {recipe.get('recipe_id', 'unknown')} has negative {field}: {value}")
                return False
        
        return True
    
    def preprocess_recipe(self, recipe: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Preprocess and validate a single recipe.
        
        Args:
            recipe: Raw recipe dictionary
            
        Returns:
            Preprocessed recipe dictionary or None if validation fails
        """
        recipe_id = recipe.get("recipe_id", "unknown")
        
        # Validate required fields
        required_fields = ["recipe_id", "title", "ingredients", "instructions"]
        for field in required_fields:
            if field not in recipe:
                logger.error(f"Recipe {recipe_id} missing required field: {field}")
                return None
        
        # Validate nutrition data
        if not self.validate_nutrition_data(recipe):
            logger.error(f"Recipe {recipe_id} has invalid nutrition data")
            return None
        
        # Clean text fields
        preprocessed = {
            "recipe_id": recipe["recipe_id"],
            "title": self.clean_text(recipe["title"]),
            "ingredients": [self.clean_text(ing) for ing in recipe["ingredients"]],
            "instructions": self.clean_text(recipe["instructions"]),
            "kcal_total": float(recipe["kcal_total"]),
            "protein_g_total": float(recipe["protein_g_total"]),
            "carbs_g_total": float(recipe["carbs_g_total"]),
            "fat_g_total": float(recipe["fat_g_total"]),
        }
        
        # Normalize tags
        dietary_tags = recipe.get("dietary_tags", [])
        preprocessed["dietary_tags"] = self.normalize_dietary_tags(dietary_tags)
        
        allergen_tags = recipe.get("allergen_tags", [])
        preprocessed["allergen_tags"] = self.normalize_allergen_tags(allergen_tags)
        
        # Optional fields with defaults
        preprocessed["prep_time_min"] = recipe.get("prep_time_min", 30)
        preprocessed["cooking_skill"] = recipe.get("cooking_skill", 2)
        
        logger.debug(f"Preprocessed recipe: {recipe_id}")
        
        return preprocessed
    
    def preprocess_recipes(self, recipes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Preprocess a batch of recipes.
        
        Args:
            recipes: List of raw recipe dictionaries
            
        Returns:
            List of preprocessed recipes (invalid recipes are filtered out)
        """
        preprocessed = []
        failed_count = 0
        
        for recipe in recipes:
            result = self.preprocess_recipe(recipe)
            if result is not None:
                preprocessed.append(result)
            else:
                failed_count += 1
        
        logger.info(f"Preprocessed {len(preprocessed)} recipes, {failed_count} failed validation")
        
        return preprocessed
