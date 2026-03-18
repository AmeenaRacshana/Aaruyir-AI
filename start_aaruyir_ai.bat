@echo off
echo Starting Aaruyir AI...

:: Start the Flask app in the background
start /B py app.py

:: Wait for a few seconds to let the server start
timeout /t 3 /nobreak >nul

:: Open the website in the default browser
echo Opening the website...
start http://localhost:5000

echo Aaruyir AI is running! Close this window to stop it.
:: Keep the window open so they can see logs or close it to kill the server
pause
