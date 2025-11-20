"""
RAG (Retrieval-Augmented Generation) Module for recipe retrieval.
Uses hybrid scoring: semantic similarity + calorie proximity + tag matching.
"""
from typing import List, Dict, Set, Optional
import numpy as np
from src.models.schemas import RecipeCandidate, DietaryPreference
from src.services.embedding_service import EmbeddingService
from src.services.vector_db import VectorDatabase, create_vector_database
from src.config import settings
from src.utils.logging_config import logger


class RAGModule:
    """
    Retrieval-Augmented Generation module for recipe retrieval.
    Implements hybrid scoring algorithm combining semantic, caloric, and tag-based matching.
    """
    
    def __init__(
        self,
        embedding_service: EmbeddingService = None,
        vector_db: VectorDatabase = None
    ):
        """
        Initialize RAG module.
        
        Args:
            embedding_service: Embedding service instance (creates new if None)
            vector_db: Vector database instance (creates new if None)
        """
        logger.info("Initializing RAG Module")
        
        # Initialize embedding service
        if embedding_service is None:
            self.embedding_service = EmbeddingService()
        else:
            self.embedding_service = embedding_service
        
        # Initialize vector database
        if vector_db is None:
            embedding_dim = self.embedding_service.get_embedding_dimension()
            self.vector_db = create_vector_database(dimension=embedding_dim)
            # Try to load existing index
            try:
                self.vector_db.load()
            except Exception as e:
                logger.warning(f"Could not load existing index: {e}")
        else:
            self.vector_db = vector_db
        
        logger.info("RAG Module initialized")
    
    def _filter_allergens(
        self,
        candidates: List[tuple],
        allergens: List[str]
    ) -> List[tuple]:
        """
        Filter out recipes containing specified allergens.
        
        Args:
            candidates: List of (recipe_id, score, metadata) tuples
            allergens: List of allergen tags to exclude
            
        Returns:
            Filtered list of candidates
        """
        if not allergens:
            return candidates
        
        allergen_set = set(allergen.lower().strip() for allergen in allergens)
        filtered = []
        
        for recipe_id, score, metadata in candidates:
            recipe_allergens = set(metadata.get("allergen_tags", []))
            if not (recipe_allergens & allergen_set):
                filtered.append((recipe_id, score, metadata))
            else:
                logger.debug(f"Filtered out recipe {recipe_id} due to allergens: {recipe_allergens & allergen_set}")
        
        return filtered
    
    def _calculate_semantic_similarity(
        self,
        query_embedding: np.ndarray,
        recipe_embedding: np.ndarray
    ) -> float:
        """
        Calculate semantic similarity using cosine similarity.
        
        Args:
            query_embedding: Query embedding vector
            recipe_embedding: Recipe embedding vector
            
        Returns:
            Similarity score in [0, 1]
        """
        # Normalize vectors
        query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
        recipe_norm = recipe_embedding / (np.linalg.norm(recipe_embedding) + 1e-8)
        
        # Cosine similarity
        cosine_sim = np.dot(query_norm, recipe_norm)
        
        # Normalize to [0, 1] range (cosine is in [-1, 1])
        normalized_sim = (cosine_sim + 1) / 2
        
        return float(normalized_sim)
    
    def _calculate_kcal_proximity_score(
        self,
        recipe_kcal: float,
        target_kcal: float
    ) -> float:
        """
        Calculate calorie proximity score.
        
        Formula: max(0, 1 - abs(recipe_kcal - target_kcal) / target_kcal)
        
        Args:
            recipe_kcal: Recipe calorie content
            target_kcal: Target calorie content
            
        Returns:
            Proximity score in [0, 1]
        """
        if target_kcal <= 0:
            return 0.0
        
        kcal_diff = abs(recipe_kcal - target_kcal)
        proximity = max(0.0, 1.0 - (kcal_diff / target_kcal))
        
        return proximity
    
    def _calculate_skill_match_score(
        self,
        recipe_skill: int,
        user_skill: int
    ) -> float:
        """
        Calculate cooking skill compatibility score.
        
        Args:
            recipe_skill: Recipe required skill level (0-5)
            user_skill: User cooking skill level (0-5)
            
        Returns:
            Skill match score in [0, 1]
        """
        if recipe_skill <= user_skill:
            return 1.0  # Perfect match or easier
        else:
            # Penalize recipes that are too difficult
            skill_gap = recipe_skill - user_skill
            return max(0.0, 1.0 - (skill_gap * settings.SKILL_PENALTY_PER_LEVEL))
    
    def _calculate_prep_time_score(
        self,
        prep_time_min: int,
        max_prep_time: Optional[int] = None
    ) -> float:
        """
        Calculate preparation time suitability score.
        
        Args:
            prep_time_min: Recipe preparation time in minutes
            max_prep_time: Maximum acceptable prep time (optional)
            
        Returns:
            Prep time score in [0, 1]
        """
        if max_prep_time is None:
            # No constraint, but prefer shorter prep times
            if prep_time_min <= 30:
                return 1.0
            elif prep_time_min <= 60:
                return 0.8
            else:
                return 0.6
        else:
            # Hard constraint
            if prep_time_min <= max_prep_time:
                return 1.0
            else:
                # Penalize recipes over the limit
                excess = prep_time_min - max_prep_time
                return max(0.0, 1.0 - (excess / max_prep_time))
    
    def _calculate_tag_score(
        self,
        recipe_tags: Set[str],
        required_tags: Set[str]
    ) -> float:
        """
        Calculate tag matching score.
        
        Formula: (matching_tags / required_tags) clipped to [0, 1]
        
        Args:
            recipe_tags: Set of recipe dietary tags
            required_tags: Set of required dietary tags
            
        Returns:
            Tag score in [0, 1]
        """
        if not required_tags:
            return 1.0
        
        matching_tags = recipe_tags & required_tags
        tag_score = len(matching_tags) / len(required_tags)
        
        return min(1.0, tag_score)
    
    def _calculate_hybrid_score(
        self,
        semantic_similarity: float,
        kcal_proximity: float,
        tag_score: float
    ) -> float:
        """
        Calculate final hybrid score.
        
        Formula: 0.6*semantic + 0.3*kcal_proximity + 0.1*tag_score
        
        Args:
            semantic_similarity: Semantic similarity score [0, 1]
            kcal_proximity: Calorie proximity score [0, 1]
            tag_score: Tag matching score [0, 1]
            
        Returns:
            Final hybrid score
        """
        final_score = (
            settings.SEMANTIC_WEIGHT * semantic_similarity +
            settings.KCAL_PROXIMITY_WEIGHT * kcal_proximity +
            settings.TAG_WEIGHT * tag_score
        )
        
        return final_score
    
    def _rescore_candidates(
        self,
        candidates: List[tuple],
        target_kcal: float,
        required_tags: Set[str]
    ) -> List[Dict]:
        """
        Rescore candidates using hybrid scoring algorithm with detailed breakdown.
        
        Args:
            candidates: List of (recipe_id, semantic_score, metadata) tuples
            target_kcal: Target calorie content
            required_tags: Required dietary tags
            
        Returns:
            List of dicts with recipe_id, scores breakdown, metadata, and explanation
        """
        rescored = []
        
        for recipe_id, semantic_score, metadata in candidates:
            # Get recipe calories
            recipe_kcal = metadata.get("kcal_total", 0)
            
            # Calculate kcal proximity
            kcal_proximity = self._calculate_kcal_proximity_score(recipe_kcal, target_kcal)
            
            # Get recipe tags
            recipe_tags = set(metadata.get("dietary_tags", []))
            
            # Calculate tag score
            tag_score = self._calculate_tag_score(recipe_tags, required_tags)
            
            # Calculate hybrid score
            hybrid_score = self._calculate_hybrid_score(
                semantic_similarity=semantic_score,
                kcal_proximity=kcal_proximity,
                tag_score=tag_score
            )
            
            # Generate explanation
            explanation = self._generate_explanation(
                semantic_score, kcal_proximity, tag_score, 
                recipe_kcal, target_kcal, recipe_tags, required_tags
            )
            
            logger.debug(
                f"Recipe {recipe_id}: semantic={semantic_score:.3f}, "
                f"kcal_prox={kcal_proximity:.3f}, tag={tag_score:.3f}, "
                f"hybrid={hybrid_score:.3f}"
            )
            
            rescored.append({
                "recipe_id": recipe_id,
                "hybrid_score": hybrid_score,
                "metadata": metadata,
                "scores": {
                    "semantic_similarity": round(semantic_score, 3),
                    "calorie_proximity": round(kcal_proximity, 3),
                    "dietary_match": round(tag_score, 3),
                    "final_score": round(hybrid_score, 3)
                },
                "explanation": explanation
            })
        
        # Sort by hybrid score (descending)
        rescored.sort(key=lambda x: x["hybrid_score"], reverse=True)
        
        return rescored
    
    def _generate_explanation(
        self,
        semantic_score: float,
        calorie_score: float,
        dietary_match_score: float,
        skill_match_score: float,
        prep_time: int,
        recipe_kcal: float,
        target_kcal: float,
        recipe_tags: Set[str],
        required_tags: Set[str],
        has_recency_penalty: bool
    ) -> str:
        """
        Generate human-readable explanation for recipe selection.
        
        Args:
            semantic_score: Semantic similarity score
            calorie_score: Calorie proximity score
            dietary_match_score: Dietary tag matching score
            skill_match_score: Cooking skill compatibility score
            prep_time: Recipe preparation time in minutes
            recipe_kcal: Recipe calories
            target_kcal: Target calories
            recipe_tags: Recipe dietary tags
            required_tags: Required dietary tags
            has_recency_penalty: Whether recipe was recently used
            
        Returns:
            Human-readable explanation string
        """
        reasons = []
        
        # Semantic relevance (check first for flow)
        if semantic_score >= 0.8:
            reasons.append("excellent match for your meal preferences")
        elif semantic_score >= 0.6:
            reasons.append("good match for your meal preferences")
        
        # Calorie match
        if calorie_score >= 0.9:
            reasons.append(f"perfect calorie match ({recipe_kcal:.0f} vs {target_kcal:.0f} target)")
        elif calorie_score >= 0.7:
            reasons.append(f"close calorie match ({recipe_kcal:.0f} kcal)")
        
        # Dietary match
        if dietary_match_score == 1.0 and required_tags:
            reasons.append("fully compatible with your dietary preferences")
        elif dietary_match_score >= 0.5 and required_tags:
            matching = recipe_tags & required_tags
            if matching:
                reasons.append(f"matches dietary preferences ({', '.join(matching)})")
        
        # Skill match
        if skill_match_score == 1.0:
            reasons.append("matches your cooking skill level")
        elif skill_match_score < 0.7:
            reasons.append("slightly challenging for your skill level")
        
        # Prep time
        if prep_time <= 30:
            reasons.append(f"quick to prepare ({prep_time} min)")
        
        # Recency
        if has_recency_penalty:
            reasons.append("recently used (lower priority)")
        
        if not reasons:
            reasons.append("best available option")
        
        return "Selected because it's an " + ", ".join(reasons) + "." if reasons else "Selected based on overall compatibility."
    
    
    def _build_query_text(
        self,
        meal_type: str,
        dietary_prefs: List[str]
    ) -> str:
        """
        Build query text for embedding generation.
        
        Args:
            meal_type: Type of meal (breakfast, lunch, dinner, snacks)
            dietary_prefs: List of dietary preferences
            
        Returns:
            Query text string
        """
        query_parts = [meal_type]
        
        if dietary_prefs:
            query_parts.extend(dietary_prefs)
        
        query_text = " ".join(query_parts)
        return query_text
    
    def _get_required_tags(self, diet_pref: DietaryPreference) -> Set[str]:
        """
        Get required dietary tags based on dietary preference.
        
        Args:
            diet_pref: Dietary preference enum
            
        Returns:
            Set of required tags
        """
        tag_mapping = {
            DietaryPreference.VEGAN: {"vegan"},
            DietaryPreference.VEGETARIAN: {"vegetarian", "vegan"},
            DietaryPreference.OVO_LACTO: {"vegetarian", "vegan", "ovo-lacto"},
            DietaryPreference.PESCO: {"pescatarian", "vegetarian", "vegan"},
            DietaryPreference.OMNIVORE: set()  # No restrictions
        }
        
        return tag_mapping.get(diet_pref, set())
    
    def retrieve_candidates(
        self,
        meal_type: str,
        target_kcal: float,
        diet_pref: DietaryPreference,
        allergens: List[str],
        top_k: int = None
    ) -> List[RecipeCandidate]:
        """
        Retrieve top-K recipe candidates for a meal.
        
        Args:
            meal_type: Type of meal (breakfast, lunch, dinner, snacks)
            target_kcal: Target calorie content for the meal
            diet_pref: Dietary preference
            allergens: List of allergens to exclude
            top_k: Number of candidates to return (default from settings)
            
        Returns:
            List of RecipeCandidate objects ranked by hybrid score
        """
        if top_k is None:
            top_k = settings.TOP_K_CANDIDATES
        
        logger.info(f"Retrieving candidates for {meal_type}, target={target_kcal} kcal")
        
        # Build query text
        dietary_prefs = list(self._get_required_tags(diet_pref))
        query_text = self._build_query_text(meal_type, dietary_prefs)
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        # Get required tags
        required_tags = self._get_required_tags(diet_pref)
        
        # Build filters for vector DB
        filters = {}
        if allergens:
            filters["exclude_allergens"] = allergens
        if required_tags:
            filters["required_dietary_tags"] = list(required_tags)
        
        # Retrieve initial candidates from vector DB (get more for rescoring)
        initial_k = top_k * 5
        candidates = self.vector_db.search(
            query_embedding=query_embedding,
            top_k=initial_k,
            filters=filters
        )
        
        logger.debug(f"Retrieved {len(candidates)} initial candidates")
        
        # Filter allergens (in case vector DB doesn't support filtering)
        candidates = self._filter_allergens(candidates, allergens)
        
        # Rescore using hybrid algorithm (returns detailed breakdown)
        rescored_candidates = self._rescore_candidates(
            candidates=candidates,
            target_kcal=target_kcal,
            required_tags=required_tags
        )
        
        # Take top-K
        top_candidates = rescored_candidates[:top_k]
        
        # Convert to RecipeCandidate objects with score details
        recipe_candidates = []
        for candidate_data in top_candidates:
            recipe_id = candidate_data["recipe_id"]
            metadata = candidate_data["metadata"]
            scores = candidate_data["scores"]
            explanation = candidate_data["explanation"]
            
            candidate = RecipeCandidate(
                recipe_id=recipe_id,
                title=metadata.get("title", ""),
                ingredients=metadata.get("ingredients", []),
                instructions=metadata.get("instructions", ""),
                kcal_total=metadata.get("kcal_total", 0),
                protein_g_total=metadata.get("protein_g_total", 0),
                carbs_g_total=metadata.get("carbs_g_total", 0),
                fat_g_total=metadata.get("fat_g_total", 0),
                dietary_tags=metadata.get("dietary_tags", []),
                allergen_tags=metadata.get("allergen_tags", []),
                prep_time_min=metadata.get("prep_time_min", 30),
                cooking_skill=metadata.get("cooking_skill", 2),
                score=scores["final_score"]
            )
            
            # Attach score breakdown and explanation as attributes
            candidate.score_breakdown = scores
            candidate.selection_explanation = explanation
            
            recipe_candidates.append(candidate)
        
        logger.info(f"Returning {len(recipe_candidates)} candidates for {meal_type}")
        
        return recipe_candidates


    def _calculate_advanced_score_with_breakdown(
        self,
        recipe_id: str,
        recipe_metadata: Dict,
        semantic_similarity: float,
        target_kcal: float,
        required_tags: Set[str],
        user_skill: int = 3,
        max_prep_time: Optional[int] = None,
        recently_used_recipes: Optional[Set[str]] = None
    ) -> Dict:
        """
        Calculate advanced hybrid score with full breakdown for explainability.
        
        Args:
            recipe_id: Recipe identifier
            recipe_metadata: Recipe metadata dictionary
            semantic_similarity: Pre-calculated semantic similarity
            target_kcal: Target calorie content
            required_tags: Required dietary tags
            user_skill: User cooking skill level (0-5)
            max_prep_time: Maximum acceptable prep time
            recently_used_recipes: Set of recently used recipe IDs to penalize
            
        Returns:
            Dictionary with detailed score breakdown and explanation
        """
        # Extract recipe data
        recipe_kcal = recipe_metadata.get("kcal_total", 0)
        recipe_tags = set(recipe_metadata.get("dietary_tags", []))
        recipe_skill = recipe_metadata.get("cooking_skill", 3)
        prep_time = recipe_metadata.get("prep_time_min", 30)
        recipe_title = recipe_metadata.get("title", "Unknown")
        
        # Calculate individual scores
        calorie_score = self._calculate_kcal_proximity_score(recipe_kcal, target_kcal)
        dietary_match_score = self._calculate_tag_score(recipe_tags, required_tags)
        skill_match_score = self._calculate_skill_match_score(recipe_skill, user_skill)
        prep_time_score = self._calculate_prep_time_score(prep_time, max_prep_time)
        
        # Check if recently used (negative constraint)
        recency_penalty = 0.0
        if recently_used_recipes and recipe_id in recently_used_recipes:
            recency_penalty = settings.RECENCY_PENALTY
        
        # Define weights
        weights = {
            "semantic": 0.40,
            "calorie": 0.25,
            "dietary": 0.15,
            "skill": 0.10,
            "prep_time": 0.10
        }
        
        # Calculate weighted total
        total_score = (
            weights["semantic"] * semantic_similarity +
            weights["calorie"] * calorie_score +
            weights["dietary"] * dietary_match_score +
            weights["skill"] * skill_match_score +
            weights["prep_time"] * prep_time_score
        )
        
        # Apply recency penalty
        total_score = max(0.0, total_score - recency_penalty)
        
        # Generate human-readable explanation
        explanation = self._generate_explanation(
            semantic_score=semantic_similarity,
            calorie_score=calorie_score,
            dietary_match_score=dietary_match_score,
            skill_match_score=skill_match_score,
            prep_time=prep_time,
            recipe_kcal=recipe_kcal,
            target_kcal=target_kcal,
            recipe_tags=recipe_tags,
            required_tags=required_tags,
            has_recency_penalty=(recency_penalty > 0)
        )
        
        return {
            "recipe_id": recipe_id,
            "recipe_title": recipe_title,
            "semantic_score": round(semantic_similarity, 3),
            "calorie_score": round(calorie_score, 3),
            "dietary_match_score": round(dietary_match_score, 3),
            "skill_match_score": round(skill_match_score, 3),
            "prep_time_score": round(prep_time_score, 3),
            "recency_penalty": round(recency_penalty, 3),
            "total_score": round(total_score, 3),
            "weights_used": weights,
            "explanation": explanation,
            "details": {
                "recipe_kcal": recipe_kcal,
                "target_kcal": target_kcal,
                "prep_time_min": prep_time,
                "cooking_skill_required": recipe_skill,
                "user_skill": user_skill
            }
        }


    def retrieve_candidates_with_explanation(
        self,
        meal_type: str,
        target_kcal: float,
        diet_pref: DietaryPreference,
        allergens: List[str],
        user_skill: int = 3,
        max_prep_time: Optional[int] = None,
        recently_used_recipes: Optional[Set[str]] = None,
        top_k: int = None,
        include_debug: bool = False
    ) -> List[RecipeCandidate]:
        """
        Retrieve recipe candidates with advanced scoring and explainability.
        
        Args:
            meal_type: Type of meal
            target_kcal: Target calorie content
            diet_pref: Dietary preference
            allergens: List of allergens to exclude
            user_skill: User cooking skill level (0-5)
            max_prep_time: Maximum acceptable prep time in minutes
            recently_used_recipes: Set of recently used recipe IDs to deprioritize
            top_k: Number of candidates to return
            include_debug: Include detailed scoring breakdown
            
        Returns:
            List of RecipeCandidate objects with score breakdowns
        """
        # Validate parameters
        if user_skill < 0 or user_skill > 5:
            logger.warning(f"Invalid user_skill {user_skill}, clamping to [0, 5]")
            user_skill = max(0, min(5, user_skill))
        
        if max_prep_time is not None and max_prep_time <= 0:
            logger.warning(f"Invalid max_prep_time {max_prep_time}, ignoring constraint")
            max_prep_time = None
        
        if recently_used_recipes and len(recently_used_recipes) > 100:
            logger.warning(f"Recently used recipes list too large ({len(recently_used_recipes)}), truncating to 100")
            recently_used_recipes = set(list(recently_used_recipes)[:100])
        
        if top_k is None:
            top_k = settings.TOP_K_CANDIDATES
        
        logger.info(f"Retrieving candidates for {meal_type} with advanced scoring (target: {target_kcal} kcal)")
        
        # Build query text
        dietary_prefs = list(self._get_required_tags(diet_pref))
        query_text = self._build_query_text(meal_type, dietary_prefs)
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query_text)
        
        # Get required tags
        required_tags = self._get_required_tags(diet_pref)
        
        # Search vector database
        initial_candidates = self.vector_db.search(
            query_embedding=query_embedding,
            top_k=min(top_k * 3, settings.MAX_CANDIDATES_FOR_SCORING)
        )
        
        # Filter allergens
        filtered_candidates = self._filter_allergens(initial_candidates, allergens)
        
        # Apply negative constraints (prep time, recently used)
        if max_prep_time:
            filtered_candidates = [
                (rid, score, meta) for rid, score, meta in filtered_candidates
                if meta.get("prep_time_min", 999) <= max_prep_time * settings.PREP_TIME_FLEXIBILITY
            ]
        
        # Fallback logic if no candidates found
        if not filtered_candidates:
            logger.warning("No candidates found after filtering, applying fallback logic")
            
            # Try without recency penalty
            if recently_used_recipes:
                logger.info("Fallback: Removing recency constraint")
                recently_used_recipes = None
                # Re-filter without recency (it's applied in scoring, not filtering)
                filtered_candidates = self._filter_allergens(initial_candidates, allergens)
            
            # Try with relaxed prep time
            if not filtered_candidates and max_prep_time:
                logger.info(f"Fallback: Increasing max_prep_time by 50% ({max_prep_time} -> {max_prep_time * 1.5})")
                max_prep_time = int(max_prep_time * 1.5)
                filtered_candidates = [
                    (rid, score, meta) for rid, score, meta in self._filter_allergens(initial_candidates, allergens)
                    if meta.get("prep_time_min", 999) <= max_prep_time * settings.PREP_TIME_FLEXIBILITY
                ]
            
            # Last resort: use initial candidates
            if not filtered_candidates:
                logger.warning("Fallback: Using initial candidates without constraints")
                filtered_candidates = initial_candidates
        
        # Calculate advanced scores with breakdown
        scored_recipes = []
        for recipe_id, semantic_sim, metadata in filtered_candidates:
            score_breakdown = self._calculate_advanced_score_with_breakdown(
                recipe_id=recipe_id,
                recipe_metadata=metadata,
                semantic_similarity=semantic_sim,
                target_kcal=target_kcal,
                required_tags=required_tags,
                user_skill=user_skill,
                max_prep_time=max_prep_time,
                recently_used_recipes=recently_used_recipes
            )
            
            scored_recipes.append((recipe_id, score_breakdown, metadata))
        
        # Sort by total score
        scored_recipes.sort(key=lambda x: x[1]["total_score"], reverse=True)
        
        # Convert to RecipeCandidate objects
        candidates = []
        for recipe_id, score_breakdown, metadata in scored_recipes[:top_k]:
            candidate = RecipeCandidate(
                recipe_id=recipe_id,
                title=metadata.get("title", "Unknown"),
                ingredients=metadata.get("ingredients", []),
                instructions=metadata.get("instructions", ""),
                kcal_total=metadata.get("kcal_total", 0),
                protein_g_total=metadata.get("protein_g_total", 0),
                carbs_g_total=metadata.get("carbs_g_total", 0),
                fat_g_total=metadata.get("fat_g_total", 0),
                dietary_tags=metadata.get("dietary_tags", []),
                allergen_tags=metadata.get("allergen_tags", []),
                prep_time_min=metadata.get("prep_time_min", 30),
                cooking_skill=metadata.get("cooking_skill", 3),
                score=score_breakdown["total_score"],
                score_breakdown=score_breakdown if include_debug else None,
                selection_explanation=score_breakdown["explanation"] if include_debug else None
            )
            candidates.append(candidate)
        
        logger.info(f"Retrieved {len(candidates)} candidates with advanced scoring")
        
        return candidates


    def _apply_preference_adjustments(
        self,
        candidate: RecipeCandidate,
        liked_recipes: Optional[Set[str]],
        disliked_recipes: Optional[Set[str]],
        regional_profile: str
    ) -> tuple:
        """
        Apply preference-based score adjustments.
        
        Args:
            candidate: Recipe candidate
            liked_recipes: Set of liked recipe IDs
            disliked_recipes: Set of disliked recipe IDs
            regional_profile: Regional cuisine preference
            
        Returns:
            Tuple of (adjusted_score, preference_boost, regional_boost)
        """
        base_score = candidate.score
        preference_boost = 0.0
        regional_boost = 0.0
        
        # Apply liked recipe boost
        if liked_recipes and candidate.recipe_id in liked_recipes:
            preference_boost = settings.PREFERENCE_BOOST_LIKED
            logger.debug(f"Boosting liked recipe {candidate.recipe_id} by {preference_boost}")
        
        # Apply disliked recipe penalty
        elif disliked_recipes and candidate.recipe_id in disliked_recipes:
            preference_boost = -settings.PREFERENCE_PENALTY_DISLIKED
            logger.debug(f"Penalizing disliked recipe {candidate.recipe_id} by {abs(preference_boost)}")
        
        # Apply regional boost
        if regional_profile and regional_profile != "global":
            # Check if recipe has matching regional tags
            recipe_tags = set(candidate.dietary_tags) if candidate.dietary_tags else set()
            if regional_profile in recipe_tags:
                regional_boost = settings.REGIONAL_BOOST
                logger.debug(f"Boosting regional match {candidate.recipe_id} for {regional_profile}")
        
        # Calculate adjusted score
        adjusted_score = base_score + preference_boost + regional_boost
        adjusted_score = max(0.0, min(1.0, adjusted_score))  # Clamp to [0, 1]
        
        return adjusted_score, preference_boost, regional_boost

    def retrieve_candidates_with_preferences(
        self,
        meal_type: str,
        target_kcal: float,
        diet_pref: DietaryPreference,
        allergens: List[str],
        user_skill: int = 3,
        max_prep_time: Optional[int] = None,
        recently_used_recipes: Optional[Set[str]] = None,
        liked_recipes: Optional[Set[str]] = None,
        disliked_recipes: Optional[Set[str]] = None,
        regional_profile: str = "global",
        top_k: int = None,
        include_debug: bool = False
    ) -> List[RecipeCandidate]:
        """
        Retrieve recipe candidates with preference-based adjustments.
        
        Args:
            meal_type: Type of meal
            target_kcal: Target calorie content
            diet_pref: Dietary preference
            allergens: List of allergens to exclude
            user_skill: User cooking skill level (0-5)
            max_prep_time: Maximum acceptable prep time in minutes
            recently_used_recipes: Set of recently used recipe IDs to deprioritize
            liked_recipes: Set of recipe IDs user has liked
            disliked_recipes: Set of recipe IDs user has disliked
            regional_profile: User's regional cuisine preference
            top_k: Number of candidates to return
            include_debug: Include detailed scoring breakdown
            
        Returns:
            List of RecipeCandidate objects with preference-adjusted scores
        """
        if top_k is None:
            top_k = settings.TOP_K_CANDIDATES
        
        logger.info(f"Retrieving candidates with preferences for {meal_type} (region: {regional_profile})")
        
        # Get more candidates initially for preference filtering
        initial_top_k = top_k * 2
        
        # Call existing method to get base candidates
        candidates = self.retrieve_candidates_with_explanation(
            meal_type=meal_type,
            target_kcal=target_kcal,
            diet_pref=diet_pref,
            allergens=allergens,
            user_skill=user_skill,
            max_prep_time=max_prep_time,
            recently_used_recipes=recently_used_recipes,
            top_k=initial_top_k,
            include_debug=include_debug
        )
        
        # Apply preference adjustments
        adjusted_candidates = []
        for candidate in candidates:
            adjusted_score, preference_boost, regional_boost = self._apply_preference_adjustments(
                candidate=candidate,
                liked_recipes=liked_recipes,
                disliked_recipes=disliked_recipes,
                regional_profile=regional_profile
            )
            
            # Store original score
            original_score = candidate.score
            
            # Update candidate score
            candidate.score = adjusted_score
            
            # Update score breakdown if debug mode
            if include_debug and hasattr(candidate, 'score_breakdown') and candidate.score_breakdown:
                candidate.score_breakdown["preference_boost"] = round(preference_boost, 3)
                candidate.score_breakdown["regional_boost"] = round(regional_boost, 3)
                candidate.score_breakdown["original_score"] = round(original_score, 3)
                candidate.score_breakdown["adjusted_score"] = round(adjusted_score, 3)
                
                # Update explanation
                explanation_additions = []
                if preference_boost > 0:
                    explanation_additions.append("You've liked this recipe before!")
                elif preference_boost < 0:
                    explanation_additions.append("Lower priority - previously disliked")
                
                if regional_boost > 0:
                    explanation_additions.append(f"Matches your {regional_profile} preference")
                
                if explanation_additions:
                    candidate.score_breakdown["explanation"] += " (" + ", ".join(explanation_additions) + ")"
            
            adjusted_candidates.append(candidate)
        
        # Re-sort by adjusted score
        adjusted_candidates.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"Returning {min(top_k, len(adjusted_candidates))} preference-adjusted candidates")
        
        return adjusted_candidates[:top_k]
