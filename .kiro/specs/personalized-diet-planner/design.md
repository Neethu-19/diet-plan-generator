# Design Document

## Overview

The Personalized Diet Plan Generator is a hybrid AI system combining deterministic nutrition science with intelligent recipe retrieval and natural language generation. The architecture ensures all numeric nutrition data originates from verified sources (deterministic calculations or indexed recipes) while leveraging phi2 LLM for natural language rendering and recipe selection.

**Core Design Principles:**
- Numeric provenance: All nutrition values traceable to deterministic engine or indexed data
- Safety-first: Validator rejects LLM hallucinations of nutrition data
- Hybrid intelligence: Deterministic calculations + RAG retrieval + LLM rendering
- Lightweight deployment: phi2 model for efficient local/cloud deployment
- API-first: Clean REST interface for frontend and third-party integrations

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                          │
│  (React/HTML Form → API Client → Plan Viewer)                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/JSON
┌────────────────────────▼────────────────────────────────────────┐
│                      FastAPI Service                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │   Endpoints  │  │  Validators  │  │  Error Handlers    │   │
│  └──────┬───────┘  └──────┬───────┘  └────────────────────┘   │
└─────────┼──────────────────┼──────────────────────────────────┘
          │                  │
┌─────────▼──────────────────▼──────────────────────────────────┐
│                    Core Business Logic                         │
│  ┌─────────────────────┐  ┌──────────────────────────────┐   │
│  │ Deterministic Engine│  │      RAG Module              │   │
│  │ - BMR/TDEE Calc     │  │ - Query Embedding            │   │
│  │ - Macro Split       │  │ - Similarity Search          │   │
│  │ - Meal Distribution │  │ - Hybrid Scoring             │   │
│  └─────────────────────┘  └──────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │           LLM Orchestration Layer                       │  │
│  │  - Prompt Construction                                  │  │
│  │  - phi2 Inference (temperature=0.1)                     │  │
│  │  - JSON Schema Enforcement                              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │         Post-Processing Validator                       │  │
│  │  - Numeric Provenance Check                             │  │
│  │  - Schema Validation                                    │  │
│  │  - Safety Constraint Enforcement                        │  │
│  └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

          │                                    │
┌─────────▼────────────────────────────────────▼─────────────────┐
│                      Data Layer                                 │
│  ┌──────────────────┐  ┌────────────────────────────────────┐ │
│  │  PostgreSQL DB   │  │    Vector Database (FAISS/Chroma)  │ │
│  │  - User Profiles │  │    - Recipe Embeddings (384/768-d) │ │
│  │  - Meal Plans    │  │    - Metadata (nutrition, tags)    │ │
│  │  - Swap History  │  │    - Indexed by recipe_id          │ │
│  └──────────────────┘  └────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow for Meal Plan Generation

```
1. User submits profile → FastAPI validates input
2. Deterministic Engine calculates BMR/TDEE/macros/meal targets
3. For each meal slot:
   a. RAG Module generates query embedding
   b. Vector DB returns top-K candidates (K=3)
   c. Hybrid scoring: 0.6*semantic + 0.3*kcal_prox + 0.1*tags
4. LLM Orchestrator constructs cursor messages:
   - System: strict rules (no numeric invention)
   - User: profile + targets + retrieved recipes
   - Assistant schema: JSON template
5. phi2 generates meal plan JSON (temp=0.1)
6. Validator checks:
   - All nutrition numbers from input context
   - JSON schema compliance
   - Safety constraints (min 1200 kcal)
7. Return validated plan or error
```

## Components and Interfaces

### 1. Deterministic Nutrition Engine

**Responsibility:** Calculate all user-specific nutrition targets using validated formulas.

**Interface:**
```python
class DeterministicEngine:
    def calculate_nutrition_targets(
        self, 
        user_profile: UserProfile
    ) -> NutritionTargets:
        """
        Returns: NutritionTargets with bmr, tdee, target_kcal,
                 protein_g, carbs_g, fat_g, meal_splits
        """
        pass
```

**Key Formulas:**
- BMR (Mifflin-St Jeor): `10*weight_kg + 6.25*height_cm - 5*age + sex_constant`
  - sex_constant: 5 (male), -161 (female), -78 (other, average)
- TDEE: `BMR * activity_multiplier`
  - sedentary: 1.2, light: 1.375, moderate: 1.55, active: 1.725, very_active: 1.9
- Target calories: `TDEE + (goal_rate_kg_per_week * 7700 / 7)`
- Safety floor: `max(target_kcal, 1200)`
- Protein: `max(1.6 * weight_kg, 0.20 * target_kcal / 4)`
- Fat: `0.25 * target_kcal / 9`
- Carbs: `(target_kcal - protein*4 - fat*9) / 4`
- Meal splits (default): breakfast 25%, lunch 35%, dinner 30%, snacks 10%

### 2. RAG Retrieval Module

**Responsibility:** Retrieve and rank recipe candidates based on hybrid scoring.

**Interface:**
```python
class RAGModule:
    def __init__(
        self, 
        embedding_model: str = "all-MiniLM-L6-v2",
        vector_db: VectorDatabase
    ):
        pass
    
    def retrieve_candidates(
        self,
        meal_type: str,
        target_kcal: float,
        dietary_prefs: List[str],
        allergens: List[str],
        top_k: int = 3
    ) -> List[RecipeCandidate]:
        """
        Returns: Top-K recipes ranked by hybrid score
        """
        pass
```

**Hybrid Scoring Algorithm:**
```python
def compute_hybrid_score(
    query_embedding: np.ndarray,
    recipe_embedding: np.ndarray,
    recipe_kcal: float,
    target_kcal: float,
    recipe_tags: Set[str],
    required_tags: Set[str]
) -> float:
    # Semantic similarity (cosine)
    s_sem = cosine_similarity(query_embedding, recipe_embedding)
    s_sem = (s_sem + 1) / 2  # Normalize to [0,1]
    
    # Calorie proximity
    kcal_diff = abs(recipe_kcal - target_kcal)
    kcal_prox = max(0, 1 - kcal_diff / target_kcal)
    
    # Tag matching
    if len(required_tags) > 0:
        tag_score = len(recipe_tags & required_tags) / len(required_tags)
    else:
        tag_score = 1.0
    
    # Weighted combination
    final_score = 0.6 * s_sem + 0.3 * kcal_prox + 0.1 * tag_score
    return final_score
```

**Embedding Model:**
- Primary: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- Alternative: `all-mpnet-base-v2` (768 dimensions, higher quality)
- Embed: recipe title + ingredient list concatenated

**Vector Database Schema:**
```python
RecipeDocument = {
    "recipe_id": str,
    "title": str,
    "ingredients": List[str],
    "instructions": str,
    "embedding": np.ndarray,  # 384 or 768-d
    "kcal_total": float,
    "protein_g_total": float,
    "carbs_g_total": float,
    "fat_g_total": float,
    "dietary_tags": List[str],  # ["vegan", "gluten-free", ...]
    "allergen_tags": List[str],  # ["nuts", "dairy", ...]
    "prep_time_min": int,
    "cooking_skill": int  # 0-5
}
```

### 3. LLM Orchestration Layer

**Responsibility:** Construct prompts, call phi2, enforce JSON output.

**Interface:**
```python
class LLMOrchestrator:
    def __init__(self, model_name: str = "microsoft/phi-2"):
        self.model = load_model(model_name)
        self.tokenizer = load_tokenizer(model_name)
    
    def generate_meal_plan(
        self,
        nutrition_targets: NutritionTargets,
        meal_candidates: Dict[str, List[RecipeCandidate]],
        user_profile: UserProfile
    ) -> Dict:
        """
        Returns: Raw LLM output (JSON string)
        """
        pass
```

**Prompt Template (Cursor-Style Messages):**

```python
SYSTEM_MESSAGE = """You are a meal planning assistant. Your role is to select recipes from provided candidates and format them into a daily meal plan.

CRITICAL RULES:
1. You MUST NOT compute, estimate, or invent ANY numeric nutrition values (kcal, protein, 