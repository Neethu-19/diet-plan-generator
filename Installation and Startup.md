##  Installation

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd diet-planner
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

This will install all required packages (~2GB download).

### Step 4: Set Up Database

```bash
# Run database migrations
alembic upgrade head
```

This creates the SQLite database with all necessary tables.

### Step 5: Index Recipe Database

```bash
# Index sample recipes into vector database
python scripts/index_recipes.py data/sample_recipes.json
```

This takes ~30 seconds and creates the ChromaDB collection.

### Step 6: Verify Installation

```bash
# Test that everything is installed correctly
python -c "from src.core.nutrition_engine import NutritionEngine; print('Installation successful!')"
```

---

##  Quick Start

### Start the System

**Terminal 1: Backend API**
ython -m uvicorn src.main:app --reload --port 8000
```

**Terminal 2: Frontend Server**
```bash
cd frontend
python -m http.server 3000
```

### Access the Application

- **Frontend**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health