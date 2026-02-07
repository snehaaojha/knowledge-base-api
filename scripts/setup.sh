#!/bin/bash
cd "$(dirname "$0")/.."
set -e
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
echo "Installing dependencies..."
pip install -r requirements.txt
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "IMPORTANT: Edit .env and set ENDEE_TOKEN for full API functionality."
    echo "Tests run without a token (they use mocks)."
else
    echo ".env already exists."
fi
echo ""
echo "Setup complete. Next steps:"
echo "  source venv/bin/activate"
echo "  ./scripts/test.sh    - Run tests (no token needed)"
echo "  ./scripts/run.sh     - Start the API (requires ENDEE_TOKEN in .env)"
