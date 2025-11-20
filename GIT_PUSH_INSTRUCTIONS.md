# 🚀 Push Code to GitHub

## Step-by-Step Instructions

### Step 1: Initialize Git Repository (if not already done)

```bash
# Navigate to your project directory
cd C:\Users\neeth\OneDrive\Desktop\diet

# Initialize git (skip if already initialized)
git init
```

### Step 2: Create .gitignore File

Before committing, create a `.gitignore` file to exclude unnecessary files:

```bash
# Create .gitignore
echo "# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# Database
*.db
*.sqlite
*.sqlite3
diet_planner.db

# Vector Database
chroma_db/
.chroma/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.bak
*~

# Model cache
.cache/
models/

# Test files
test_*.py
*_test.py" > .gitignore
```

### Step 3: Add Remote Repository

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/Neethu-19/diet-plan-generator.git

# Verify remote was added
git remote -v
```

### Step 4: Stage All Files

```bash
# Add all files to staging
git add .

# Check what will be committed
git status
```

### Step 5: Create Initial Commit

```bash
# Commit with a descriptive message
git commit -m "Initial commit: AI-Powered Personalized Diet Planning System

Features:
- Daily and weekly meal planning
- Advanced RAG with 6-factor scoring
- LLM enhancements with 5 audience modes
- Progress tracking and adaptive adjustments
- Preference learning and feedback system
- Interactive charts and visualizations
- Clean, professional UI design
- Complete API with 15+ endpoints
- Comprehensive documentation"
```

### Step 6: Push to GitHub

```bash
# Push to main branch
git branch -M main
git push -u origin main
```

If you get an error about the branch already existing:

```bash
# Force push (use with caution)
git push -u origin main --force
```

---

## Alternative: If Repository Already Has Content

If the GitHub repository already has files, you'll need to pull first:

```bash
# Pull existing content
git pull origin main --allow-unrelated-histories

# Resolve any conflicts if they occur
# Then commit and push
git add .
git commit -m "Merge with existing repository"
git push origin main
```

---

## Quick Commands (Copy-Paste)

```bash
# Complete sequence
cd C:\Users\neeth\OneDrive\Desktop\diet
git init
git remote add origin https://github.com/Neethu-19/diet-plan-generator.git
git add .
git commit -m "Initial commit: Complete AI-Powered Diet Planning System"
git branch -M main
git push -u origin main
```

---

## Verify Upload

After pushing, verify on GitHub:

1. Go to https://github.com/Neethu-19/diet-plan-generator
2. Check that all files are present
3. Verify README.md displays correctly
4. Check that .gitignore is working (no __pycache__, .db files)

---

## Update Repository Later

When you make changes:

```bash
# Stage changes
git add .

# Commit with message
git commit -m "Description of changes"

# Push to GitHub
git push origin main
```

---

## Common Issues

### Issue 1: Authentication Required

**Solution**: Use Personal Access Token

1. Go to GitHub Settings → Developer Settings → Personal Access Tokens
2. Generate new token with 'repo' permissions
3. Use token as password when prompted

### Issue 2: Repository Not Empty

**Error**: `! [rejected] main -> main (fetch first)`

**Solution**:
```bash
git pull origin main --allow-unrelated-histories
git push origin main
```

### Issue 3: Large Files

**Error**: `file size exceeds GitHub's limit`

**Solution**: Add to .gitignore and remove from staging
```bash
git rm --cached <large-file>
echo "<large-file>" >> .gitignore
git commit -m "Remove large file"
```

---

## Files to Verify Are Included

✅ Should be in repository:
- src/ (all Python code)
- frontend/ (all HTML/JS files)
- alembic/ (database migrations)
- data/sample_recipes.json
- requirements.txt
- README.md
- All documentation files

❌ Should NOT be in repository:
- __pycache__/
- *.db files
- chroma_db/
- venv/
- .env
- *.log files

---

## Repository Structure on GitHub

After pushing, your repository should look like:

```
diet-plan-generator/
├── .gitignore
├── README.md
├── requirements.txt
├── alembic.ini
├── src/
├── frontend/
├── alembic/
├── data/
├── scripts/
└── docs/
```

---

## Next Steps After Pushing

1. ✅ Add repository description on GitHub
2. ✅ Add topics/tags (python, fastapi, ai, nutrition, meal-planning)
3. ✅ Enable GitHub Pages (for frontend demo)
4. ✅ Add LICENSE file
5. ✅ Create releases/tags
6. ✅ Set up GitHub Actions (optional)

---

## GitHub Repository Settings

### Recommended Settings:

**Description**:
```
AI-Powered Personalized Diet Planning System with explainable recommendations, preference learning, and adaptive progress tracking
```

**Topics**:
```
python, fastapi, ai, machine-learning, nutrition, meal-planning, 
diet, health, rag, llm, personalization, charts, visualization
```

**Website**:
```
https://neethu-19.github.io/diet-plan-generator
```

---

## Enable GitHub Pages (Optional)

To host your frontend on GitHub Pages:

1. Go to repository Settings
2. Navigate to Pages
3. Source: Deploy from branch
4. Branch: main
5. Folder: /frontend
6. Save

Your frontend will be available at:
```
https://neethu-19.github.io/diet-plan-generator
```

---

## Create Release

After pushing, create a release:

1. Go to Releases
2. Click "Create a new release"
3. Tag: v1.0.0
4. Title: "Initial Release - Complete Diet Planning System"
5. Description: Copy from README features section
6. Publish release

---

## Summary

Run these commands in order:

```bash
cd C:\Users\neeth\OneDrive\Desktop\diet
git init
git remote add origin https://github.com/Neethu-19/diet-plan-generator.git
git add .
git commit -m "Initial commit: Complete AI-Powered Diet Planning System"
git branch -M main
git push -u origin main
```

Then verify at: https://github.com/Neethu-19/diet-plan-generator

**Your code will be live on GitHub!** 🎉
