# Personalized Diet Plan Generator

A hybrid AI system that generates personalized daily meal plans using deterministic nutrition calculations, RAG-based recipe retrieval, and phi2 LLM for natural language rendering.

## Features

- **Deterministic Nutrition Engine**: Calculates BMR, TDEE, and macro targets using scientifically validated formulas (Mifflin-St Jeor)
- **RAG Recipe Retrieval**: Hybrid scoring algorithm combining semantic similarity, calorie proximity, and dietary tag matching
- **LLM Rendering**: Uses phi2 for natural language meal plan generation with strict numeric provenance rules
- **Safety-First**: All nutrition values are traceable to verified sources (no LLM hallucination)
- **REST API**: Clean FastAPI interface with OpenAPI documentation
- **Web Interface**: Simple HTML/JS frontend for meal plan generation

## Architecture

```
User Input → Deterministic Engine → RAG Retrieval → LLM Orchestration → Validator → Meal Plan
```

## Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development)
- 8GB+ RAM (for phi2 model)
- PostgreSQL 15+

## Quick Start with Docker

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd personalized-diet-planner
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Prepare sample recipes** (create `data/recipes.json`)
   ```json
   [
     {
       "recipe_id": "recipe_001",
       "title": "Oatmeal with Berries",
       "ingredients": ["1 cup oats", "1/2 cup blueberries", "1 tbsp honey"],
       "instructions": "Cook oats, top with berries and honey",
       "kcal_total": 350,
       "protein_g_total": 12,
       "carbs_g_total": 65,
       "fat_g_total": 6,
       "dietary_tags": ["vegetarian", "vegan"],
       "allergen_tags": [],
       "prep_time_min": 10,
       "cooking_skill": 1
     }
   ]
   ```

4. **Start services**
   ```bash
   docker-compose up -d
   ```

5. **Index recipes**
   ```bash
   docker-compose exec api python scripts/index_recipes.py /app/data/recipes.json
   ```

6. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Local Development Setup

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up PostgreSQL**
   ```bash
   # Start PostgreSQL (or use Docker)
   docker run -d -p 5432:5432 \
     -e POSTGRES_USER=user \
     -e POSTGRES_PASSWORD=password \
     -e POSTGRES_DB=diet_planner \
     postgres:15-alpine
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Run database migrations**
   ```bash
   alembic upgrade head
   ```

5. **Index recipes**
   ```bash
   python scripts/index_recipes.py data/recipes.json
   ```

6. **Start the API server**
   ```bash
   uvicorn src.main:app --reload --port 8000
   ```

7. **Serve the frontend**
   ```bash
   # Use any static file server, e.g.:
   cd frontend
   python -m http.server 3000
   ```

## API Endpoints

### POST /api/v1/generate-plan
Generate a personalized meal plan.

**Request:**
```json
{
  "user_profile": {
    "age": 30,
    "sex": "male",
    "weight_kg": 75,
    "height_cm": 180,
    "activity_level": "moderate",
    "goal": "maintain",
    "goal_rate_kg_per_week": 0,
    "diet_pref": "omnivore",
    "allergies": ["nuts"],
    "wake_time": "07:00:00",
    "lunch_time": "12:00:00",
    "dinner_time": "19:00:00",
    "cooking_skill": 3
  }
}
```

**Response:**
```json
{
  "meal_plan": {
    "plan_id": "...",
    "user_id": "...",
    "date": "2024-01-01T00:00:00",
    "meals": [...],
    "total_nutrition": {
      "kcal": 2000,
      "protein_g": 150,
      "carbs_g": 200,
      "fat_g": 65
    },
    "nutrition_provenance": "DETERMINISTIC_ENGINE_AND_INDEXED_RECIPES",
    "plan_version": "1.0",
    "sources": [...]
  },
  "status": "success"
}
```

### GET /api/v1/recipes/{recipe_id}
Get recipe details by ID.

### GET /api/v1/health
Health check endpoint.

## Configuration

Key environment variables:

- `MODEL_NAME`: LLM model (default: microsoft/phi-2)
- `EMBEDDING_MODEL`: Embedding model (default: sentence-transformers/all-MiniLM-L6-v2)
- `VECTOR_DB_TYPE`: Vector database type (faiss or chroma)
- `DATABASE_URL`: PostgreSQL connection string
- `MIN_DAILY_CALORIES`: Safety floor for daily calories (default: 1200)
- `LLM_TEMPERATURE`: LLM sampling temperature (default: 0.1)

## Project Structure

```
.
├── src/
│   ├── api/              # FastAPI endpoints
│   ├── core/             # Business logic (nutrition engine, RAG, validator)
│   ├── services/         # External services (LLM, embeddings, vector DB)
│   ├── models/           # Pydantic schemas
│   ├── data/             # Database models and repositories
│   └── utils/            # Utilities and logging
├── frontend/             # HTML/JS frontend
├── scripts/              # Utility scripts (indexing, etc.)
├── alembic/              # Database migrations
├── data/                 # Data files (recipes, vector DB)
├── docker-compose.yml    # Docker services configuration
├── Dockerfile            # API service container
└── requirements.txt      # Python dependencies
```

## Testing

Generate a test meal plan:

```bash
curl -X POST http://localhost:8000/api/v1/generate-plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_profile": {
      "age": 30,
      "sex": "male",
      "weight_kg": 75,
      "height_cm": 180,
      "activity_level": "moderate",
      "goal": "maintain",
      "goal_rate_kg_per_week": 0,
      "diet_pref": "omnivore",
      "allergies": [],
      "wake_time": "07:00:00",
      "lunch_time": "12:00:00",
      "dinner_time": "19:00:00",
      "cooking_skill": 3
    }
  }'
```

## Troubleshooting

### Model Loading Issues
- Ensure you have sufficient RAM (8GB+ recommended)
- phi2 model will be downloaded on first run (~5GB)
- Check logs: `docker-compose logs api`

### Recipe Indexing Fails
- Verify recipe JSON format matches schema
- Check that all required nutrition fields are present
- Ensure vector DB directory is writable

### Database Connection Errors
- Verify PostgreSQL is running
- Check DATABASE_URL in .env
- Run migrations: `alembic upgrade head`

## License

MIT

## Contributing

Contributions welcome! Please ensure:
- All nutrition calculations remain deterministic
- LLM outputs are validated for numeric provenance
- Tests pass before submitting PRs
