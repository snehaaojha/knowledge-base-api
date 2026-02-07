#!/bin/bash
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi
PYTHON=python
[ -f venv/bin/python ] && PYTHON=venv/bin/python
exec $PYTHON -m uvicorn app.main:app --host 0.0.0.0 --port 8000
