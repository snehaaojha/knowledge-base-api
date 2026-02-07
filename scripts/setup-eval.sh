#!/bin/bash
cd "$(dirname "$0")/.."
set -e
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "Installing minimal deps for tests (no sentence-transformers)..."
pip install -r requirements-eval.txt
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
else
    echo ".env already exists."
fi
echo ""
echo "Evaluator setup complete. Run: ./scripts/test.sh"
