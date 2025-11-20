"""
Progress tracking and adaptive calorie adjustment service.
"""
from typing import Optional, List, Dict, Tuple
from datetime import datetime, date, timedelta
from statistics import mean
import uuid

from sqlalchemy.orm import Session
from src.data.models import ProgressLogModel, CalorieAdjustmentModel, UserProfileModel
from src.utils.logging_config import logger


class ProgressService:
    """Service for tracking progress and making adaptive adjustments."""
    
    def __init__(self, db: Session):
        self.db = db
        
        # Safety limits
        self.MIN_CALORIES_FEMALE = 1200
        self.MIN_CALORIES_MALE = 1500
        self.MAX_CALORIES = 4000
        self.MAX_ADJUSTMENT = 300
        
        # Progress thresholds
        self.PROGRESS_TOLERANCE = 0.3  # 30% deviation is acceptable
        self.HIGH_ADHERENCE_THRESHOLD = 0.8
        self.LOW_ADHERENCE_THRESHOLD = 0.6
        
    def log_progress(
        self,
        user_id: str,
        log_date: date,
        actual_weight_kg: float,
        adherence_score: float,
        notes: Optional[str] = None,
        energy_level: Optional[int] = None,
        hunger_level: Optional[int] = None
    ) -> ProgressLogModel:
        """
        Log user's daily progress.
        
        Args:
            user_id: User identifier
            log_date: Date of the log
            actual_weight_kg: Actual weight measurement
            adherence_score: How well user followed the plan (0.0-1.0)
            notes: Optional notes
            energy_level: Optional energy level (1-5)
            hunger_level: Optional hunger level (1-5)
            
        Returns:
            Created ProgressLogModel
        """
        # Check for duplicate
        existing = self.db.query(ProgressLogModel).filter(
            ProgressLogModel.user_id == user_id,
            ProgressLogModel.log_date == log_date
        ).first()
        
        if existing:
            # Update existing log
            existing.actual_weight_kg = actual_weight_kg
            existing.adherence_score = adherence_score
            existing.notes = notes
            existing.energy_level = energy_level
            existing.hunger_level = hunger_level
            self.db.commit()
            self.db.refresh(existing)
            logger.info(f"Updated progress log for user {user_id} on {log_date}")
            return existing
        
        # Create new log
        log = ProgressLogModel(
            log_id=f"log_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            log_date=log_date,
            actual_weight_kg=actual_weight_kg,
            adherence_score=adherence_score,
            notes=notes,
            energy_level=energy_level,
            hunger_level=hunger_level
        )
        
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        
        logger.info(f"Created progress log for user {user_id} on {log_date}")
        return log

    
    def get_progress_history(
        self,
        user_id: str,
        days: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[ProgressLogModel]:
        """
        Get progress history for a user.
        
        Args:
            user_id: User identifier
            days: Number of days to retrieve (default 90)
            start_date: Optional start date filter
            end_date: Optional end date filter
            
        Returns:
            List of ProgressLogModel ordered by date
        """
        query = self.db.query(ProgressLogModel).filter(
            ProgressLogModel.user_id == user_id
        )
        
        if start_date and end_date:
            query = query.filter(
                ProgressLogModel.log_date >= start_date,
                ProgressLogModel.log_date <= end_date
            )
        elif not start_date and not end_date:
            # Default to last N days
            cutoff_date = date.today() - timedelta(days=days)
            query = query.filter(ProgressLogModel.log_date >= cutoff_date)
        
        logs = query.order_by(ProgressLogModel.log_date.asc()).all()
        return logs
    
    def analyze_progress(
        self,
        user_id: str,
        days: int = 30
    ) -> Optional[Dict]:
        """
        Analyze user's progress and determine if adjustments are needed.
        
        Args:
            user_id: User identifier
            days: Number of days to analyze (default 30)
            
        Returns:
            Dictionary with analysis results or None if insufficient data
        """
        # Get user profile
        user = self.db.query(UserProfileModel).filter(
            UserProfileModel.user_id == user_id
        ).first()
        
        if not user:
            logger.warning(f"User {user_id} not found")
            return None
        
        # Get progress logs
        logs = self.get_progress_history(user_id, days=days)
        
        if len(logs) < 2:
            logger.info(f"Insufficient data for user {user_id}: {len(logs)} logs")
            return None
        
        # Calculate metrics
        first_log = logs[0]
        last_log = logs[-1]
        
        days_elapsed = (last_log.log_date - first_log.log_date).days
        if days_elapsed == 0:
            days_elapsed = 1
        
        weeks_elapsed = days_elapsed / 7.0
        
        # Weight change
        weight_change = last_log.actual_weight_kg - first_log.actual_weight_kg
        actual_rate = weight_change / weeks_elapsed if weeks_elapsed > 0 else 0
        
        # Adherence
        adherence_scores = [log.adherence_score for log in logs]
        avg_adherence = mean(adherence_scores)
        
        # Determine adherence trend
        if len(logs) >= 7:
            recent_adherence = mean([log.adherence_score for log in logs[-7:]])
            early_adherence = mean([log.adherence_score for log in logs[:7]])
            if recent_adherence > early_adherence + 0.1:
                adherence_trend = "improving"
            elif recent_adherence < early_adherence - 0.1:
                adherence_trend = "declining"
            else:
                adherence_trend = "stable"
        else:
            adherence_trend = "stable"
        
        # Expected rate
        goal_rate = user.goal_rate_kg_per_week
        
        # Determine progress status
        progress_status, recommendation = self._evaluate_progress(
            actual_rate, goal_rate, avg_adherence
        )
        
        # Calculate calorie adjustment
        calorie_adjustment_needed, suggested_change, new_target = self._calculate_calorie_adjustment(
            user, actual_rate, goal_rate, avg_adherence, progress_status
        )
        
        analysis = {
            "user_id": user_id,
            "analysis_period_days": days_elapsed,
            "num_logs": len(logs),
            "starting_weight": first_log.actual_weight_kg,
            "current_weight": last_log.actual_weight_kg,
            "total_weight_change": weight_change,
            "actual_rate_kg_per_week": round(actual_rate, 2),
            "goal_rate_kg_per_week": goal_rate,
            "average_adherence": round(avg_adherence, 2),
            "adherence_trend": adherence_trend,
            "progress_status": progress_status,
            "recommendation": recommendation,
            "calorie_adjustment_needed": calorie_adjustment_needed,
            "suggested_calorie_change": suggested_change,
            "new_target_kcal": new_target
        }
        
        logger.info(f"Progress analysis for {user_id}: {progress_status}, adherence: {avg_adherence:.2f}")
        
        return analysis

    
    def _evaluate_progress(
        self,
        actual_rate: float,
        goal_rate: float,
        avg_adherence: float
    ) -> Tuple[str, str]:
        """
        Evaluate if progress is on track.
        
        Args:
            actual_rate: Actual weight change rate (kg/week)
            goal_rate: Goal weight change rate (kg/week)
            avg_adherence: Average adherence score
            
        Returns:
            Tuple of (status, recommendation)
        """
        # Handle different goal types
        if goal_rate == 0:  # Maintenance
            if abs(actual_rate) < 0.2:
                return "on_track", "Great job maintaining your weight!"
            elif actual_rate > 0.2:
                return "gaining", "You're gaining weight. Consider reducing calories slightly."
            else:
                return "losing", "You're losing weight. Consider increasing calories slightly."
        
        # Weight loss goal (negative rate)
        if goal_rate < 0:
            rate_diff = actual_rate - goal_rate
            tolerance = abs(goal_rate) * self.PROGRESS_TOLERANCE
            
            if actual_rate > goal_rate + tolerance:
                # Losing too slowly or gaining
                if avg_adherence < self.LOW_ADHERENCE_THRESHOLD:
                    return "too_slow", "Progress is slow. Focus on improving adherence to your meal plan."
                else:
                    return "too_slow", "Progress is slower than expected. Consider reducing calories."
            
            elif actual_rate < goal_rate - tolerance:
                # Losing too fast
                return "too_fast", "You're losing weight faster than recommended. Consider increasing calories for sustainable progress."
            
            else:
                return "on_track", "Excellent! You're right on track with your weight loss goal."
        
        # Weight gain goal (positive rate)
        else:
            rate_diff = actual_rate - goal_rate
            tolerance = goal_rate * self.PROGRESS_TOLERANCE
            
            if actual_rate < goal_rate - tolerance:
                # Gaining too slowly or losing
                if avg_adherence < self.LOW_ADHERENCE_THRESHOLD:
                    return "too_slow", "Progress is slow. Focus on improving adherence to your meal plan."
                else:
                    return "too_slow", "You're not gaining weight as expected. Consider increasing calories."
            
            elif actual_rate > goal_rate + tolerance:
                # Gaining too fast
                return "too_fast", "You're gaining weight faster than recommended. Consider reducing calories slightly."
            
            else:
                return "on_track", "Great! You're on track with your weight gain goal."
    
    def _calculate_calorie_adjustment(
        self,
        user: UserProfileModel,
        actual_rate: float,
        goal_rate: float,
        avg_adherence: float,
        progress_status: str
    ) -> Tuple[bool, Optional[int], Optional[float]]:
        """
        Calculate recommended calorie adjustment.
        
        Args:
            user: User profile
            actual_rate: Actual progress rate
            goal_rate: Goal progress rate
            avg_adherence: Average adherence
            progress_status: Progress status from evaluation
            
        Returns:
            Tuple of (adjustment_needed, suggested_change, new_target)
        """
        # Don't adjust if adherence is too low
        if avg_adherence < self.LOW_ADHERENCE_THRESHOLD:
            return False, None, None
        
        # Don't adjust if on track
        if progress_status == "on_track":
            return False, None, None
        
        # Calculate current TDEE estimate (simplified)
        from src.core.nutrition_engine import NutritionEngine
        engine = NutritionEngine()
        
        # Create temporary profile for calculation
        from src.models.schemas import UserProfile
        temp_profile = UserProfile(
            user_id=user.user_id,
            age=user.age,
            sex=user.sex,
            weight_kg=user.weight_kg,
            height_cm=user.height_cm,
            activity_level=user.activity_level,
            goal=user.goal,
            goal_rate_kg_per_week=user.goal_rate_kg_per_week,
            diet_pref=user.diet_pref,
            allergies=user.allergies,
            wake_time=datetime.strptime(user.wake_time, "%H:%M:%S").time(),
            lunch_time=datetime.strptime(user.lunch_time, "%H:%M:%S").time(),
            dinner_time=datetime.strptime(user.dinner_time, "%H:%M:%S").time(),
            cooking_skill=user.cooking_skill,
            budget_per_week=user.budget_per_week
        )
        
        targets = engine.calculate_nutrition_targets(temp_profile)
        current_target = targets.target_kcal
        
        # Calculate adjustment
        # 1 kg of fat ≈ 7700 kcal
        # Rate difference in kg/week → daily calorie adjustment
        rate_diff = actual_rate - goal_rate
        daily_adjustment = (rate_diff * 7700) / 7  # Convert to daily calories
        
        # Limit adjustment
        if abs(daily_adjustment) > self.MAX_ADJUSTMENT:
            daily_adjustment = self.MAX_ADJUSTMENT if daily_adjustment > 0 else -self.MAX_ADJUSTMENT
        
        # Round to nearest 50
        suggested_change = round(daily_adjustment / 50) * 50
        new_target = current_target + suggested_change
        
        # Apply safety limits
        min_calories = self.MIN_CALORIES_FEMALE if user.sex == "female" else self.MIN_CALORIES_MALE
        
        if new_target < min_calories:
            new_target = min_calories
            suggested_change = int(new_target - current_target)
        elif new_target > self.MAX_CALORIES:
            new_target = self.MAX_CALORIES
            suggested_change = int(new_target - current_target)
        
        # Only adjust if change is significant (>= 50 kcal)
        if abs(suggested_change) < 50:
            return False, None, None
        
        return True, int(suggested_change), round(new_target, 0)
    
    def apply_calorie_adjustment(
        self,
        user_id: str,
        analysis: Dict
    ) -> Optional[CalorieAdjustmentModel]:
        """
        Apply and record a calorie adjustment.
        
        Args:
            user_id: User identifier
            analysis: Progress analysis dictionary
            
        Returns:
            Created CalorieAdjustmentModel or None
        """
        if not analysis.get("calorie_adjustment_needed"):
            return None
        
        adjustment = CalorieAdjustmentModel(
            adjustment_id=f"adj_{uuid.uuid4().hex[:12]}",
            user_id=user_id,
            previous_target_kcal=analysis.get("new_target_kcal", 0) - analysis.get("suggested_calorie_change", 0),
            new_target_kcal=analysis.get("new_target_kcal"),
            adjustment_amount=analysis.get("suggested_calorie_change"),
            reason=analysis.get("progress_status"),
            actual_progress_rate=analysis.get("actual_rate_kg_per_week"),
            expected_progress_rate=analysis.get("goal_rate_kg_per_week"),
            average_adherence=analysis.get("average_adherence"),
            num_logs_analyzed=analysis.get("num_logs")
        )
        
        self.db.add(adjustment)
        self.db.commit()
        self.db.refresh(adjustment)
        
        logger.info(f"Applied calorie adjustment for {user_id}: {adjustment.adjustment_amount} kcal")
        
        return adjustment
