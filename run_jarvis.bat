@echo off
title JARVIS AI Assistant
echo Starting JARVIS with Python 3.12...
"C:\Users\CHAMA COMPUTERS\AppData\Local\Programs\Python\Python312\python.exe" main.py
if errorlevel 1 (
    echo.
    echo An error occurred while running JARVIS.
    pause
)
