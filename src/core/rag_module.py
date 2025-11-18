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
        kcal_proximity: float,
        tag_score: float,
        recipe_kcal: float,
        target_kcal: float,
        recipe_tags: Set[str],
        required_tags: Set[str]
    ) -> str:
        """
        Generate human-readable explanation for recipe selection.
        
        Args:
            semantic_score: Semantic similarity score
            kcal_proximity: Calorie proximity score
            tag_score: Tag matching score
            recipe_kcal: Recipe calories
            target_kcal: Target calories
            recipe_tags: Recipe dietary tags
            required_tags: Required dietary tags
            
        Returns:
            Human-readable explanation string
        """
        reasons = []
        
        # Calorie match
        if kcal_proximity >= 0.9:
            reasons.append(f"excellent calorie match ({recipe_kcal:.0f} vs {target_kcal:.0f} target)")
        elif kcal_proximity >= 0.7:
            reasons.append(f"good calorie match ({recipe_kcal:.0f} vs {target_kcal:.0f} target)")
        elif kcal_proximity >= 0.5:
            reasons.append(f"moderate calorie match ({recipe_kcal:.0f} vs {target_kcal:.0f} target)")
        
        # Dietary match
        if tag_score == 1.0 and required_tags:
            matching = recipe_tags & required_tags
            reasons.append(f"perfect dietary fit ({', '.join(matching)})")
        elif tag_score >= 0.5 and required_tags:
            matching = recipe_tags & required_tags
            reasons.append(f"matches dietary preferences ({', '.join(matching)})")
        
        # Semantic relevance
        if semantic_score >= 0.8:
            reasons.append("highly relevant to meal type")
        elif semantic_score >= 0.6:
            reasons.append("relevant to meal type")
        
        if not reasons:
            reasons.append("best available option")
        
        return "Chosen for: " + ", ".join(reasons)
    
    
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
