#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not on PATH. Install Docker Desktop / Engine, or use MongoDB Atlas (see backend/.env.example)."
  exit 1
fi
docker compose -f docker-compose.mongodb.yml up -d
echo "MongoDB listening on mongodb://localhost:27017"
echo "Stop with: docker compose -f docker-compose.mongodb.yml down"
