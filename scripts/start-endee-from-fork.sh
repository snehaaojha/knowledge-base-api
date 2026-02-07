#!/bin/bash
# Run Endee from your fork (Criterion 2: Fork & Use)
# Builds and runs Endee from https://github.com/snehaaojha/endee_t1
set -e
cd "$(dirname "$0")/.."
FORK_DIR="endee_fork"
FORK_URL="https://github.com/snehaaojha/endee_t1.git"

if [ ! -d "$FORK_DIR" ]; then
    echo "Cloning Endee fork..."
    git clone "$FORK_URL" "$FORK_DIR"
fi
cd "$FORK_DIR"

echo "Building Endee image from fork..."
docker build --ulimit nofile=100000:100000 --build-arg BUILD_ARCH=avx2 -t endee-oss:latest -f ./infra/Dockerfile .

echo "Starting Endee on port 8080..."
docker run -d -p 8080:8080 -v endee-data:/data -e NDD_AUTH_TOKEN= --name endee-server endee-oss:latest 2>/dev/null || docker start endee-server

echo "Endee is running. Set in .env: ENDEE_BASE_URL=http://localhost:8080/api/v1"
