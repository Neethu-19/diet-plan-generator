# Quick Start Guide

## You're Almost Ready! 🎉

The dependencies are installed and recipes are being indexed. Here's what to do next:

### Step 1: Wait for Recipe Indexing to Complete
The indexing script is currently running. Wait for it to show:
```
Successfully indexed 8 recipes
Index saved to ./data/vector_db
```

### Step 2: Start the API Server
Once indexing is done, run:
```bash
run.bat
```

Or manually:
```bash
python -m uvicorn src.main:app --reload --port 8000
```

**⚠️ IMPORTANT**: First startup will take 5-10 minutes as it downloads the phi2 model (~5GB).

You'll see messages like:
- "Loading embedding model..."
- "Loading LLM model (this may take several minutes)..."
- Wait for "All services initialized successfully"

### Step 3: Open the Frontend
Once the API is running, open a new terminal and run:
```bash
cd frontend
python -m http.server 3000
```

Then open your browser to: **http://localhost:3000**

### Step 4: Generate Your First Meal Plan!
1. Fill in the form with your details
2. Click "Generate My Meal Plan"
3. Wait 30-60 seconds for generation
4. View your personalized meal plan!

## Troubleshooting

**"Module not found" errors**: Make sure you're in the project root directory

**"No recipes found"**: The indexing script needs to complete first

**API won't start**: Check if port 8000 is already in use

**Model loading fails**: Ensure you have 8GB+ RAM available

## What's Happening Behind the Scenes?

1. **Nutrition Engine**: Calculates your BMR, TDEE, and macro targets
2. **RAG Retrieval**: Finds recipes matching your needs using hybrid scoring
3. **phi2 LLM**: Generates natural language meal plan
4. **Validator**: Ensures all nutrition numbers are accurate (no hallucination!)

## Need Help?

Check the logs in the terminal where you ran `run.bat` for detailed information about what's happening.

Enjoy your personalized meal plans! 🥗
