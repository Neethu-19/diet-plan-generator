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
