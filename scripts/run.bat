@echo off
cd /d "%~dp0.."
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
)
if exist venv\Scripts\python.exe (venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000) else (python -m uvicorn app.main:app --host 0.0.0.0 --port 8000)
