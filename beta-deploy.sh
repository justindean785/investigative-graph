#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
docker compose -f docker-compose.beta.yml up --build -d
echo ""
echo "Trace Analyst beta stack is up."
echo "  App:  http://localhost:3000"
echo "  API:  http://localhost:8001/api/ (or via nginx at http://localhost:3000/api/)"
echo ""
echo "Stop:  docker compose -f docker-compose.beta.yml down"
