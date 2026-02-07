#!/bin/bash
cd "$(dirname "$0")/.."
[ ! -f .env ] && echo "Creating .env from .env.example..." && cp .env.example .env
docker-compose up --build
