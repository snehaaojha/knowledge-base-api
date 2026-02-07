#!/bin/bash
cd "$(dirname "$0")/.."
[ -f venv/bin/python ] && exec venv/bin/python -m pytest -v || exec python -m pytest -v
