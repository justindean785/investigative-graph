"""
routers/system.py — Miscellaneous utility endpoints.

Currently exposes:
  GET /api/evidence/categories — returns the full evidence category catalogue

Add any future system-level, health, or metadata endpoints here.
"""

from typing import Optional

from core.security import validate_api_key
from fastapi import APIRouter, Header

router = APIRouter(prefix="/api", tags=["system"])

# ---------------------------------------------------------------------------
# Evidence categories catalogue
# Defined here because the path is /api/evidence/categories, not nested
# under /api/investigations.  This is pure metadata — no DB access.
# ---------------------------------------------------------------------------

EVIDENCE_CATEGORIES = {
    "web": {
        "label": "Web Evidence",
        "types": [
            {"value": "webpage", "label": "Web Page", "icon": "globe"},
            {"value": "screenshot", "label": "Website Screenshot", "icon": "image"},
            {"value": "url", "label": "URL", "icon": "link"},
            {"value": "forum_post", "label": "Forum Post", "icon": "message-square"},
            {"value": "blog_article", "label": "Blog Article", "icon": "file-text"},
            {
                "value": "paste_site",
                "label": "Paste Site Content",
                "icon": "clipboard",
            },
        ],
    },
    "social": {
        "label": "Social Media Evidence",
        "types": [
            {
                "value": "social_profile",
                "label": "Social Media Profile",
                "icon": "user",
            },
            {
                "value": "social_post",
                "label": "Social Media Post",
                "icon": "message-circle",
            },
            {
                "value": "social_comment",
                "label": "Social Media Comment",
                "icon": "message-square",
            },
            {"value": "thread", "label": "Thread", "icon": "git-branch"},
            {"value": "video_post", "label": "Video Post", "icon": "video"},
        ],
    },
    "identity": {
        "label": "Identity Evidence",
        "types": [
            {"value": "email_evidence", "label": "Email Address", "icon": "mail"},
            {"value": "username_evidence", "label": "Username", "icon": "at-sign"},
            {"value": "phone_evidence", "label": "Phone Number", "icon": "phone"},
            {"value": "alias", "label": "Alias", "icon": "users"},
            {"value": "real_name", "label": "Real Name", "icon": "user-check"},
        ],
    },
    "crypto": {
        "label": "Crypto / Financial Evidence",
        "types": [
            {"value": "crypto_wallet", "label": "Crypto Wallet", "icon": "wallet"},
            {
                "value": "blockchain_tx",
                "label": "Blockchain Transaction",
                "icon": "activity",
            },
            {
                "value": "exchange_account",
                "label": "Exchange Account",
                "icon": "database",
            },
            {
                "value": "payment_screenshot",
                "label": "Payment Screenshot",
                "icon": "credit-card",
            },
        ],
    },
    "infrastructure": {
        "label": "Infrastructure Evidence",
        "types": [
            {"value": "domain_evidence", "label": "Domain", "icon": "globe"},
            {"value": "subdomain", "label": "Subdomain", "icon": "git-merge"},
            {"value": "ip_evidence", "label": "IP Address", "icon": "server"},
            {"value": "server", "label": "Server", "icon": "hard-drive"},
            {"value": "dns_record", "label": "DNS Record", "icon": "list"},
            {"value": "whois_record", "label": "WHOIS Record", "icon": "file-text"},
        ],
    },
    "files": {
        "label": "Files and Media",
        "types": [
            {"value": "document", "label": "Document", "icon": "file-text"},
            {"value": "screenshot", "label": "Screenshot", "icon": "image"},
            {"value": "photo", "label": "Photo", "icon": "camera"},
            {"value": "video", "label": "Video", "icon": "video"},
            {"value": "audio", "label": "Audio", "icon": "volume-2"},
            {"value": "pdf", "label": "PDF", "icon": "file"},
            {"value": "spreadsheet", "label": "Spreadsheet", "icon": "table"},
        ],
    },
    "communication": {
        "label": "Communication Evidence",
        "types": [
            {"value": "email_message", "label": "Email Message", "icon": "mail"},
            {"value": "chat_log", "label": "Chat Log", "icon": "message-square"},
            {"value": "sms_message", "label": "SMS Message", "icon": "smartphone"},
            {"value": "telegram_chat", "label": "Telegram Chat", "icon": "send"},
            {"value": "discord_message", "label": "Discord Message", "icon": "hash"},
        ],
    },
    "forensics": {
        "label": "Technical Forensics",
        "types": [
            {"value": "metadata_dump", "label": "Metadata Dump", "icon": "code"},
            {"value": "exif_data", "label": "EXIF Data", "icon": "info"},
            {"value": "log_file", "label": "Log File", "icon": "file-code"},
            {"value": "hash_value", "label": "Hash Value", "icon": "hash"},
        ],
    },
    "notes": {
        "label": "Investigator Notes",
        "types": [
            {"value": "analyst_note", "label": "Analyst Note", "icon": "edit"},
            {"value": "observation", "label": "Observation", "icon": "eye"},
            {"value": "hypothesis", "label": "Hypothesis", "icon": "help-circle"},
            {"value": "lead_note", "label": "Lead", "icon": "lightbulb"},
        ],
    },
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/evidence/categories")
async def get_evidence_categories(x_api_key: Optional[str] = Header(None)):
    """Return the full evidence category and type catalogue."""
    await validate_api_key(x_api_key)
    return EVIDENCE_CATEGORIES
