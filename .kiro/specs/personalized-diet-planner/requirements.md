# Requirements Document

## Introduction

The Personalized Diet Plan Generator is a hybrid AI system that produces daily meal plans for students and professionals. The system combines a deterministic nutrition calculation engine with RAG-based recipe retrieval and phi2 LLM for natural language rendering. The system accepts user inputs (demographics, activity level, dietary preferences, allergies, schedule) and generates nutritionally balanced meal plans while ensuring all numeric nutrition data originates from deterministic calculations or indexed recipe databases—never from LLM hallucination.

## Glossary

- **System**: The Personalized Diet Plan Generator application
- **Deterministic Engine**: The calculation module that computes BMR, TDEE, macro targets, and meal splits using established formulas
- **RAG Module**: The Retrieval-Augmented Generation component that retrieves relevant recipes from the vector database
- **phi2**: The lightweight language model (microsoft/phi-2) used for natural language rendering of meal plans
- **Vector Database**: The indexed storage of recipe embeddings (FAISS/Chroma) with metadata
- **Nutrition Provenance**: The traceable source of all numeric nutrition values (deterministic engine or indexed recipe)
- **User Profile**: The collection of user inputs including age, sex, weight, height, activity level, goals, dietary preferences, allergies, and schedule
- **Meal Plan**: A structured daily schedule of meals with recipes, portions, and complete nutrition information
- **BMR**: Basal Metabolic Rate calculated using Mifflin-St Jeor equation
- **TDEE**: Total Daily Energy Expenditure (BMR × activity multiplier)
- **Validator**: The post-processing component that verifies LLM outputs comply with numeric provenance rules

## Requirements

### Requirement 1: User Profile Input

**User Story:** As a user, I want to provide my personal information and preferences, so that the system can generate a meal plan tailored to my specific needs.

#### Acceptance Criteria

1. THE System SHALL accept user inputs including age (integer), sex (enumeration: male, female, other), weight in kilograms (float), height in centimeters (float), activity level (enumeration: sedentary, light, moderate, active, very_active), goal (enumeration: lose, maintain, gain), goal rate in kilograms per week (signed float), dietary preference (enumeration: vegan, vegetarian, ovo-lacto, pesco, omnivore), allergies (list of strings), schedule (wake time, lunch time, dinner time as time values), cooking skill (integer 0-5), and optional budget per week (float).

2. WHEN the System receives a user profile input, THE System SHALL validate that all required fields are present and within acceptable ranges.

3. IF any required field is missing or invalid, THEN THE System SHALL return a validation error response with specific field-level error messages.

4. THE System SHALL store validated user profiles with a unique identifier for subsequent meal plan generation requests.

### Requirement 2: Deterministic Nutrition Calculation

**User Story:** As a user, I want the system to calculate my daily caloric and macro needs using scientifically validated formulas, so that my meal plan is nutritionally appropriate for my goals.

#### Acceptance Criteria

1. THE System SHALL calculate Basal Metabolic Rate using the Mifflin-St Jeor equation: BMR = (10 × weight_kg) + (6.25 × height_cm) - (5 × age) + sex_constant, where sex_constant equals 5 for male and -161 for female.

2. THE System SHALL calculate Total Daily Energy Expenditure by multiplying BMR by an activity multiplier: 1.2 for sedentary, 1.375 for light, 1.55 for moderate, 1.725 for active, and 1.9 for very_active.

3. THE System SHALL calculate target daily calories by adjusting TDEE based on goal and goal rate, where caloric adjustment equals goal_rate_kg_per_week × 7700 ÷ 7.

4. THE System SHALL enforce a minimum daily calorie floor of 1200 kcal regardless of calculated target.

5. THE System SHALL calculate protein target as the maximum of 1.6 grams per kilogram body weight or 20 percent of target calories divided by 4.

6. THE System SHALL calculate fat target as 25 percent of target calories divided by 9.

7. THE System SHALL calculate carbohydrate target as remaining calories after protein and fat allocation divided by 4.

8. THE System SHALL distribute daily calorie target across meals using configurable split ratios (default: breakfast 25%, lunch 35%, dinner 30%, snacks 10%).

### Requirement 3: Recipe Retrieval and Indexing

**User Story:** As a user, I want the system to retrieve recipes that match my dietary preferences and nutritional needs, so that my meal plan includes foods I can and want to eat.

#### Acceptance Criteria

1. THE System SHALL maintain a vector database of recipe embeddings with metadata including recipe_id, title, ingredients, instructions, kcal_total, protein_g_total, carbs_g_total, fat_g_total, dietary_tags, allergen_tags, and preparation_time.

2. WHEN generating a meal plan, THE System SHALL retrieve candidate recipes by computing a composite score: final_score = 0.6 × semantic_similarity + 0.3 × kcal_proximity_score + 0.1 × tag_score.

3. THE System SHALL calculate semantic similarity as normalized cosine similarity between query embedding and recipe embedding in range [0,1].

4. THE System SHALL calculate kcal_proximity_score as max(0, 1 - abs(recipe_kcal - target_kcal) / target_kcal).

5. THE System SHALL calculate tag_score as (count of matching dietary tags / count of required tags) clipped to range [0,1].

6. THE System SHALL retrieve the top 3 candidate recipes for each meal slot based on final_score ranking.

7. THE System SHALL filter out recipes containing any allergens specified in the user profile before scoring.

8. THE System SHALL use sentence-transformers model (all-MiniLM-L6-v2 or all-mpnet-base-v2) for generating recipe embeddings with dimension 384 or 768 respectively.

### Requirement 4: LLM-Based Meal Plan Rendering

**User Story:** As a user, I want to receive my meal plan in natural, readable language with clear instructions, so that I can easily understand and follow the plan.

#### Acceptance Criteria

1. WHEN rendering a meal plan, THE System SHALL provide phi2 with a system message containing strict rules prohibiting numeric nutrition invention, a user message containing user profile and deterministic nutrition targets, and retrieved recipe candidates with complete nutrition data.

2. THE System SHALL configure phi2 with temperature between 0.0 and 0.2 and max_new_tokens of 800 to minimize randomness.

3. THE System SHALL instruct phi2 to select one recipe per meal from provided candidates and render the meal plan as valid JSON matching the defined schema.

4. THE System SHALL require phi2 output to include fields: plan_id, user_id, date, meals (array), total_nutrition, nutrition_provenance, plan_version, and sources.

5. WHEN a retrieved recipe lacks complete nutrition data, THE System SHALL instruct phi2 to mark that meal with nutrition_status as "MISSING_NUTRITION" and omit numeric values.

6. THE System SHALL include in each meal object: meal_type, recipe_id, recipe_title, portion_size, ingredients, instructions, kcal, protein_g, carbs_g, fat_g, and nutrition_status.

### Requirement 5: Nutrition Provenance and Safety

**User Story:** As a user, I want to trust that all nutrition numbers in my meal plan come from verified sources, so that I can rely on the accuracy of the information for my health goals.

#### Acceptance Criteria

1. THE System SHALL enforce that all numeric nutrition values (kcal, protein_g, carbs_g, fat_g) in the final meal plan originate exclusively from the Deterministic Engine or indexed recipe documents.

2. THE System SHALL reject any LLM output that contains numeric nutrition values not present in the provided input context.

3. WHEN the Validator detects invented numeric nutrition values, THE System SHALL return an error response and log the violation for monitoring.

4. THE System SHALL include a nutrition_provenance field in each meal indicating the source as "INDEXED_RECIPE" or "ESTIMATED_SERVER_SIDE".

5. WHERE the user opts in to server-side estimation, THE System SHALL provide an endpoint to estimate nutrition by composing ingredient-level data from a foods database and mark results with nutrition_status as "ESTIMATED".

6. THE System SHALL include a sources array mapping each meal to recipe_id, source_doc_id, and source_snippet_excerpt for traceability.

### Requirement 6: Meal Swap and Substitution

**User Story:** As a user, I want to request swaps or substitutions for specific meals, so that I can adjust my plan based on availability or preference changes.

#### Acceptance Criteria

1. WHEN the user requests a meal swap, THE System SHALL accept swap request parameters including plan_id, meal_type, and optional constraints (different_protein, different_cuisine, faster_prep).

2. THE System SHALL retrieve alternative recipe candidates using the same retrieval algorithm with updated constraints.

3. THE System SHALL provide the alternative candidates to phi2 with a swap-specific prompt template.

4. THE System SHALL return an updated meal plan with the swapped meal while preserving other meals and maintaining overall daily nutrition targets within 10 percent tolerance.

5. THE System SHALL include swap_history metadata tracking original recipe_id and swap reason.

### Requirement 7: API Service Interface

**User Story:** As a developer integrating with this system, I want a well-defined REST API with clear contracts, so that I can reliably build client applications.

#### Acceptance Criteria

1. THE System SHALL expose a POST /generate-plan endpoint accepting user profile JSON and returning a complete meal plan JSON response.

2. THE System SHALL expose a POST /swap endpoint accepting plan_id, meal_type, and optional constraints, returning an updated meal plan.

3. THE System SHALL expose a GET /recipes/{recipe_id} endpoint returning complete recipe details including nutrition data.

4. WHERE server-side estimation is enabled, THE System SHALL expose a POST /estimate-nutrition endpoint accepting recipe_id and returning estimated nutrition with ESTIMATED status marker.

5. THE System SHALL return HTTP 400 for validation errors with detailed field-level error messages in JSON format.

6. THE System SHALL return HTTP 500 for internal errors with a generic error message and log detailed error information server-side.

7. THE System SHALL include OpenAPI/Swagger documentation accessible at /docs endpoint.

### Requirement 8: Data Pipeline and Embedding Generation

**User Story:** As a system administrator, I want an automated pipeline to process and index new recipes, so that the recipe database stays current and searchable.

#### Acceptance Criteria

1. THE System SHALL provide a data preprocessing pipeline that cleans recipe text, validates nutrition data completeness, and normalizes dietary and allergen tags.

2. THE System SHALL generate embeddings for recipe titles and ingredient lists using the configured sentence-transformers model.

3. THE System SHALL index recipe embeddings in the vector database (FAISS or Chroma) with associated metadata.

4. WHEN a new recipe is added, THE System SHALL validate that kcal_total, protein_g_total, carbs_g_total, and fat_g_total fields are present and numeric.

5. THE System SHALL reject recipes with missing or invalid nutrition data from indexing unless marked for server-side estimation.

### Requirement 9: Frontend User Interface

**User Story:** As a user, I want a simple web interface to input my information and view my meal plan, so that I can interact with the system without technical knowledge.

#### Acceptance Criteria

1. THE System SHALL provide a web-based onboarding form collecting all required user profile fields with appropriate input types and validation.

2. THE System SHALL display generated meal plans in a structured view showing each meal with recipe title, ingredients, instructions, portion size, and nutrition breakdown.

3. WHEN viewing a meal plan, THE System SHALL provide a swap button for each meal that triggers the swap flow.

4. THE System SHALL display total daily nutrition summary with progress indicators comparing actual to target values.

5. THE System SHALL display loading states during meal plan generation with estimated wait time.

### Requirement 10: Deployment and Environment Configuration

**User Story:** As a developer, I want clear deployment instructions and environment configuration, so that I can run the system locally or deploy to production.

#### Acceptance Criteria

1. THE System SHALL provide a docker-compose configuration for local development including FastAPI service, PostgreSQL database, and vector database container.

2. THE System SHALL document required environment variables including MODEL_NAME, EMBEDDING_MODEL, VECTOR_DB_TYPE, DATABASE_URL, and API_PORT.

3. THE System SHALL provide a README with step-by-step instructions to run locally including dependency installation, database initialization, recipe indexing, and service startup.

4. THE System SHALL include a health check endpoint at GET /health returning service status and dependency availability.

5. THE System SHALL log all requests, errors, and validation failures with appropriate log levels for debugging and monitoring.
