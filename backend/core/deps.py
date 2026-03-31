"""
core/deps.py — Shared application dependencies.

Contains:
  - MongoDB client and database handle
  - Investigation engine reference (get/set for lifespan-safe access)
  - In-memory SSE event queues
  - Rate limiter
  - serialize_datetime helper
  - create_timeline_event helper
  - MongoDB index creation
  - Text/file extraction utilities (shared by enrichment + ingest routers)
  - ENTITY_PATTERNS regex definitions

Nothing in this file imports from any router — it is purely a dependency
provider to keep the import graph acyclic.
"""

from __future__ import annotations

import asyncio
import collections
import ipaddress
import logging
import re
import socket
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from models import TimelineEvent
from motor.motor_asyncio import AsyncIOMotorClient

from core.config import DB_NAME, MONGO_URL

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional heavy-weight imports (OCR / PDF / HTML parsing)
# ---------------------------------------------------------------------------

try:
    import pytesseract
    from PIL import Image  # type: ignore[import]

    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from PyPDF2 import PdfReader  # type: ignore[import]

    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from bs4 import BeautifulSoup  # type: ignore[import]

    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# ---------------------------------------------------------------------------
# MongoDB
# ---------------------------------------------------------------------------

client: AsyncIOMotorClient = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# ---------------------------------------------------------------------------
# Investigation engine — set during lifespan, read from routers
# ---------------------------------------------------------------------------

_investigation_engine = None


def get_investigation_engine():
    """Return the current InvestigationEngine instance (may be None before startup)."""
    return _investigation_engine


def set_investigation_engine(engine) -> None:
    """Called once from main.py lifespan after the engine is initialised."""
    global _investigation_engine
    _investigation_engine = engine


# ---------------------------------------------------------------------------
# SSE event queues  {investigation_id -> [asyncio.Queue, ...]}
# ---------------------------------------------------------------------------

investigation_event_queues: Dict[str, list] = {}

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Simple in-memory token-bucket rate limiter keyed by client identifier."""

    def __init__(self) -> None:
        import time as _time

        self._time = _time
        self._buckets: Dict[str, Dict[str, Any]] = {}

    def check(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = self._time.monotonic()
        bucket = self._buckets.get(key)
        if bucket is None or now - bucket["window_start"] >= window_seconds:
            self._buckets[key] = {"window_start": now, "count": 1}
            return True
        if bucket["count"] >= max_requests:
            return False
        bucket["count"] += 1
        return True


_rate_limiter = _RateLimiter()

# Limits: AI = 30 req/min, OSINT = 20 req/min, general = 120 req/min
_RATE_LIMITS: Dict[str, tuple] = {
    "ai": (30, 60),
    "osint": (20, 60),
    "general": (120, 60),
}


def enforce_rate_limit(api_key: str, category: str = "general") -> None:
    """Raise HTTP 429 if the given api_key has exceeded the category limit."""
    max_req, window = _RATE_LIMITS.get(category, _RATE_LIMITS["general"])
    bucket_key = f"{api_key}:{category}"
    if not _rate_limiter.check(bucket_key, max_req, window):
        raise HTTPException(
            status_code=429,
            detail=(
                f"Rate limit exceeded ({max_req} requests per {window}s for {category})"
            ),
        )


# ---------------------------------------------------------------------------
# Datetime serialiser
# ---------------------------------------------------------------------------


def serialize_datetime(obj: Any) -> Any:
    """Recursively convert datetime objects to ISO-8601 strings."""
    if isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


# ---------------------------------------------------------------------------
# Timeline event helper
# ---------------------------------------------------------------------------


async def create_timeline_event(
    investigation_id: str,
    event_type: str,
    description: str,
    entity_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> TimelineEvent:
    """Insert a timeline event into MongoDB and return the model instance."""
    event = TimelineEvent(
        investigation_id=investigation_id,
        event_type=event_type,
        description=description,
        entity_id=entity_id,
        metadata=metadata or {},
    )
    doc = event.model_dump()
    doc["timestamp"] = doc["timestamp"].isoformat()
    await db.timeline_events.insert_one(doc)
    return event


# ---------------------------------------------------------------------------
# MongoDB index creation
# ---------------------------------------------------------------------------


async def create_mongodb_indexes() -> None:
    """Create MongoDB indexes for frequently-queried fields."""
    await db.investigations.create_index("id", unique=True)
    await db.entities.create_index("investigation_id")
    await db.entities.create_index([("id", 1), ("investigation_id", 1)])
    await db.relationships.create_index("investigation_id")
    await db.relationships.create_index([("id", 1), ("investigation_id", 1)])
    await db.timeline_events.create_index("investigation_id")
    await db.timeline_events.create_index([("investigation_id", 1), ("timestamp", -1)])
    await db.evidence.create_index("investigation_id")
    await db.evidence.create_index([("id", 1), ("investigation_id", 1)])
    await db.ai_suggestions.create_index([("investigation_id", 1), ("status", 1)])
    await db.investigation_leads.create_index("investigation_id")
    await db.investigation_leads.create_index([("id", 1), ("investigation_id", 1)])
    await db.chat_messages.create_index([("investigation_id", 1), ("session_id", 1)])
    logger.info("MongoDB indexes created")


# ---------------------------------------------------------------------------
# Entity extraction patterns (shared between enrichment + ingest routers)
# ---------------------------------------------------------------------------

ENTITY_PATTERNS: Dict[str, Any] = {
    "email": {
        "compiled": re.compile(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.IGNORECASE
        ),
        "label": "Email Address",
        "entity_type": "email",
        "risk_base": 0.3,
    },
    "domain": {
        "compiled": re.compile(
            r"(?<![/@])(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)"
            r"+(?:onion|com|net|org|io|co|info|biz|gov|edu|mil|int|xyz|online|site|tech|"
            r"dev|app|cloud|ru|cn|uk|de|fr|jp|br|in|au|nl|se|ch|es|it|pl|cz|ro|hu|bg|ua|kz|by)",
            re.IGNORECASE,
        ),
        "label": "Domain",
        "entity_type": "domain",
        "risk_base": 0.4,
    },
    "onion_domain": {
        "compiled": re.compile(r"[a-z2-7]{16,56}\.onion", re.IGNORECASE),
        "label": "Tor Hidden Service",
        "entity_type": "domain",
        "risk_base": 0.8,
    },
    "ip_v4": {
        "compiled": re.compile(
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}"
            r"(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
            re.IGNORECASE,
        ),
        "label": "IPv4 Address",
        "entity_type": "ip",
        "risk_base": 0.3,
    },
    "ip_v6": {
        "compiled": re.compile(
            r"(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}"
            r"|(?:[0-9a-fA-F]{1,4}:){1,7}:"
            r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}",
            re.IGNORECASE,
        ),
        "label": "IPv6 Address",
        "entity_type": "ip",
        "risk_base": 0.3,
    },
    "wallet_eth": {
        "compiled": re.compile(r"0x[a-fA-F0-9]{40}", re.IGNORECASE),
        "label": "Ethereum Wallet",
        "entity_type": "wallet",
        "risk_base": 0.5,
    },
    "wallet_btc": {
        "compiled": re.compile(r"(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}", re.IGNORECASE),
        "label": "Bitcoin Wallet",
        "entity_type": "wallet",
        "risk_base": 0.5,
    },
    "wallet_monero": {
        "compiled": re.compile(r"4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}", re.IGNORECASE),
        "label": "Monero Wallet",
        "entity_type": "wallet",
        "risk_base": 0.7,
    },
    "phone_intl": {
        "compiled": re.compile(r"\+[1-9]\d{1,14}", re.IGNORECASE),
        "label": "International Phone",
        "entity_type": "phone",
        "risk_base": 0.2,
    },
    "phone_us": {
        "compiled": re.compile(
            r"(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", re.IGNORECASE
        ),
        "label": "US Phone Number",
        "entity_type": "phone",
        "risk_base": 0.2,
    },
    "username_twitter": {
        "compiled": re.compile(
            r"(?:twitter\.com/|@)([A-Za-z0-9_]{1,15})", re.IGNORECASE
        ),
        "label": "Twitter Handle",
        "entity_type": "username",
        "risk_base": 0.1,
    },
    "username_telegram": {
        "compiled": re.compile(r"(?:t\.me/|@)([A-Za-z0-9_]{5,32})", re.IGNORECASE),
        "label": "Telegram Handle",
        "entity_type": "username",
        "risk_base": 0.2,
    },
    "username_generic": {
        "compiled": re.compile(r"@[A-Za-z0-9_]{3,30}", re.IGNORECASE),
        "label": "Username/Handle",
        "entity_type": "username",
        "risk_base": 0.1,
    },
    "url": {
        "compiled": re.compile(r'https?://[^\s<>"\'{}|\\^`\[\]]+', re.IGNORECASE),
        "label": "URL",
        "entity_type": "url",
        "risk_base": 0.2,
    },
    "social_profile": {
        "compiled": re.compile(
            r"(?:facebook\.com|instagram\.com|linkedin\.com|github\.com|reddit\.com)"
            r"/[A-Za-z0-9._-]+",
            re.IGNORECASE,
        ),
        "label": "Social Profile URL",
        "entity_type": "social",
        "risk_base": 0.1,
    },
    "hash_md5": {
        "compiled": re.compile(r"\b[a-fA-F0-9]{32}\b", re.IGNORECASE),
        "label": "MD5 Hash",
        "entity_type": "hash",
        "risk_base": 0.3,
    },
    "hash_sha256": {
        "compiled": re.compile(r"\b[a-fA-F0-9]{64}\b", re.IGNORECASE),
        "label": "SHA256 Hash",
        "entity_type": "hash",
        "risk_base": 0.3,
    },
}


def extract_entities_from_text(
    text: str,
    source_evidence_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Extract all entities/indicators from *text* using ENTITY_PATTERNS regex set."""
    extracted: List[Dict[str, Any]] = []
    seen_values: set = set()

    for pattern_name, config in ENTITY_PATTERNS.items():
        try:
            matches = config["compiled"].findall(text)
            for match in matches:
                # Groups produce tuples; take the first captured group.
                if isinstance(match, tuple):
                    match = match[0] if match else ""

                clean_value = match.strip()
                if not clean_value or len(clean_value) < 3:
                    continue

                # Skip common false positives
                if clean_value.lower() in {"www", "http", "https", "ftp", "mail"}:
                    continue

                dedup_key = f"{config['entity_type']}:{clean_value.lower()}"
                if dedup_key in seen_values:
                    continue
                seen_values.add(dedup_key)

                risk_score: float = config.get("risk_base", 0.3)
                if ".onion" in clean_value.lower():
                    risk_score = max(risk_score, 0.8)
                if pattern_name.startswith("wallet_"):
                    risk_score = max(risk_score, 0.5)

                extracted.append(
                    {
                        "type": config["entity_type"],
                        "pattern_match": pattern_name,
                        "value": clean_value,
                        "label": config["label"],
                        "confidence": 0.85,
                        "risk_score": risk_score,
                        "source_evidence_id": source_evidence_id,
                    }
                )
        except re.error as exc:
            logger.error("Regex error for pattern %s: %s", pattern_name, exc)
            continue

    extracted.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    return extracted


# ---------------------------------------------------------------------------
# URL / file content extraction  (used by ingest endpoints + enrichment)
# ---------------------------------------------------------------------------


def is_safe_url(url: str) -> bool:
    """Return True only if *url* does not resolve to a private/internal address."""
    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if any(
            x in host for x in ["localhost", "127.0.0.1", "0.0.0.0", "internal", "10."]
        ):
            return False
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        return not (ip.is_private or ip.is_loopback or ip.is_link_local)
    except Exception:
        return False


async def fetch_url_content(url: str) -> Dict[str, Any]:
    """Fetch and parse content from *url*.  Blocks SSRF via is_safe_url()."""
    if not is_safe_url(url):
        raise HTTPException(status_code=400, detail="URL not allowed")

    result: Dict[str, Any] = {
        "success": False,
        "content": "",
        "title": "",
        "metadata": {},
        "error": None,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as c:
            response = await c.get(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    )
                },
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type", "").lower()

            if "text/html" in content_type and BS4_AVAILABLE:
                soup = BeautifulSoup(response.text, "lxml")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                title_tag = soup.find("title")
                result["title"] = title_tag.get_text().strip() if title_tag else url
                meta_desc = soup.find("meta", {"name": "description"})
                if meta_desc:
                    result["metadata"]["description"] = meta_desc.get("content", "")
                result["content"] = soup.get_text(separator=" ", strip=True)[:50000]
                result["success"] = True
            elif "application/json" in content_type:
                result["content"] = response.text
                result["title"] = "JSON Data"
                result["success"] = True
            else:
                result["content"] = response.text[:50000]
                result["title"] = url
                result["success"] = True

    except Exception as exc:
        result["error"] = str(exc)
        logger.error("Failed to fetch URL %s: %s", url, exc)

    return result


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract plain text from *pdf_bytes* using PyPDF2.  Returns '' if unavailable."""
    if not PDF_AVAILABLE:
        return ""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except Exception as exc:
        logger.error("PDF extraction failed: %s", exc)
        return ""


def extract_text_from_image(image_bytes: bytes) -> str:
    """Run OCR on *image_bytes* using pytesseract.  Returns '' if unavailable."""
    if not OCR_AVAILABLE:
        return ""
    try:
        image = Image.open(BytesIO(image_bytes))
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as exc:
        logger.error("OCR extraction failed: %s", exc)
        return ""
