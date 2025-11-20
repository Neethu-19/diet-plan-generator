@echo off
echo ========================================
echo Pushing Code to GitHub
echo ========================================
echo.

echo Step 1: Initializing Git Repository...
git init
echo.

echo Step 2: Adding Remote Repository...
git remote add origin https://github.com/Neethu-19/diet-plan-generator.git
echo.

echo Step 3: Staging All Files...
git add .
echo.

echo Step 4: Creating Commit...
git commit -m "Initial commit: Complete AI-Powered Diet Planning System with RAG, LLM enhancements, and interactive visualizations"
echo.

echo Step 5: Setting Main Branch...
git branch -M main
echo.

echo Step 6: Pushing to GitHub...
git push -u origin main
echo.

echo ========================================
echo Done! Check your repository at:
echo https://github.com/Neethu-19/diet-plan-generator
echo ========================================
pause
