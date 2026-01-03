@echo off
echo ===================================================
echo Starting iDecor Chatbot Server...
echo ===================================================
echo.
echo Installing requirements if needed...
pip install -r requirements.txt > nul 2>&1
echo.
echo Server is starting...
echo Once you see "Running on http://127.0.0.1:5000",
echo Open your browser and go to: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server.
echo ===================================================
python whatsapp_bot.py
pause
