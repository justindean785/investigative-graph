"""
routers/osint.py — OSINT search endpoint and provider integrations.

Routes:
  POST /api/osint/search — query GHOSINT, BOSINT, and Swatted in parallel

Also exports:
  osint_search_for_engine(query, search_type) -> dict
    Used by main.py to wire the investigation engine to the same
    OSINT providers without creating a circular import.

Provider functions are module-private (_search_*) and are only called
from inside this file or via the exported engine wrapper.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from core.config import (
    BOSINT_API_KEY,
    GHOSINT_API_KEY,
    SWATTED_API_TOKEN,
)
from core.deps import enforce_rate_limit
from core.security import validate_api_key
from fastapi import APIRouter, Header
from models import OSINTSearchRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["osint"])

# ---------------------------------------------------------------------------
# Mock fallback data (used when no OSINT provider keys are configured)
# ---------------------------------------------------------------------------

MOCK_OSINT_DATA: Dict[str, List[Dict[str, Any]]] = {
    "email": [
        {"source": "breach_db", "data": "Found in 3 data breaches", "risk": 0.7},
        {"source": "domain_whois", "data": "Registered 5 domains", "risk": 0.4},
    ],
    "username": [
        {
            "source": "social_media",
            "data": "Active on Twitter, GitHub, Reddit",
            "risk": 0.2,
        },
        {"source": "forum_posts", "data": "12 posts on security forums", "risk": 0.3},
    ],
    "domain": [
        {
            "source": "whois",
            "data": "Registered 2 years ago, Privacy protected",
            "risk": 0.5,
        },
        {"source": "dns", "data": "Resolves to 185.199.108.153", "risk": 0.3},
    ],
    "ip": [
        {
            "source": "geolocation",
            "data": "Located in US-East, AWS infrastructure",
            "risk": 0.2,
        },
        {
            "source": "reputation",
            "data": "Clean reputation, no malicious activity",
            "risk": 0.1,
        },
    ],
    "phone": [
        {"source": "carrier_lookup", "data": "T-Mobile USA, Active", "risk": 0.3},
        {"source": "breach_db", "data": "Found in 1 data breach", "risk": 0.6},
    ],
    "wallet": [
        {
            "source": "blockchain",
            "data": "42 transactions, $12.5K total volume",
            "risk": 0.4,
        },
        {"source": "mixer_check", "data": "No mixer usage detected", "risk": 0.2},
    ],
}

# ---------------------------------------------------------------------------
# BOSINT provider
# ---------------------------------------------------------------------------

_BOSINT_COMMANDS: Dict[str, List[str]] = {
    "email": ["email", "darkweb"],
    "username": ["username", "darkweb"],
    "phone": ["phone"],
    "domain": ["domain"],
    "ip": ["ip"],
    "wallet": ["darkweb"],
}


async def _search_bosint_command(
    api_key: str, command: str, query: str
) -> Optional[Dict[str, Any]]:
    """Call a single BOSINT command.  Returns a result dict or None."""
    try:
        url = f"https://app.bosint.gg/bosintapi/{api_key}/{command}/{query}"
        timeout = 90.0 if command == "username" else 30.0
        async with httpx.AsyncClient(timeout=timeout) as c:
            resp = await c.get(url)
        if resp.status_code in (401, 403, 429):
            logger.debug("BOSINT %s: %s", command, resp.status_code)
            return None
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            logger.debug("BOSINT %s: %s", command, data.get("error", "unknown error"))
            return None
        return {
            "source": f"bosint/{command}",
            "data": data.get("data", data),
            "risk": 0.5,
        }
    except Exception as exc:
        logger.debug("BOSINT %s failed: %s", command, exc)
        return None


async def _search_bosint(query: str, search_type: str) -> List[Dict[str, Any]]:
    """Query relevant BOSINT commands in parallel for the given search type."""
    if not BOSINT_API_KEY:
        return []
    commands = _BOSINT_COMMANDS.get(search_type, [])
    if not commands:
        return []
    tasks = [_search_bosint_command(BOSINT_API_KEY, cmd, query) for cmd in commands]
    raw = await asyncio.gather(*tasks)
    return [r for r in raw if r is not None]


# ---------------------------------------------------------------------------
# GHOSINT provider
# ---------------------------------------------------------------------------


async def _search_ghosint(query: str, search_type: str) -> List[Dict[str, Any]]:
    """Query GHOSINT and return a list of result dicts."""
    if not GHOSINT_API_KEY:
        return []

    free_services = ["leakcheck", "snusbase", "breachvip"]
    paid_services = ["ghosint.search", "leakosint"]

    if search_type in ("url", "wallet"):
        services = list(paid_services)
    elif search_type == "phone":
        services = free_services + ["seon"]
    else:
        services = list(free_services)

    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            resp = await c.post(
                "https://api.ghosint.io/search",
                json={"key": GHOSINT_API_KEY, "query": query, "services": services},
            )
            resp.raise_for_status()
            data = resp.json()

        if not data.get("success"):
            return []

        results: List[Dict[str, Any]] = []
        for svc_name, svc_data in data.get("response", {}).items():
            if isinstance(svc_data, dict) and svc_data.get("error"):
                continue
            results.append(
                {"source": f"ghosint/{svc_name}", "data": svc_data, "risk": 0.5}
            )
        return results

    except Exception as exc:
        logger.warning("GHOSINT search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Swatted provider
# ---------------------------------------------------------------------------

# Module-level session cache: (creds_dict, cookies_dict) or None
_swatted_session: Optional[tuple] = None

# Swatted modules per search type: (method, path, body_builder, label)
_SWATTED_MODULES: Dict[str, List[tuple]] = {
    "email": [
        ("POST", "/api/leakosint/search", lambda q: {"query": q}, "leakosint"),
        ("POST", "/api/snusbase/search", lambda q: {"query": q}, "snusbase"),
        ("POST", "/api/leakcheck/v2", lambda q: {"query": q}, "leakcheck"),
        ("POST", "/api/breachint/search", lambda q: {"query": q}, "breachint"),
        (
            "POST",
            "/api/stealerlogs/search",
            lambda q: {"query": q, "type": "email"},
            "stealerlogs",
        ),
    ],
    "username": [
        ("POST", "/api/leakosint/search", lambda q: {"query": q}, "leakosint"),
        ("POST", "/api/snusbase/search", lambda q: {"query": q}, "snusbase"),
        ("GET", "/api/tiktok_lookup", lambda q: q, "tiktok"),
        ("GET", "/api/instagram_lookup", lambda q: q, "instagram"),
    ],
    "phone": [
        ("POST", "/api/leakosint/search", lambda q: {"query": q}, "leakosint"),
        ("POST", "/api/snusbase/search", lambda q: {"query": q}, "snusbase"),
    ],
    "domain": [
        ("POST", "/api/shodan/dns", lambda q: {"domain": q}, "shodan_dns"),
        ("POST", "/api/infodra", lambda q: {"query": q}, "infodra"),
    ],
    "ip": [
        ("POST", "/api/shodan/host", lambda q: {"ip": q}, "shodan"),
        (
            "POST",
            "/api/stealerlogs/iplookup",
            lambda q: {"query": q},
            "stealerlogs_ip",
        ),
    ],
    "wallet": [
        ("POST", "/api/crypto", lambda q: {"query": q}, "crypto"),
    ],
}


def _swatted_headers(creds: Dict, with_csrf: bool = False) -> Dict[str, str]:
    h: Dict[str, str] = {
        "Authorization": f"Bearer {creds['session']}",
        "X-User-ID": creds["user_id"],
    }
    if with_csrf:
        h["X-CSRF-Token"] = creds["csrf"]
        h["Content-Type"] = "application/json"
    return h


async def _get_swatted_session() -> Optional[tuple]:
    """Exchange the account token for session credentials + cookies (cached)."""
    global _swatted_session

    if _swatted_session:
        return _swatted_session
    if not SWATTED_API_TOKEN:
        return None

    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(
            "https://swattedw.tf/api/login_token_api",
            json={"api_key": SWATTED_API_TOKEN},
        )
        r.raise_for_status()
        data = r.json()

    if "sessionToken" not in data:
        logger.error("Swatted login failed: %s", data)
        return None

    creds = {
        "session": data["sessionToken"],
        "user_id": data["userID"],
        "csrf": data["csrfToken"],
    }
    cookies = {
        "sessionToken": data["sessionToken"],
        "userID": data["userID"],
        "csrfToken": data["csrfToken"],
    }
    _swatted_session = (creds, cookies)
    logger.info("Swatted session credentials acquired")
    return _swatted_session


async def _search_swatted_module(
    creds: Dict,
    cookies: Dict,
    method: str,
    path: str,
    body_fn: Any,
    query: str,
    label: str,
) -> Optional[Dict[str, Any]]:
    """Call a single Swatted module.  Returns a result dict or None."""
    try:
        async with httpx.AsyncClient(timeout=25.0, cookies=cookies) as c:
            if method == "POST":
                resp = await c.post(
                    f"https://swattedw.tf{path}",
                    json=body_fn(query),
                    headers=_swatted_headers(creds, with_csrf=True),
                )
            else:
                resp = await c.get(
                    f"https://swattedw.tf{path}",
                    params={"username": query}
                    if "lookup" in path
                    else {"query": query},
                    headers=_swatted_headers(creds),
                )
        if resp.status_code in (401, 403):
            logger.debug("Swatted %s: %s %s", label, resp.status_code, resp.text[:200])
            return None
        resp.raise_for_status()
        data = resp.json()
        return {"source": f"swatted/{label}", "data": data, "risk": 0.5}
    except Exception as exc:
        logger.debug("Swatted %s failed: %s", label, exc)
        return None


async def _search_swatted(query: str, search_type: str) -> List[Dict[str, Any]]:
    """Query all relevant Swatted modules in parallel for the given search type."""
    global _swatted_session

    session = await _get_swatted_session()
    if not session:
        return []

    creds, cookies = session
    modules = _SWATTED_MODULES.get(search_type, [])
    if not modules:
        return []

    tasks = [
        _search_swatted_module(creds, cookies, method, path, body_fn, query, label)
        for method, path, body_fn, label in modules
    ]
    raw = await asyncio.gather(*tasks)
    results = [r for r in raw if r is not None]

    if not results and raw:
        # All modules failed — clear cached session to force re-auth next time
        _swatted_session = None
        logger.warning("Swatted: all modules failed, clearing session for re-auth")

    return results


# ---------------------------------------------------------------------------
# Engine-facing search wrapper (exported for main.py wiring)
# ---------------------------------------------------------------------------


async def osint_search_for_engine(query: str, search_type: str) -> Dict[str, Any]:
    """
    Run all three OSINT providers in parallel and return a unified dict.

    This function is imported by main.py and passed to InvestigationEngine
    so the engine can trigger OSINT queries without importing from a router.
    """
    tasks = [
        asyncio.create_task(_search_ghosint(query, search_type)),
        asyncio.create_task(_search_swatted(query, search_type)),
        asyncio.create_task(_search_bosint(query, search_type)),
    ]
    all_results = await asyncio.gather(*tasks)

    results: List[Dict[str, Any]] = []
    for batch in all_results:
        results.extend(batch)

    return {
        "query": query,
        "search_type": search_type,
        "results": results,
        "live_data": True,
    }


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("/osint/search")
async def osint_search(
    input: OSINTSearchRequest,
    x_api_key: str = Header(None),
):
    """
    Search OSINT providers for a given query and search type.

    Falls back to mock data when no provider API keys are configured.
    """
    await validate_api_key(x_api_key)
    enforce_rate_limit(x_api_key, "osint")

    if not GHOSINT_API_KEY and not SWATTED_API_TOKEN and not BOSINT_API_KEY:
        results = MOCK_OSINT_DATA.get(
            input.search_type,
            [
                {
                    "source": "general",
                    "data": f"Mock data for {input.query}",
                    "risk": 0.3,
                }
            ],
        )
        return {
            "query": input.query,
            "search_type": input.search_type,
            "results": results,
            "live_data": False,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    tasks = [
        asyncio.create_task(_search_ghosint(input.query, input.search_type)),
        asyncio.create_task(_search_swatted(input.query, input.search_type)),
        asyncio.create_task(_search_bosint(input.query, input.search_type)),
    ]
    all_results = await asyncio.gather(*tasks)

    results: List[Dict[str, Any]] = []
    for batch in all_results:
        results.extend(batch)

    return {
        "query": input.query,
        "search_type": input.search_type,
        "results": results,
        "live_data": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
