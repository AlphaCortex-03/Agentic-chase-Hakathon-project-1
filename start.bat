@echo off
echo ============================================================
echo   IncidentX — Autonomous IT Incident Response Agent
echo   Agentic Chase Hackathon PS 01
echo ============================================================
echo.

REM Check if .env exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo.
    echo Please create a .env file with your Gemini API key:
    echo   GEMINI_API_KEY=your_api_key_here
    echo.
    echo Get a free key at: https://aistudio.google.com/app/apikey
    echo.
    pause
    exit /b 1
)

echo Starting IncidentX Dashboard...
echo Open your browser at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server.
echo.
streamlit run app.py --server.port 8501 --server.headless false
pause
