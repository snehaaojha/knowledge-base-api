@echo off
cd /d "%~dp0.."
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo Installing minimal deps for tests (no sentence-transformers)...
pip install -r requirements-eval.txt
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
) else (
    echo .env already exists.
)
echo.
echo Evaluator setup complete. Run: scripts\test.bat
