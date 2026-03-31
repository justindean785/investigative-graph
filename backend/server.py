"""
server.py — Compatibility shim.

The application entry point historically used by:
  - uvicorn server:app  (Dockerfile CMD, AGENTS.md, conftest.py)
  - All existing scripts and CI workflows

All application code now lives in main.py and the core/ + routers/ packages.
This file simply re-exports `app` so the existing startup commands continue
to work without modification.

DO NOT add any logic here. Import only.
"""

from main import app  # noqa: F401
