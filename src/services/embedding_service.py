"""
Embedding generation service using sentence-transformers.
Generates embeddings for recipe text (title + ingredients).
"""
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer
from src.config import settings
from src.utils.logging_config import logger


class EmbeddingService:
    """Service for generating text embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = None):
        """
        Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        logger.info(f"Loading embedding model: {self.model_name}")
        
        try:
            self.model = SentenceTransformer(self.model_name)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Embedding model loaded. Dimension: {self.embedding_dim}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def create_recipe_text(self, recipe: Dict[str, Any]) -> str:
        """
        Create text representation of recipe for embedding.
        Combines title and ingredients.
        
        Args:
            recipe: Recipe dictionary with title and ingredients
            
        Returns:
            Combined text string
        """
        title = recipe.get("title", "")
        ingredients = recipe.get("ingredients", [])
        
        # Combine title and ingredients
        ingredients_text = ", ".join(ingredients)
        recipe_text = f"{title}. Ingredients: {ingredients_text}"
        
        return recipe_text
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of input texts
            batch_size: Batch size for processing
            
        Returns:
            Array of embeddings with shape (len(texts), embedding_dim)
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts")
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                show_progress_bar=True
            )
            logger.info(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise
    
    def generate_recipe_embedding(self, recipe: Dict[str, Any]) -> np.ndarray:
        """
        Generate embedding for a recipe.
        
        Args:
            recipe: Recipe dictionary
            
        Returns:
            Embedding vector
        """
        recipe_text = self.create_recipe_text(recipe)
        return self.generate_embedding(recipe_text)
    
    def generate_recipe_embeddings_batch(
        self, 
        recipes: List[Dict[str, Any]], 
        batch_size: int = 32
    ) -> np.ndarray:
        """
        Generate embeddings for a batch of recipes.
        
        Args:
            recipes: List of recipe dictionaries
            batch_size: Batch size for processing
            
        Returns:
            Array of embeddings
        """
        recipe_texts = [self.create_recipe_text(recipe) for recipe in recipes]
        return self.generate_embeddings_batch(recipe_texts, batch_size=batch_size)
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Embedding dimension
        """
        return self.embedding_dim
