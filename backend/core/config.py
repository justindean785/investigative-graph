"""
core/config.py — Application configuration.

All environment variables are read here once at import time.
Routers and helpers import individual names from this module.

Startup validation (MONGO_URL, DB_NAME) is intentionally kept here
so the error surface is a single place — fail fast before any DB call.
"""

import os
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

# Load .env from the backend/ root (parent of core/)
_ROOT_DIR = Path(__file__).parent.parent
load_dotenv(_ROOT_DIR / ".env")

# ---------------------------------------------------------------------------
# MongoDB — required; raise immediately if missing
# ---------------------------------------------------------------------------

MONGO_URL: str = os.environ.get("MONGO_URL", "").strip()
if not MONGO_URL:
    raise RuntimeError(
        "MONGO_URL is not set. Copy backend/.env.example to backend/.env and "
        "set MONGO_URL (e.g. mongodb://127.0.0.1:27017 for local Mongo or your "
        "Atlas connection string)."
    )

DB_NAME: str = os.environ.get("DB_NAME", "").strip()
if not DB_NAME:
    raise RuntimeError(
        "DB_NAME is not set. Set DB_NAME in backend/.env (e.g. trace_analyst)."
    )

# ---------------------------------------------------------------------------
# API security
# ---------------------------------------------------------------------------

# Default preserved for local dev / test-suite compatibility.
# Production deployments MUST override via environment variable.
API_KEY: str = os.environ.get("API_KEY", "trace-analyst-secret-2026")

# ---------------------------------------------------------------------------
# AI providers
# ---------------------------------------------------------------------------

GEMINI_API_KEY: Optional[str] = os.environ.get("GEMINI_API_KEY")

# Model names can be overridden in .env if Google renames them.
GEMINI_MODEL_FLASH: str = os.environ.get("GEMINI_MODEL_FLASH", "gemini-2.0-flash")
GEMINI_MODEL_PRO: str = os.environ.get("GEMINI_MODEL_PRO", "gemini-1.5-pro")
GEMINI_MODEL_CHAT: str = os.environ.get("GEMINI_MODEL_CHAT", GEMINI_MODEL_FLASH)

GROK_API_KEY: Optional[str] = os.environ.get("GROK_API_KEY")

# ---------------------------------------------------------------------------
# OSINT providers
# ---------------------------------------------------------------------------

GHOSINT_API_KEY: Optional[str] = os.environ.get("GHOSINT_API_KEY")
BOSINT_API_KEY: Optional[str] = os.environ.get("BOSINT_API_KEY")
SWATTED_API_TOKEN: Optional[str] = os.environ.get("SWATTED_API_TOKEN")

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ORIGINS: List[str] = os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(
    ","
)
