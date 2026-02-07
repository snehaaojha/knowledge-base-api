@echo off
cd /d "%~dp0.."
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat
echo Installing dependencies...
pip install -r requirements.txt
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env and set ENDEE_TOKEN for full API functionality.
    echo Tests run without a token (they use mocks).
) else (
    echo .env already exists.
)
echo.
echo Setup complete. Next steps:
echo   scripts\test.bat    - Run tests (no token needed)
echo   scripts\run.bat     - Start the API (requires ENDEE_TOKEN in .env)
