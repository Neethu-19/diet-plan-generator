"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.utils.logging_config import logger
from src.config import settings
from src.api.endpoints import router

app = FastAPI(
    title="Personalized Diet Plan Generator",
    description="Hybrid AI system for generating personalized meal plans using deterministic nutrition calculations, RAG-based recipe retrieval, and phi2 LLM for natural language rendering. All numeric nutrition values are traceable to verified sources.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "status": "error"}
    )


@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    logger.info("Starting Personalized Diet Plan Generator")
    logger.info(f"Model: {settings.MODEL_NAME}")
    logger.info(f"Embedding Model: {settings.EMBEDDING_MODEL}")
    logger.info(f"Vector DB: {settings.VECTOR_DB_TYPE}")
    
    # Initialize services
    try:
        from src.api.endpoints import (
            nutrition_engine, rag_module, llm_orchestrator, validator
        )
        from src.core.nutrition_engine import NutritionEngine
        from src.core.rag_module import RAGModule
        from src.services.llm_service import LLMOrchestrator
        from src.core.validator import MealPlanValidator
        from src.api import endpoints
        
        logger.info("Initializing core services...")
        
        # Initialize nutrition engine
        endpoints.nutrition_engine = NutritionEngine()
        logger.info("✓ Nutrition engine initialized")
        
        # Initialize validator
        endpoints.validator = MealPlanValidator()
        logger.info("✓ Validator initialized")
        
        # Initialize RAG module (loads embedding service and vector DB)
        logger.info("Loading RAG module (this may take a moment)...")
        endpoints.rag_module = RAGModule()
        logger.info("✓ RAG module initialized")
        
        # Initialize LLM orchestrator (loads phi2 model) - OPTIONAL
        # Disabled to save memory - using simple planner instead
        logger.info("Skipping LLM model loading (using simple planner)")
        endpoints.llm_orchestrator = None
        logger.info("✓ Simple planner mode enabled")
        
        logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        logger.warning("Application started but some services may not be available")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down Personalized Diet Plan Generator")


# Register API routes
app.include_router(router, prefix="/api/v1", tags=["Meal Planning"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Personalized Diet Plan Generator API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
