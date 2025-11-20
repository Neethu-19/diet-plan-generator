"""
Preference Service for managing user preferences and feedback.
"""
from typing import Dict, Set, Optional
from sqlalchemy.orm import Session
import uuid

from src.data.repositories import PreferenceRepository
from src.utils.logging_config import logger


class PreferenceService:
    """Service for managing user preferences and feedback."""
    
    def __init__(self, db_session: Session):
        """
        Initialize preference service.
        
        Args:
            db_session: Database session
        """
        self.db = db_session
        self.repository = PreferenceRepository(db_session)
    
    def submit_feedback(
        self,
        user_id: str,
        recipe_id: str,
        liked: bool
    ) -> Dict:
        """
        Submit or update recipe feedback.
        
        Args:
            user_id: User identifier
            recipe_id: Recipe identifier
            liked: Whether user liked the recipe
            
        Returns:
            Feedback record dictionary
        """
        logger.info(f"Submitting feedback for user {user_id} on recipe {recipe_id}: liked={liked}")
        
        # Check if feedback already exists
        existing = self.repository.get_feedback(user_id, recipe_id)
        
        if existing:
            # Update existing feedback
            updated = self.repository.update_feedback(
                feedback_id=existing.feedback_id,
                liked=liked
            )
            return self._feedback_to_dict(updated)
        else:
            # Create new feedback
            feedback_id = f"feedback_{uuid.uuid4().hex[:12]}"
            created = self.repository.create_feedback(
                feedback_id=feedback_id,
                user_id=user_id,
                recipe_id=recipe_id,
                liked=liked
            )
            return self._feedback_to_dict(created)
    
    def get_user_preferences(
        self,
        user_id: str
    ) -> Dict:
        """
        Get user's complete preference data.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with liked_recipes, disliked_recipes, regional_profile
        """
        logger.debug(f"Retrieving preferences for user {user_id}")
        
        # Get feedback
        feedback_list = self.repository.get_all_feedback(user_id)
        
        liked_recipes = set()
        disliked_recipes = set()
        
        for feedback in feedback_list:
            if feedback.liked:
                liked_recipes.add(feedback.recipe_id)
            else:
                disliked_recipes.add(feedback.recipe_id)
        
        # Get regional profile
        prefs = self.repository.get_user_preferences(user_id)
        regional_profile = prefs.regional_profile if prefs else "global"
        
        logger.debug(f"User {user_id} has {len(liked_recipes)} liked, {len(disliked_recipes)} disliked recipes")
        
        return {
            "liked_recipes": liked_recipes,
            "disliked_recipes": disliked_recipes,
            "regional_profile": regional_profile
        }
    
    def update_regional_profile(
        self,
        user_id: str,
        regional_profile: str
    ) -> Dict:
        """
        Update user's regional cuisine preference.
        
        Args:
            user_id: User identifier
            regional_profile: Regional cuisine preference
            
        Returns:
            Updated preferences dictionary
        """
        logger.info(f"Updating regional profile for user {user_id} to {regional_profile}")
        
        prefs = self.repository.get_user_preferences(user_id)
        
        if prefs:
            updated = self.repository.update_regional_profile(
                user_id=user_id,
                regional_profile=regional_profile
            )
        else:
            updated = self.repository.create_user_preferences(
                user_id=user_id,
                regional_profile=regional_profile
            )
        
        return {
            "user_id": updated.user_id,
            "regional_profile": updated.regional_profile,
            "updated_at": updated.updated_at.isoformat()
        }
    
    def get_feedback_stats(
        self,
        user_id: str
    ) -> Dict:
        """
        Calculate feedback statistics and insights.
        
        Args:
            user_id: User identifier
            
        Returns:
            Statistics dictionary
        """
        logger.debug(f"Calculating feedback stats for user {user_id}")
        
        feedback_list = self.repository.get_all_feedback(user_id)
        
        total_liked = sum(1 for f in feedback_list if f.liked)
        total_disliked = sum(1 for f in feedback_list if not f.liked)
        total_feedback = len(feedback_list)
        
        # Calculate tag distribution (would need recipe metadata)
        # For now, return basic stats
        
        # Calculate preference diversity (simple version)
        if total_feedback > 0:
            diversity = min(total_liked, total_disliked) / total_feedback
        else:
            diversity = 0.0
        
        return {
            "user_id": user_id,
            "total_liked": total_liked,
            "total_disliked": total_disliked,
            "total_feedback": total_feedback,
            "feedback_rate": 0.0,  # Would need total recipes tried
            "most_liked_tags": [],
            "regional_distribution": {},
            "preference_diversity_score": round(diversity, 2)
        }
    
    def delete_user_feedback(
        self,
        user_id: str
    ) -> bool:
        """
        Delete all feedback for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            True if successful
        """
        logger.info(f"Deleting all feedback for user {user_id}")
        
        return self.repository.delete_all_feedback(user_id)
    
    def _feedback_to_dict(self, feedback) -> Dict:
        """
        Convert feedback model to dictionary.
        
        Args:
            feedback: RecipeFeedbackModel
            
        Returns:
            Dictionary representation
        """
        return {
            "feedback_id": feedback.feedback_id,
            "user_id": feedback.user_id,
            "recipe_id": feedback.recipe_id,
            "liked": feedback.liked,
            "feedback_date": feedback.feedback_date.isoformat(),
            "updated_at": feedback.updated_at.isoformat()
        }
