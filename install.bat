@echo off
echo Installing IncidentX dependencies...
echo.
pip install -r requirements.txt
echo.
echo Installation complete!
echo.
echo Next step: Create your .env file with your Gemini API key:
echo   GEMINI_API_KEY=your_api_key_here
echo.
echo Then run: start.bat
pause
