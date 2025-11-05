@echo off
ECHO Running the Daily News Recap script...

:: --- IMPORTANT ---
:: Change this first path to your project's virtual environment
CALL "C:\Users\Jonah\OneDrive\Desktop\School Files\2025 - Fall\Business Applications Develop\Projects\Quarterly-Assessment-3\python venv\Scripts\activate.bat"

:: This next line automatically changes to the script's directory
:: This is so it can find the .py file and your .env file
cd /d "%~dp0"

ECHO Starting Python script (this window will close when done)...

:: We use pythonw.exe (instead of python.exe) to run the script
:: "silently" without a black command window popping up.
pythonw.exe news-recap-and-email.py
ECHO Script finished.
exit