# 🚀 Quick Reference Guide

## System URLs

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Quick Commands

### Start Everything (After First Setup)
```bash
# Terminal 1 - API Server
python -m uvicorn src.main:app --reload --port 8000

# Terminal 2 - Frontend Server
cd frontend
python -m http.server 3000
```

### Check System Health
```bash
curl http://localhost:8000/health
```

### Generate a Meal Plan (API)
```bash
curl -X POST http://localhost:8000/generate-plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "age": 30,
    "sex": "male",
    "weight_kg": 75,
    "height_cm": 175,
    "activity_level": "moderate",
    "goal": "maintain",
    "goal_rate_kg_per_week": 0,
    "dietary_preferences": ["omnivore"],
    "allergens": [],
    "wake_time": "07:00",
    "lunch_time": "12:00",
    "dinner_time": "19:00"
  }'
```

### Run Integration Tests
```bash
python scripts/test_integration.py
```

### Re-index Recipes (If You Add More)
```bash
python scripts/index_recipes.py data/sample_recipes.json
```

## Configuration Quick Tweaks

### Change LLM Temperature (in .env)
```
LLM_TEMPERATURE=0.1  # More deterministic (current)
LLM_TEMPERATURE=0.3  # More creative
```

### Change RAG Scoring Weights (in .env)
```
SEMANTIC_WEIGHT=0.6        # How much semantic similarity matters
KCAL_PROXIMITY_WEIGHT=0.3  # How much calorie matching matters
TAG_WEIGHT=0.1             # How much dietary tags matter
```

### Change Number of Recipe Candidates (in .env)
```
TOP_K_CANDIDATES=3  # Default
TOP_K_CANDIDATES=5  # More options for LLM to choose from
```

## Common Issues & Fixes

### Issue: API Server Won't Start
**Fix**: Check if port 8000 is already in use
```bash
netstat -ano | findstr :8000
```

### Issue: Frontend Won't Load
**Fix**: Check if port 3000 is already in use
```bash
netstat -ano | findstr :3000
```

### Issue: Meal Plan Generation Fails
**Fix**: Check the API logs for errors
- Look for validation failures
- Check if recipes are indexed
- Verify model loaded successfully

### Issue: No Recipes Match Constraints
**Fix**: Add more recipes to the database
```bash
# Edit data/sample_recipes.json to add more recipes
python scripts/index_recipes.py data/sample_recipes.json
```

### Issue: Out of Memory
**Fix**: Reduce model size or use CPU offloading
- Current model (phi-2): ~3GB RAM
- Consider using a smaller model if needed

## Understanding the Output

### Meal Plan Structure
```json
{
  "plan_id": "unique_id",
  "user_id": "user_id",
  "date": "2025-11-15",
  "meals": [
    {
      "meal_type": "breakfast",
      "recipe_id": "recipe_001",
      "recipe_title": "Oatmeal with Berries",
      "portion_size": "1.2x",
      "nutrition": {
        "kcal_total": 450,
        "protein_g_total": 15,
        "carbs_g_total": 65,
        "fat_g_total": 12
      }
    }
  ],
  "total_nutrition": {
    "kcal_total": 2500,
    "protein_g_total": 150,
    "carbs_g_total": 280,
    "fat_g_total": 70
  },
  "nutrition_provenance": "verified"
}
```

### Nutrition Calculations

**BMR (Basal Metabolic Rate):**
- Male: 10 × weight(kg) + 6.25 × height(cm) - 5 × age + 5
- Female: 10 × weight(kg) + 6.25 × height(cm) - 5 × age - 161
- Other: 10 × weight(kg) + 6.25 × height(cm) - 5 × age - 78

**TDEE (Total Daily Energy Expenditure):**
- Sedentary: BMR × 1.2
- Light: BMR × 1.375
- Moderate: BMR × 1.55
- Active: BMR × 1.725
- Very Active: BMR × 1.9

**Target Calories:**
- Maintain: TDEE
- Lose: TDEE - (goal_rate × 7700 / 7)
- Gain: TDEE + (goal_rate × 7700 / 7)
- Minimum: 1200 kcal

**Macros:**
- Protein: max(1.6 × weight_kg, 0.20 × target_kcal / 4)
- Fat: 0.25 × target_kcal / 9
- Carbs: (target_kcal - protein×4 - fat×9) / 4

**Meal Split (default):**
- Breakfast: 25%
- Lunch: 35%
- Dinner: 30%
- Snacks: 10%

## Performance Tips

1. **First generation is slowest** (30-60s) - model needs to warm up
2. **Subsequent generations are faster** (20-40s)
3. **Meal swaps are fastest** (15-30s) - only regenerating one meal
4. **More recipes = better matches** - add more to data/sample_recipes.json
5. **Adjust TOP_K_CANDIDATES** - higher = more options but slower

## Adding More Recipes

Recipe format in `data/sample_recipes.json`:
```json
{
  "recipe_id": "recipe_009",
  "title": "Grilled Chicken Salad",
  "ingredients": ["chicken breast", "mixed greens", "olive oil", "lemon"],
  "instructions": "Grill chicken, toss with greens and dressing",
  "meal_type": "lunch",
  "cuisine": "mediterranean",
  "dietary_tags": ["high_protein", "low_carb"],
  "allergens": [],
  "nutrition": {
    "kcal_total": 350,
    "protein_g_total": 40,
    "carbs_g_total": 15,
    "fat_g_total": 18
  }
}
```

After adding recipes, re-index:
```bash
python scripts/index_recipes.py data/sample_recipes.json
```

## Monitoring & Debugging

### Check API Logs
Look at the terminal running the API server for:
- Request logs
- Validation errors
- Model inference times
- Provenance violations

### Check Frontend Console
Open browser DevTools (F12) to see:
- API request/response
- JavaScript errors
- Network timing

### Test Individual Components
```bash
# Test nutrition engine
python -c "from src.core.nutrition_engine import NutritionEngine; e = NutritionEngine(); print(e.calculate_targets(30, 'male', 75, 175, 'moderate', 'maintain', 0))"

# Test RAG module
python -c "from src.core.rag_module import RAGModule; r = RAGModule(); print(r.retrieve_candidates('breakfast', 500, ['omnivore'], []))"
```

## Next Steps

1. ✅ Wait for model download to complete
2. ✅ Open http://localhost:3000
3. ✅ Fill out your profile
4. ✅ Generate your first meal plan
5. ✅ Try swapping meals
6. ✅ Experiment with different profiles
7. ✅ Add more recipes if needed
8. ✅ Run integration tests

---

**Happy meal planning! 🍽️**
