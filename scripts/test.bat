@echo off
cd /d "%~dp0.."
if exist venv\Scripts\python.exe (venv\Scripts\python.exe -m pytest -v) else (python -m pytest -v)
