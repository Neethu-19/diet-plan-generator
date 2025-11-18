@echo off
echo ========================================
echo Personalized Diet Plan Generator
echo ========================================
echo.
echo Starting API server...
echo This will take a few minutes on first run (downloading phi2 model)
echo.
python -m uvicorn src.main:app --reload --port 8000
