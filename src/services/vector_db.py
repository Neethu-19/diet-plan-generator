"""
Vector database integration supporting FAISS and Chroma.
Stores recipe embeddings with metadata for retrieval.
"""
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import json
import os
from abc import ABC, abstractmethod
from src.config import settings
from src.utils.logging_config import logger


class VectorDatabase(ABC):
    """Abstract base class for vector database implementations."""
    
    @abstractmethod
    def add_recipe(self, recipe_id: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """Add a recipe with its embedding and metadata."""
        pass
    
    @abstractmethod
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar recipes."""
        pass
    
    @abstractmethod
    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get recipe metadata by ID."""
        pass
    
    @abstractmethod
    def save(self):
        """Save the index to disk."""
        pass
    
    @abstractmethod
    def load(self):
        """Load the index from disk."""
        pass


class FAISSVectorDatabase(VectorDatabase):
    """FAISS-based vector database implementation."""
    
    def __init__(self, dimension: int, index_path: str = None):
        """
        Initialize FAISS vector database.
        
        Args:
            dimension: Embedding dimension
            index_path: Path to save/load index
        """
        import faiss
        
        self.dimension = dimension
        self.index_path = index_path or settings.VECTOR_DB_PATH
        
        # Create FAISS index (using L2 distance, will normalize for cosine similarity)
        self.index = faiss.IndexFlatL2(dimension)
        
        # Store metadata separately
        self.recipe_ids: List[str] = []
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info(f"Initialized FAISS index with dimension {dimension}")
    
    def add_recipe(self, recipe_id: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """
        Add a recipe to the index.
        
        Args:
            recipe_id: Unique recipe identifier
            embedding: Recipe embedding vector
            metadata: Recipe metadata (nutrition, tags, etc.)
        """
        # Normalize embedding for cosine similarity
        embedding = embedding.astype('float32')
        embedding = embedding / np.linalg.norm(embedding)
        
        # Add to FAISS index
        self.index.add(embedding.reshape(1, -1))
        
        # Store metadata
        self.recipe_ids.append(recipe_id)
        self.metadata[recipe_id] = metadata
        
        logger.debug(f"Added recipe {recipe_id} to index")
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for similar recipes.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filters: Optional filters (allergens to exclude, dietary tags to match)
            
        Returns:
            List of (recipe_id, similarity_score, metadata) tuples
        """
        # Normalize query embedding
        query_embedding = query_embedding.astype('float32')
        query_embedding = query_embedding / np.linalg.norm(query_embedding)
        
        # Search FAISS index (get more results for filtering)
        search_k = min(top_k * 10, len(self.recipe_ids))
        distances, indices = self.index.search(query_embedding.reshape(1, -1), search_k)
        
        # Convert L2 distances to cosine similarity scores
        # Since vectors are normalized, L2 distance relates to cosine similarity
        # similarity = 1 - (distance^2 / 2)
        similarities = 1 - (distances[0] ** 2 / 2)
        
        # Collect results with metadata
        results = []
        for idx, similarity in zip(indices[0], similarities):
            if idx < len(self.recipe_ids):
                recipe_id = self.recipe_ids[idx]
                metadata = self.metadata[recipe_id]
                
                # Apply filters
                if filters:
                    if not self._apply_filters(metadata, filters):
                        continue
                
                results.append((recipe_id, float(similarity), metadata))
        
        # Return top_k results
        return results[:top_k]
    
    def _apply_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        Apply filters to recipe metadata.
        
        Args:
            metadata: Recipe metadata
            filters: Filter criteria
            
        Returns:
            True if recipe passes filters
        """
        # Filter out allergens
        if "exclude_allergens" in filters:
            recipe_allergens = set(metadata.get("allergen_tags", []))
            exclude_allergens = set(filters["exclude_allergens"])
            if recipe_allergens & exclude_allergens:
                return False
        
        # Match dietary tags
        if "required_dietary_tags" in filters:
            recipe_tags = set(metadata.get("dietary_tags", []))
            required_tags = set(filters["required_dietary_tags"])
            if not required_tags.issubset(recipe_tags):
                return False
        
        return True
    
    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """
        Get recipe metadata by ID.
        
        Args:
            recipe_id: Recipe identifier
            
        Returns:
            Recipe metadata or None if not found
        """
        return self.metadata.get(recipe_id)
    
    def save(self):
        """Save the index and metadata to disk."""
        import faiss
        
        os.makedirs(self.index_path, exist_ok=True)
        
        # Save FAISS index
        index_file = os.path.join(self.index_path, "faiss.index")
        faiss.write_index(self.index, index_file)
        
        # Save metadata
        metadata_file = os.path.join(self.index_path, "metadata.json")
        with open(metadata_file, 'w') as f:
            json.dump({
                "recipe_ids": self.recipe_ids,
                "metadata": self.metadata
            }, f)
        
        logger.info(f"Saved FAISS index to {self.index_path}")
    
    def load(self):
        """Load the index and metadata from disk."""
        import faiss
        
        index_file = os.path.join(self.index_path, "faiss.index")
        metadata_file = os.path.join(self.index_path, "metadata.json")
        
        if not os.path.exists(index_file) or not os.path.exists(metadata_file):
            logger.warning(f"Index files not found at {self.index_path}")
            return
        
        # Load FAISS index
        self.index = faiss.read_index(index_file)
        
        # Load metadata
        with open(metadata_file, 'r') as f:
            data = json.load(f)
            self.recipe_ids = data["recipe_ids"]
            self.metadata = data["metadata"]
        
        logger.info(f"Loaded FAISS index from {self.index_path} with {len(self.recipe_ids)} recipes")


class ChromaVectorDatabase(VectorDatabase):
    """Chroma-based vector database implementation."""
    
    def __init__(self, dimension: int, index_path: str = None):
        """
        Initialize Chroma vector database.
        
        Args:
            dimension: Embedding dimension
            index_path: Path to save/load collection
        """
        import chromadb
        
        self.dimension = dimension
        self.index_path = index_path or settings.VECTOR_DB_PATH
        
        # Create Chroma client
        self.client = chromadb.PersistentClient(path=self.index_path)
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="recipes",
            metadata={"dimension": dimension}
        )
        
        logger.info(f"Initialized Chroma collection with dimension {dimension}")
    
    def add_recipe(self, recipe_id: str, embedding: np.ndarray, metadata: Dict[str, Any]):
        """Add a recipe to the collection."""
        # Convert metadata values to strings for Chroma
        chroma_metadata = {
            k: str(v) if not isinstance(v, (str, int, float, bool)) else v
            for k, v in metadata.items()
        }
        
        self.collection.add(
            ids=[recipe_id],
            embeddings=[embedding.tolist()],
            metadatas=[chroma_metadata]
        )
        
        logger.debug(f"Added recipe {recipe_id} to Chroma collection")
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Search for similar recipes."""
        # Build where clause for filters
        where = None
        if filters and "exclude_allergens" in filters:
            # Note: Chroma filtering is limited, may need post-filtering
            pass
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where
        )
        
        # Format results
        formatted_results = []
        if results['ids'] and len(results['ids']) > 0:
            for i, recipe_id in enumerate(results['ids'][0]):
                similarity = 1 - results['distances'][0][i]  # Convert distance to similarity
                metadata = results['metadatas'][0][i]
                formatted_results.append((recipe_id, similarity, metadata))
        
        return formatted_results
    
    def get_recipe(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get recipe metadata by ID."""
        results = self.collection.get(ids=[recipe_id])
        if results['ids']:
            return results['metadatas'][0]
        return None
    
    def save(self):
        """Chroma persists automatically."""
        logger.info("Chroma collection persisted automatically")
    
    def load(self):
        """Chroma loads automatically on init."""
        logger.info("Chroma collection loaded automatically")


def create_vector_database(dimension: int, db_type: str = None) -> VectorDatabase:
    """
    Factory function to create vector database instance.
    
    Args:
        dimension: Embedding dimension
        db_type: Type of database ("faiss" or "chroma")
        
    Returns:
        VectorDatabase instance
    """
    db_type = db_type or settings.VECTOR_DB_TYPE
    
    if db_type == "faiss":
        return FAISSVectorDatabase(dimension)
    elif db_type == "chroma":
        return ChromaVectorDatabase(dimension)
    else:
        raise ValueError(f"Unsupported vector database type: {db_type}")
