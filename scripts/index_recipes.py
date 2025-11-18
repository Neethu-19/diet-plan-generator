"""
Script to index recipes into the vector database.
Loads recipes from JSON, preprocesses them, generates embeddings, and indexes.
"""
# MUST set this before any imports to avoid TensorFlow issues
import os
os.environ['TRANSFORMERS_NO_TF'] = '1'

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.recipe_preprocessor import RecipePreprocessor
from src.services.embedding_service import EmbeddingService
from src.services.vector_db import create_vector_database
from src.utils.logging_config import logger
from src.config import settings


def load_recipes_from_json(file_path: str):
    """
    Load recipes from JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        List of recipe dictionaries
    """
    logger.info(f"Loading recipes from {file_path}")
    
    with open(file_path, 'r') as f:
        recipes = json.load(f)
    
    logger.info(f"Loaded {len(recipes)} recipes")
    return recipes


def index_recipes(recipes_file: str):
    """
    Main indexing pipeline.
    
    Args:
        recipes_file: Path to recipes JSON file
    """
    logger.info("Starting recipe indexing pipeline")
    
    # Step 1: Load recipes
    recipes = load_recipes_from_json(recipes_file)
    
    # Step 2: Preprocess recipes
    logger.info("Preprocessing recipes...")
    preprocessor = RecipePreprocessor()
    preprocessed_recipes = preprocessor.preprocess_recipes(recipes)
    
    if not preprocessed_recipes:
        logger.error("No valid recipes to index")
        return
    
    # Step 3: Initialize embedding service
    logger.info("Initializing embedding service...")
    embedding_service = EmbeddingService()
    embedding_dim = embedding_service.get_embedding_dimension()
    
    # Step 4: Generate embeddings
    logger.info("Generating embeddings...")
    embeddings = embedding_service.generate_recipe_embeddings_batch(
        preprocessed_recipes,
        batch_size=32
    )
    
    # Step 5: Initialize vector database
    logger.info("Initializing vector database...")
    vector_db = create_vector_database(dimension=embedding_dim)
    
    # Step 6: Index recipes
    logger.info("Indexing recipes...")
    for recipe, embedding in zip(preprocessed_recipes, embeddings):
        recipe_id = recipe["recipe_id"]
        
        # Prepare metadata (everything except recipe_id)
        metadata = {k: v for k, v in recipe.items() if k != "recipe_id"}
        
        # Add to vector database
        vector_db.add_recipe(recipe_id, embedding, metadata)
    
    # Step 7: Save index
    logger.info("Saving index...")
    vector_db.save()
    
    logger.info(f"Successfully indexed {len(preprocessed_recipes)} recipes")
    logger.info(f"Index saved to {settings.VECTOR_DB_PATH}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/index_recipes.py <recipes_json_file>")
        print("Example: python scripts/index_recipes.py data/recipes.json")
        sys.exit(1)
    
    recipes_file = sys.argv[1]
    
    if not os.path.exists(recipes_file):
        print(f"Error: File not found: {recipes_file}")
        sys.exit(1)
    
    try:
        index_recipes(recipes_file)
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        sys.exit(1)
