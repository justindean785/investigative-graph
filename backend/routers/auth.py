"""
routers/auth.py — Authentication and health check endpoints.

Routes:
  GET  /api/           — health check / root
  POST /api/auth/validate — validate API key
"""

import hmac
from typing import Optional

from core.config import API_KEY
from core.security import validate_api_key
from fastapi import APIRouter, Header, HTTPException

router = APIRouter(prefix="/api", tags=["auth"])


@router.get("/")
async def root(x_api_key: str = Header(None)):
    await validate_api_key(x_api_key)
    return {"message": "Trace Analyst API v1.0", "status": "operational"}


@router.post("/auth/validate")
async def validate_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key and hmac.compare_digest(x_api_key, API_KEY):
        return {"valid": True, "message": "API key is valid"}
    raise HTTPException(status_code=401, detail="Invalid API key")
