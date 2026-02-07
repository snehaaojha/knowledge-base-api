@echo off
cd /d "%~dp0.."
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
)
docker-compose up --build
