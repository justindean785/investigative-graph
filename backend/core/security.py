"""
core/security.py — API key validation.

Logic preserved verbatim from server.py; only the import path changed.
"""

import hmac
from typing import Optional

from fastapi import Header, HTTPException

from core.config import API_KEY


async def validate_api_key(x_api_key: Optional[str] = Header(None)):
    """Validate the x-api-key header using constant-time HMAC comparison."""
    if not x_api_key or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True
