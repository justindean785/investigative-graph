"""
routers/enrichment.py — Entity enrichment and extraction endpoints.

Routes:
  POST /api/enrich/entity                                    — mock-enrich a single entity
  POST /api/extract/entities                                 — extract indicators from raw text
  GET  /api/investigations/{id}/entities/{entity_id}/enrichment — get enrichment for a saved entity

Business logic (generate_mock_enrichment) lives here because it is only
called from this router.  No behaviour changes from server.py.
"""

from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.deps import ENTITY_PATTERNS, db, extract_entities_from_text
from core.security import validate_api_key
from fastapi import APIRouter, Header, HTTPException
from models import EnrichmentRequest, EntityExtractionRequest

router = APIRouter(prefix="/api", tags=["enrichment"])


# ---------------------------------------------------------------------------
# Mock enrichment data generator — preserved verbatim from server.py
# ---------------------------------------------------------------------------


def generate_mock_enrichment(entity_type: str, entity_value: str) -> Dict[str, Any]:
    """Generate realistic mock enrichment data based on entity type.

    Uses a deterministic seed (MD5 of the value) so results are stable
    for the same input, while still looking varied across different values.
    """
    seed = int(hashlib.md5(entity_value.encode()).hexdigest()[:8], 16)
    random.seed(seed)

    base_enrichment: Dict[str, Any] = {
        "entity_value": entity_value,
        "entity_type": entity_type,
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "sources_checked": [],
        "intelligence": {},
        "risk_assessment": {},
    }

    if entity_type == "email":
        breach_count = random.randint(0, 7)
        base_enrichment["sources_checked"] = [
            "HaveIBeenPwned",
            "DeHashed",
            "IntelX",
            "Snusbase",
        ]
        base_enrichment["intelligence"] = {
            "breach_exposure": {
                "total_breaches": breach_count,
                "breaches": [
                    {
                        "name": "LinkedIn 2021",
                        "date": "2021-06-22",
                        "exposed_data": ["email", "password_hash"],
                    },
                    {
                        "name": "Collection #1",
                        "date": "2019-01-17",
                        "exposed_data": ["email", "password"],
                    },
                    {
                        "name": "Apollo",
                        "date": "2018-07-23",
                        "exposed_data": ["email", "employer", "title"],
                    },
                ][:breach_count]
                if breach_count > 0
                else [],
            },
            "associated_usernames": [
                f"user_{random.randint(100, 999)}",
                f"admin_{random.randint(10, 99)}",
            ]
            if random.random() > 0.5
            else [],
            "associated_domains": [entity_value.split("@")[1]]
            if "@" in entity_value
            else [],
            "first_seen": (
                f"20{random.randint(15, 23)}-"
                f"{random.randint(1, 12):02d}-"
                f"{random.randint(1, 28):02d}"
            ),
            "last_activity": (
                f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
            ),
        }
        base_enrichment["risk_assessment"] = {
            "score": min(0.9, breach_count * 0.15 + random.uniform(0.1, 0.3)),
            "level": (
                "HIGH" if breach_count > 3 else "MEDIUM" if breach_count > 0 else "LOW"
            ),
            "factors": [
                "Multiple breach exposures" if breach_count > 1 else None,
                "Password potentially compromised" if breach_count > 0 else None,
                "Associated with suspicious domains" if random.random() > 0.7 else None,
            ],
        }
        base_enrichment["risk_assessment"]["factors"] = [
            f for f in base_enrichment["risk_assessment"]["factors"] if f
        ]

    elif entity_type == "domain":
        is_onion = ".onion" in entity_value
        base_enrichment["sources_checked"] = [
            "WHOIS",
            "SecurityTrails",
            "VirusTotal",
            "URLScan",
        ]
        base_enrichment["intelligence"] = {
            "whois": {
                "registrar": (
                    "Namecheap" if not is_onion else "N/A (Tor Hidden Service)"
                ),
                "registration_date": (
                    f"20{random.randint(18, 23)}-"
                    f"{random.randint(1, 12):02d}-"
                    f"{random.randint(1, 28):02d}"
                ),
                "expiration_date": (
                    f"20{random.randint(25, 28)}-"
                    f"{random.randint(1, 12):02d}-"
                    f"{random.randint(1, 28):02d}"
                ),
                "privacy_protected": random.random() > 0.3,
                "registrant_country": (
                    random.choice(["RU", "US", "CN", "DE", "NL", "RO"])
                    if not is_onion
                    else "Unknown"
                ),
            },
            "dns_records": {
                "a_records": [
                    f"{random.randint(1, 255)}.{random.randint(1, 255)}."
                    f"{random.randint(1, 255)}.{random.randint(1, 255)}"
                ],
                "mx_records": (
                    [f"mail.{entity_value}"] if random.random() > 0.5 else []
                ),
                "nameservers": [f"ns1.{entity_value}", f"ns2.{entity_value}"],
            },
            "hosting": {
                "asn": f"AS{random.randint(1000, 65000)}",
                "organization": random.choice(
                    [
                        "Cloudflare",
                        "Amazon AWS",
                        "DigitalOcean",
                        "OVH",
                        "M247",
                        "Bulletproof Host",
                    ]
                ),
                "country": random.choice(["US", "NL", "RO", "RU", "DE"]),
            },
            "threat_intelligence": {
                "malware_detected": random.random() > 0.8,
                "phishing_detected": random.random() > 0.85,
                "category": (
                    random.choice(
                        [
                            "uncategorized",
                            "technology",
                            "finance",
                            "suspicious",
                            "malware",
                        ]
                    )
                    if is_onion
                    else "uncategorized"
                ),
            },
        }
        intel = base_enrichment["intelligence"]
        base_enrichment["risk_assessment"] = {
            "score": 0.85 if is_onion else random.uniform(0.2, 0.6),
            "level": "HIGH" if is_onion else random.choice(["LOW", "MEDIUM"]),
            "factors": [
                "Tor hidden service (.onion)" if is_onion else None,
                "Privacy-protected WHOIS"
                if intel["whois"]["privacy_protected"]
                else None,
                "Hosted on bulletproof infrastructure"
                if "Bulletproof" in intel["hosting"]["organization"]
                else None,
            ],
        }
        base_enrichment["risk_assessment"]["factors"] = [
            f for f in base_enrichment["risk_assessment"]["factors"] if f
        ]

    elif entity_type == "wallet":
        is_eth = entity_value.startswith("0x")
        tx_count = random.randint(5, 200)
        base_enrichment["sources_checked"] = [
            "Etherscan" if is_eth else "Blockchain.com",
            "Chainalysis",
            "Crystal",
        ]
        base_enrichment["intelligence"] = {
            "blockchain": "Ethereum" if is_eth else "Bitcoin",
            "balance": {
                "amount": round(random.uniform(0.01, 50), 4),
                "currency": "ETH" if is_eth else "BTC",
                "usd_value": round(random.uniform(100, 150000), 2),
            },
            "transactions": {
                "total_count": tx_count,
                "incoming": random.randint(1, tx_count),
                "outgoing": tx_count - random.randint(1, tx_count // 2),
                "first_transaction": (
                    f"20{random.randint(17, 22)}-"
                    f"{random.randint(1, 12):02d}-"
                    f"{random.randint(1, 28):02d}"
                ),
                "last_transaction": (
                    f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
                ),
            },
            "exchange_interactions": {
                "binance": random.random() > 0.5,
                "coinbase": random.random() > 0.6,
                "kraken": random.random() > 0.7,
                "unknown_exchange": random.random() > 0.4,
            },
            "risk_indicators": {
                "mixer_usage": random.random() > 0.85,
                "darknet_association": random.random() > 0.8,
                "sanctioned_entity": random.random() > 0.95,
            },
        }
        risk_indicators = base_enrichment["intelligence"]["risk_indicators"]
        risk_score = 0.3
        if risk_indicators["mixer_usage"]:
            risk_score += 0.3
        if risk_indicators["darknet_association"]:
            risk_score += 0.25
        if risk_indicators["sanctioned_entity"]:
            risk_score += 0.35
        base_enrichment["risk_assessment"] = {
            "score": min(0.95, risk_score),
            "level": (
                "HIGH" if risk_score > 0.6 else "MEDIUM" if risk_score > 0.35 else "LOW"
            ),
            "factors": [
                "Mixer/tumbler usage detected"
                if risk_indicators["mixer_usage"]
                else None,
                "Darknet marketplace association"
                if risk_indicators["darknet_association"]
                else None,
                "Interaction with sanctioned entity"
                if risk_indicators["sanctioned_entity"]
                else None,
                f"High transaction volume ({tx_count} txs)" if tx_count > 100 else None,
            ],
        }
        base_enrichment["risk_assessment"]["factors"] = [
            f for f in base_enrichment["risk_assessment"]["factors"] if f
        ]

    elif entity_type == "ip":
        base_enrichment["sources_checked"] = [
            "IPInfo",
            "AbuseIPDB",
            "Shodan",
            "VirusTotal",
        ]
        base_enrichment["intelligence"] = {
            "geolocation": {
                "country": random.choice(["US", "RU", "CN", "DE", "NL", "RO", "UA"]),
                "city": random.choice(
                    [
                        "New York",
                        "Moscow",
                        "Beijing",
                        "Berlin",
                        "Amsterdam",
                        "Bucharest",
                    ]
                ),
                "isp": random.choice(
                    [
                        "Amazon AWS",
                        "Google Cloud",
                        "DigitalOcean",
                        "OVH",
                        "Rostelecom",
                        "China Telecom",
                    ]
                ),
            },
            "hosting": {
                "asn": f"AS{random.randint(1000, 65000)}",
                "is_datacenter": random.random() > 0.3,
                "is_vpn": random.random() > 0.7,
                "is_tor_exit": random.random() > 0.9,
            },
            "reputation": {
                "abuse_reports": random.randint(0, 50),
                "malicious_activity": random.random() > 0.7,
                "last_reported": (
                    f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"
                    if random.random() > 0.5
                    else None
                ),
            },
            "open_ports": (
                [22, 80, 443]
                + ([3389] if random.random() > 0.7 else [])
                + ([8080] if random.random() > 0.6 else [])
            ),
        }
        hosting = base_enrichment["intelligence"]["hosting"]
        abuse_count = base_enrichment["intelligence"]["reputation"]["abuse_reports"]
        base_enrichment["risk_assessment"] = {
            "score": min(
                0.9,
                abuse_count * 0.02 + (0.3 if hosting["is_tor_exit"] else 0),
            ),
            "level": (
                "HIGH" if abuse_count > 20 else "MEDIUM" if abuse_count > 5 else "LOW"
            ),
            "factors": [
                f"{abuse_count} abuse reports" if abuse_count > 0 else None,
                "Tor exit node" if hosting["is_tor_exit"] else None,
                "VPN/Proxy detected" if hosting["is_vpn"] else None,
            ],
        }
        base_enrichment["risk_assessment"]["factors"] = [
            f for f in base_enrichment["risk_assessment"]["factors"] if f
        ]

    elif entity_type == "person":
        base_enrichment["sources_checked"] = [
            "Social Media",
            "Public Records",
            "News Archives",
        ]
        base_enrichment["intelligence"] = {
            "social_presence": {
                "linkedin": random.random() > 0.4,
                "twitter": random.random() > 0.5,
                "facebook": random.random() > 0.6,
                "github": random.random() > 0.7,
            },
            "associated_entities": {
                "emails": (
                    [f"{entity_value.lower().replace(' ', '.')}@example.com"]
                    if random.random() > 0.5
                    else []
                ),
                "organizations": (
                    [random.choice(["TechCorp", "FinanceInc", "Unknown LLC"])]
                    if random.random() > 0.6
                    else []
                ),
            },
        }
        base_enrichment["risk_assessment"] = {
            "score": random.uniform(0.1, 0.5),
            "level": "LOW",
            "factors": [],
        }

    else:
        base_enrichment["intelligence"] = {
            "note": "Limited enrichment available for this entity type"
        }
        base_enrichment["risk_assessment"] = {
            "score": 0.3,
            "level": "UNKNOWN",
            "factors": [],
        }

    return base_enrichment


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/enrich/entity")
async def enrich_entity(
    request: EnrichmentRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Enrich an entity with intelligence data (mock enrichment)."""
    await validate_api_key(x_api_key)

    enrichment_data = generate_mock_enrichment(
        request.entity_type, request.entity_value
    )

    return {
        "success": True,
        "entity_id": request.entity_id,
        "enrichment": enrichment_data,
    }


@router.post("/extract/entities")
async def api_extract_entities(
    request: EntityExtractionRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Extract potential entity indicators from raw text content."""
    await validate_api_key(x_api_key)

    extracted = extract_entities_from_text(request.text, request.source_evidence_id)

    return {
        "success": True,
        "extracted_count": len(extracted),
        "entities": extracted,
        "patterns_checked": list(ENTITY_PATTERNS.keys()),
    }


@router.get("/investigations/{investigation_id}/entities/{entity_id}/enrichment")
async def get_entity_enrichment(
    investigation_id: str,
    entity_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Return mock enrichment data for a specific saved entity."""
    await validate_api_key(x_api_key)

    entity = await db.entities.find_one(
        {"id": entity_id, "investigation_id": investigation_id},
        {"_id": 0},
    )
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    enrichment_data = generate_mock_enrichment(entity["entity_type"], entity["value"])

    return {"success": True, "entity": entity, "enrichment": enrichment_data}
