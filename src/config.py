"""
Configuration management for environment variables and application settings.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Model Configuration
    MODEL_NAME: str = "microsoft/phi-2"
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384  # 384 for MiniLM, 768 for mpnet
    
    # Vector Database
    VECTOR_DB_TYPE: str = "faiss"  # "faiss" or "chroma"
    VECTOR_DB_PATH: str = "./data/vector_db"
    
    # PostgreSQL Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/diet_planner"
    
    # API Configuration
    API_PORT: int = 8000
    API_HOST: str = "0.0.0.0"
    
    # LLM Generation Parameters
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_NEW_TOKENS: int = 800
    
    # RAG Configuration
    TOP_K_CANDIDATES: int = 3
    SEMANTIC_WEIGHT: float = 0.6
    KCAL_PROXIMITY_WEIGHT: float = 0.3
    TAG_WEIGHT: float = 0.1
    
    # Advanced RAG Scoring Configuration
    RECENCY_PENALTY: float = 0.3  # 30% penalty for recently used recipes
    PREP_TIME_FLEXIBILITY: float = 1.5  # Allow 150% of max_prep_time
    SKILL_PENALTY_PER_LEVEL: float = 0.3  # 30% penalty per skill level gap
    MAX_CANDIDATES_FOR_SCORING: int = 30  # top_k * 3 for advanced scoring
    SCORING_TIMEOUT_MS: int = 500  # Maximum time for scoring operation
    
    # Personalization Configuration
    PREFERENCE_BOOST_LIKED: float = 0.2  # 20% boost for liked recipes
    PREFERENCE_PENALTY_DISLIKED: float = 0.5  # 50% penalty for disliked recipes
    REGIONAL_BOOST: float = 0.3  # 30% boost for regional matches
    PREFERENCE_CACHE_TTL: int = 300  # Cache preferences for 5 minutes
    
    # Nutrition Safety
    MIN_DAILY_CALORIES: int = 1200
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


# Global settings instance
settings = Settings()
