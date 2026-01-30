@echo off
cd /d "%~dp0"

echo Starting Fupo backend and frontend...
echo.

start "Fupo Backend" cmd /k python run_backend.py
timeout /t 2 /nobreak >nul
start "Fupo Frontend" cmd /k "cd frontend && npm run tauri dev"

echo Backend and frontend started in separate windows. Close those windows to stop the servers.
