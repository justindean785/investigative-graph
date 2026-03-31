"""
routers/investigations.py — Investigation CRUD, timeline, leads, exports, ingest, and report.

Routes (all prefixed /api/investigations):
  POST   /                              — create investigation
  GET    /                              — list investigations
  GET    /{investigation_id}            — get investigation
  PATCH  /{investigation_id}            — update investigation
  DELETE /{investigation_id}            — delete investigation (cascades all data)

  GET    /{investigation_id}/timeline   — list timeline events

  GET    /{investigation_id}/report     — generate threat report

  POST   /{investigation_id}/leads/generate        — run hypothesis engine
  GET    /{investigation_id}/leads                 — list leads
  PATCH  /{investigation_id}/leads/{lead_id}       — update lead status
  DELETE /{investigation_id}/leads/{lead_id}       — delete lead

  GET    /{investigation_id}/export/json           — full JSON export
  GET    /{investigation_id}/export/csv            — entities + relationships as ZIP/CSV
  GET    /{investigation_id}/export/markdown       — human-readable Markdown report

  POST   /{investigation_id}/ingest/url            — ingest URL with entity extraction
  POST   /{investigation_id}/ingest/text           — ingest raw text with entity extraction
  POST   /{investigation_id}/ingest/file           — upload file with OCR/PDF extraction

All business logic preserved verbatim from server.py.
Only import paths and router prefix differ.
"""

from __future__ import annotations

import collections
import csv
import io
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.deps import (
    OCR_AVAILABLE,
    PDF_AVAILABLE,
    create_timeline_event,
    db,
    extract_entities_from_text,
    extract_text_from_image,
    extract_text_from_pdf,
    fetch_url_content,
    serialize_datetime,
)
from core.security import validate_api_key
from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response, StreamingResponse
from models import (
    Evidence,
    EvidenceCreate,
    Investigation,
    InvestigationCreate,
    InvestigationUpdate,
    RawTextIngestRequest,
    URLIngestRequest,
)

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


# ---------------------------------------------------------------------------
# Lead generation engine — preserved verbatim from server.py
# ---------------------------------------------------------------------------


def generate_investigation_leads(
    entities: List[Dict],
    relationships: List[Dict],
    evidence: List[Dict],
    timeline: List[Dict],
) -> List[Dict]:
    """
    Automated hypothesis generation engine that analyses investigation data
    and produces actionable investigative leads.
    """
    from collections import defaultdict

    leads: List[Dict] = []

    if not entities:
        return leads

    # Build lookup structures
    entity_map = {e["id"]: e for e in entities}
    entities_by_type: Dict[str, list] = defaultdict(list)
    for e in entities:
        entities_by_type[e.get("entity_type", "unknown")].append(e)

    adjacency: Dict[str, list] = defaultdict(list)
    relationship_map: Dict[str, list] = defaultdict(list)
    for rel in relationships:
        source = rel.get("source_entity_id")
        target = rel.get("target_entity_id")
        if source and target:
            adjacency[source].append(target)
            adjacency[target].append(source)
            relationship_map[source].append(rel)
            relationship_map[target].append(rel)

    # ============= PATTERN 1: Shared Domain Cluster =============
    emails = entities_by_type.get("email", [])
    domains = entities_by_type.get("domain", [])

    if emails and domains:
        emails_by_domain: Dict[str, list] = defaultdict(list)
        for email in emails:
            email_value = email.get("value", "")
            if "@" in email_value:
                email_domain = email_value.split("@")[1].lower()
                emails_by_domain[email_domain].append(email)

        for domain in domains:
            domain_value = domain.get("value", "")
            connected_emails = list(emails_by_domain.get(domain_value.lower(), []))
            connected_ids = {e["id"] for e in connected_emails}
            for email in emails:
                if email["id"] not in connected_ids and email["id"] in adjacency.get(
                    domain["id"], []
                ):
                    connected_emails.append(email)

            if len(connected_emails) >= 2:
                leads.append(
                    {
                        "id": f"lead_{uuid.uuid4().hex[:12]}",
                        "lead_type": "alias_cluster",
                        "title": "Possible Operator Cluster Detected",
                        "description": (
                            f"Multiple email addresses ({len(connected_emails)}) are associated "
                            f"with the domain {domain_value}. This may indicate a single operator "
                            "using multiple aliases or an organized group."
                        ),
                        "confidence": min(0.95, 0.5 + len(connected_emails) * 0.15),
                        "severity": "high" if len(connected_emails) >= 3 else "medium",
                        "affected_entities": [e["id"] for e in connected_emails]
                        + [domain["id"]],
                        "evidence_ids": [],
                        "suggested_actions": [
                            {
                                "type": "investigate",
                                "label": "Cross-reference email registration dates",
                                "action": "enrich_emails",
                            },
                            {
                                "type": "search",
                                "label": "Search for username patterns",
                                "action": "username_search",
                            },
                            {
                                "type": "connect",
                                "label": "Link emails to domain operator",
                                "action": "create_relationship",
                            },
                        ],
                        "metadata": {
                            "pattern": "shared_domain",
                            "domain": domain_value,
                            "email_count": len(connected_emails),
                        },
                    }
                )

    # ============= PATTERN 2: Wallet Cluster Analysis =============
    wallets = entities_by_type.get("wallet", [])

    if len(wallets) >= 2:
        wallet_connections: Dict[str, set] = collections.defaultdict(set)
        for wallet in wallets:
            for connected_id in adjacency.get(wallet["id"], []):
                connected_entity = entity_map.get(connected_id)
                if connected_entity:
                    wallet_connections[wallet["id"]].add(connected_id)

        wallet_list = list(wallets)
        for i, w1 in enumerate(wallet_list):
            for w2 in wallet_list[i + 1 :]:
                shared = wallet_connections[w1["id"]] & wallet_connections[w2["id"]]
                if shared:
                    shared_entities = [
                        entity_map[eid] for eid in shared if eid in entity_map
                    ]
                    leads.append(
                        {
                            "id": f"lead_{uuid.uuid4().hex[:12]}",
                            "lead_type": "wallet_cluster",
                            "title": "Wallet Cluster Detected",
                            "description": (
                                f"Wallets '{w1.get('label') or w1.get('value')[:12]}...' and "
                                f"'{w2.get('label') or w2.get('value')[:12]}...' share "
                                f"{len(shared)} common connection(s). This may indicate fund "
                                "movement coordination or common ownership."
                            ),
                            "confidence": min(0.90, 0.6 + len(shared) * 0.1),
                            "severity": "high",
                            "affected_entities": [w1["id"], w2["id"]] + list(shared),
                            "evidence_ids": [],
                            "suggested_actions": [
                                {
                                    "type": "investigate",
                                    "label": "Trace transaction history",
                                    "action": "blockchain_trace",
                                },
                                {
                                    "type": "enrich",
                                    "label": "Check exchange withdrawals",
                                    "action": "exchange_check",
                                },
                                {
                                    "type": "connect",
                                    "label": "Link wallets as cluster",
                                    "action": "create_cluster_relationship",
                                },
                            ],
                            "metadata": {
                                "wallet_1": w1.get("value"),
                                "wallet_2": w2.get("value"),
                                "shared_connections": [
                                    e.get("value") for e in shared_entities
                                ],
                            },
                        }
                    )

    # ============= PATTERN 3: Infrastructure Correlation =============
    if len(domains) >= 2:
        domain_list = list(domains)
        for i, d1 in enumerate(domain_list):
            for d2 in domain_list[i + 1 :]:
                d1_connections = set(adjacency.get(d1["id"], []))
                d2_connections = set(adjacency.get(d2["id"], []))
                shared_infra = d1_connections & d2_connections
                both_onion = ".onion" in d1.get("value", "") and ".onion" in d2.get(
                    "value", ""
                )

                if shared_infra or both_onion:
                    leads.append(
                        {
                            "id": f"lead_{uuid.uuid4().hex[:12]}",
                            "lead_type": "shared_infrastructure",
                            "title": "Shared Infrastructure Pattern",
                            "description": (
                                f"Domains '{d1.get('value')}' and '{d2.get('value')}' appear "
                                "to share infrastructure or operator connections. "
                                f"{'Both are Tor hidden services.' if both_onion else ''}"
                            ),
                            "confidence": 0.75 if both_onion else 0.65,
                            "severity": "high" if both_onion else "medium",
                            "affected_entities": [d1["id"], d2["id"]],
                            "evidence_ids": [],
                            "suggested_actions": [
                                {
                                    "type": "enrich",
                                    "label": "Compare WHOIS/DNS records",
                                    "action": "domain_compare",
                                },
                                {
                                    "type": "investigate",
                                    "label": "Check hosting ASN overlap",
                                    "action": "asn_analysis",
                                },
                                {
                                    "type": "search",
                                    "label": "Search for related domains",
                                    "action": "domain_search",
                                },
                            ],
                            "metadata": {
                                "domain_1": d1.get("value"),
                                "domain_2": d2.get("value"),
                                "both_onion": both_onion,
                            },
                        }
                    )

    # ============= PATTERN 4: Username/Alias Reuse =============
    usernames = entities_by_type.get("username", [])
    persons = entities_by_type.get("person", [])

    email_usernames = []
    for email in emails:
        if "@" in email.get("value", ""):
            username_part = email["value"].split("@")[0].lower()
            email_usernames.append({"username": username_part, "source": email})

    username_values = [u.get("value", "").lower() for u in usernames]
    for eu in email_usernames:
        if eu["username"] in username_values or any(
            eu["username"] in uv or uv in eu["username"]
            for uv in username_values
            if len(uv) > 3
        ):
            matching_username = next(
                (u for u in usernames if eu["username"] in u.get("value", "").lower()),
                None,
            )
            if matching_username:
                leads.append(
                    {
                        "id": f"lead_{uuid.uuid4().hex[:12]}",
                        "lead_type": "username_reuse",
                        "title": "Username Reuse Pattern Detected",
                        "description": (
                            f"The username pattern '{eu['username']}' appears in both email "
                            f"'{eu['source'].get('value')}' and social handle "
                            f"'{matching_username.get('value')}'. This strongly suggests "
                            "the same individual."
                        ),
                        "confidence": 0.85,
                        "severity": "medium",
                        "affected_entities": [
                            eu["source"]["id"],
                            matching_username["id"],
                        ],
                        "evidence_ids": [],
                        "suggested_actions": [
                            {
                                "type": "search",
                                "label": "Search username across platforms",
                                "action": "osint_username_search",
                            },
                            {
                                "type": "connect",
                                "label": "Link as alias",
                                "action": "create_alias_relationship",
                            },
                            {
                                "type": "investigate",
                                "label": "Profile social media activity",
                                "action": "social_profile",
                            },
                        ],
                        "metadata": {
                            "username_pattern": eu["username"],
                            "email": eu["source"].get("value"),
                            "social_handle": matching_username.get("value"),
                        },
                    }
                )

    # ============= PATTERN 5: High-Risk Entity Connections =============
    for person in persons:
        person_connections = adjacency.get(person["id"], [])
        high_risk_connections = []

        for conn_id in person_connections:
            connected = entity_map.get(conn_id)
            if connected and connected.get("entity_type") in ["wallet", "domain"]:
                value = connected.get("value", "")
                if ".onion" in value or connected.get("entity_type") == "wallet":
                    high_risk_connections.append(connected)

        if len(high_risk_connections) >= 2:
            leads.append(
                {
                    "id": f"lead_{uuid.uuid4().hex[:12]}",
                    "lead_type": "high_risk_connection",
                    "title": "High-Risk Entity Network",
                    "description": (
                        f"Individual '{person.get('label') or person.get('value')}' is connected "
                        f"to {len(high_risk_connections)} high-risk entities including wallets "
                        "and/or dark web domains. This may indicate involvement in "
                        "suspicious activities."
                    ),
                    "confidence": min(0.90, 0.55 + len(high_risk_connections) * 0.15),
                    "severity": "critical"
                    if len(high_risk_connections) >= 3
                    else "high",
                    "affected_entities": [person["id"]]
                    + [e["id"] for e in high_risk_connections],
                    "evidence_ids": [],
                    "suggested_actions": [
                        {
                            "type": "investigate",
                            "label": "Deep profile investigation",
                            "action": "profile_deep_dive",
                        },
                        {
                            "type": "enrich",
                            "label": "Check all connected entities",
                            "action": "bulk_enrich",
                        },
                        {
                            "type": "report",
                            "label": "Flag for priority review",
                            "action": "priority_flag",
                        },
                    ],
                    "metadata": {
                        "person": person.get("value"),
                        "high_risk_count": len(high_risk_connections),
                        "high_risk_types": list(
                            set(e.get("entity_type") for e in high_risk_connections)
                        ),
                    },
                }
            )

    # ============= PATTERN 6: Timing Anomaly Detection =============
    if len(timeline) >= 3:
        timestamps = []
        for event in timeline:
            ts = event.get("timestamp")
            if isinstance(ts, str):
                try:
                    timestamps.append(datetime.fromisoformat(ts.replace("Z", "+00:00")))
                except (ValueError, TypeError):
                    pass
            elif isinstance(ts, datetime):
                timestamps.append(ts)

        if len(timestamps) >= 3:
            timestamps.sort()
            burst_events = []
            for i in range(1, len(timestamps)):
                diff = (timestamps[i] - timestamps[i - 1]).total_seconds()
                if diff < 300:  # 5 minutes
                    burst_events.append(i)

            if len(burst_events) >= 3:
                leads.append(
                    {
                        "id": f"lead_{uuid.uuid4().hex[:12]}",
                        "lead_type": "timing_anomaly",
                        "title": "Activity Burst Detected",
                        "description": (
                            f"Multiple investigation events ({len(burst_events) + 1}) occurred "
                            "in rapid succession. This may indicate automated data dumps, "
                            "coordinated activity, or a significant event window worth "
                            "focusing on."
                        ),
                        "confidence": 0.70,
                        "severity": "medium",
                        "affected_entities": [],
                        "evidence_ids": [],
                        "suggested_actions": [
                            {
                                "type": "investigate",
                                "label": "Review burst period evidence",
                                "action": "timeline_focus",
                            },
                            {
                                "type": "search",
                                "label": "Search for related external events",
                                "action": "news_search",
                            },
                        ],
                        "metadata": {
                            "burst_count": len(burst_events) + 1,
                            "time_window": "5 minutes",
                        },
                    }
                )

    # ============= PATTERN 7: Missing Connection Hypothesis =============
    unconnected_pairs = []
    entity_list = list(entities)
    for i, e1 in enumerate(entity_list):
        for e2 in entity_list[i + 1 :]:
            if e2["id"] in adjacency.get(e1["id"], []):
                continue

            e1_neighbors = set(adjacency.get(e1["id"], []))
            e2_neighbors = set(adjacency.get(e2["id"], []))
            common_neighbors = e1_neighbors & e2_neighbors

            if common_neighbors:
                common_entities = [
                    entity_map.get(n) for n in common_neighbors if n in entity_map
                ]
                if common_entities:
                    unconnected_pairs.append(
                        {"e1": e1, "e2": e2, "via": common_entities[0]}
                    )

    for pair in unconnected_pairs[:2]:
        leads.append(
            {
                "id": f"lead_{uuid.uuid4().hex[:12]}",
                "lead_type": "missing_connection",
                "title": "Potential Hidden Connection",
                "description": (
                    f"'{pair['e1'].get('label') or pair['e1'].get('value')}' and "
                    f"'{pair['e2'].get('label') or pair['e2'].get('value')}' are both "
                    f"connected to '{pair['via'].get('label') or pair['via'].get('value')}' "
                    "but not to each other. Investigate whether a direct relationship exists."
                ),
                "confidence": 0.55,
                "severity": "low",
                "affected_entities": [
                    pair["e1"]["id"],
                    pair["e2"]["id"],
                    pair["via"]["id"],
                ],
                "evidence_ids": [],
                "suggested_actions": [
                    {
                        "type": "investigate",
                        "label": "Research direct connection",
                        "action": "connection_research",
                    },
                    {
                        "type": "connect",
                        "label": "Create relationship if confirmed",
                        "action": "create_relationship",
                    },
                ],
                "metadata": {
                    "entity_1": pair["e1"].get("value"),
                    "entity_2": pair["e2"].get("value"),
                    "connecting_entity": pair["via"].get("value"),
                },
            }
        )

    # Sort leads by severity then confidence
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    leads.sort(key=lambda x: (severity_order.get(x["severity"], 4), -x["confidence"]))

    for lead in leads:
        lead["status"] = "new"

    return leads


# ===========================================================================
# INVESTIGATION CRUD ROUTES
# ===========================================================================


@router.post("/", response_model=Investigation)
async def create_investigation(
    input: InvestigationCreate,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    investigation = Investigation(
        name=input.name,
        description=input.description,
        tags=input.tags,
    )

    doc = serialize_datetime(investigation.model_dump())
    await db.investigations.insert_one(doc)

    await create_timeline_event(
        investigation.id,
        "investigation_created",
        f"Investigation '{investigation.name}' created",
    )

    return investigation


@router.get("/")
async def get_investigations(
    x_api_key: str = Header(None),
    skip: int = 0,
    limit: int = 100,
):
    await validate_api_key(x_api_key)
    limit = min(limit, 500)

    investigations = (
        await db.investigations.find({}, {"_id": 0})
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    for inv in investigations:
        if isinstance(inv.get("created_at"), str):
            inv["created_at"] = datetime.fromisoformat(inv["created_at"])
        if isinstance(inv.get("updated_at"), str):
            inv["updated_at"] = datetime.fromisoformat(inv["updated_at"])

    return investigations


@router.get("/{investigation_id}", response_model=Investigation)
async def get_investigation(
    investigation_id: str,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    investigation = await db.investigations.find_one(
        {"id": investigation_id}, {"_id": 0}
    )
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    if isinstance(investigation.get("created_at"), str):
        investigation["created_at"] = datetime.fromisoformat(
            investigation["created_at"]
        )
    if isinstance(investigation.get("updated_at"), str):
        investigation["updated_at"] = datetime.fromisoformat(
            investigation["updated_at"]
        )

    return investigation


@router.patch("/{investigation_id}", response_model=Investigation)
async def update_investigation(
    investigation_id: str,
    input: InvestigationUpdate,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    investigation = await db.investigations.find_one(
        {"id": investigation_id}, {"_id": 0}
    )
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    update_data = input.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.investigations.update_one({"id": investigation_id}, {"$set": update_data})

    updated_inv = await db.investigations.find_one({"id": investigation_id}, {"_id": 0})
    if isinstance(updated_inv.get("created_at"), str):
        updated_inv["created_at"] = datetime.fromisoformat(updated_inv["created_at"])
    if isinstance(updated_inv.get("updated_at"), str):
        updated_inv["updated_at"] = datetime.fromisoformat(updated_inv["updated_at"])

    return updated_inv


@router.delete("/{investigation_id}")
async def delete_investigation(
    investigation_id: str,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    result = await db.investigations.delete_one({"id": investigation_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Investigation not found")

    # Cascade-delete all related collections
    await db.entities.delete_many({"investigation_id": investigation_id})
    await db.relationships.delete_many({"investigation_id": investigation_id})
    await db.timeline_events.delete_many({"investigation_id": investigation_id})
    await db.evidence.delete_many({"investigation_id": investigation_id})
    await db.ai_suggestions.delete_many({"investigation_id": investigation_id})
    await db.investigation_leads.delete_many({"investigation_id": investigation_id})
    await db.chat_messages.delete_many({"investigation_id": investigation_id})

    return {"success": True, "message": "Investigation and all related data deleted"}


# ===========================================================================
# TIMELINE ROUTE
# ===========================================================================


@router.get("/{investigation_id}/timeline")
async def get_timeline(
    investigation_id: str,
    x_api_key: str = Header(None),
    skip: int = 0,
    limit: int = 200,
):
    await validate_api_key(x_api_key)
    limit = min(limit, 1000)

    events = (
        await db.timeline_events.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        )
        .sort("timestamp", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )

    for event in events:
        if isinstance(event.get("timestamp"), str):
            event["timestamp"] = datetime.fromisoformat(event["timestamp"])

    return events


# ===========================================================================
# REPORT ROUTE
# ===========================================================================


@router.get("/{investigation_id}/report")
async def generate_report(
    investigation_id: str,
    x_api_key: str = Header(None),
):
    await validate_api_key(x_api_key)

    investigation = await db.investigations.find_one(
        {"id": investigation_id}, {"_id": 0}
    )
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    entities = await db.entities.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    evidence = await db.evidence.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    timeline = (
        await db.timeline_events.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        )
        .sort("timestamp", -1)
        .to_list(10000)
    )
    leads = await db.investigation_leads.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)

    # Threat scoring
    entity_type_counts: Dict[str, int] = {}
    high_risk_entities: List[Dict[str, Any]] = []
    for e in entities:
        etype = e.get("entity_type", "unknown")
        entity_type_counts[etype] = entity_type_counts.get(etype, 0) + 1
        risk = e.get("risk_score", 0)
        if risk >= 0.7:
            high_risk_entities.append(
                {
                    "id": e.get("id"),
                    "type": etype,
                    "value": e.get("value"),
                    "risk_score": risk,
                }
            )

    connection_density = round(len(relationships) / max(len(entities), 1), 2)

    risk_scores = [
        e.get("risk_score", 0) for e in entities if e.get("risk_score", 0) > 0
    ]
    severity_map = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
    lead_scores = [severity_map.get(ld.get("severity", "medium"), 0.5) for ld in leads]
    all_scores = risk_scores + lead_scores
    overall_threat_score = round(sum(all_scores) / max(len(all_scores), 1), 2)

    if overall_threat_score >= 0.75:
        threat_level = "CRITICAL"
    elif overall_threat_score >= 0.5:
        threat_level = "HIGH"
    elif overall_threat_score >= 0.25:
        threat_level = "MEDIUM"
    else:
        threat_level = "LOW"

    verified_evidence = [
        e for e in evidence if e.get("verification_status") == "verified"
    ]
    disputed_evidence = [
        e for e in evidence if e.get("verification_status") == "disputed"
    ]
    evidence_by_type: Dict[str, int] = {}
    for e in evidence:
        etype = e.get("evidence_type", "unknown")
        evidence_by_type[etype] = evidence_by_type.get(etype, 0) + 1

    connection_count: Dict[str, int] = {}
    for r in relationships:
        src = r.get("source_entity_id", "")
        tgt = r.get("target_entity_id", "")
        connection_count[src] = connection_count.get(src, 0) + 1
        connection_count[tgt] = connection_count.get(tgt, 0) + 1

    entity_map = {e.get("id"): e for e in entities}
    key_entities = sorted(connection_count.items(), key=lambda x: x[1], reverse=True)[
        :10
    ]
    key_findings: List[Dict[str, Any]] = []
    for eid, count in key_entities:
        ent = entity_map.get(eid)
        if ent:
            key_findings.append(
                {
                    "entity_id": eid,
                    "type": ent.get("entity_type"),
                    "value": ent.get("value"),
                    "connections": count,
                    "risk_score": ent.get("risk_score", 0),
                }
            )

    return {
        "investigation": investigation,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "threat_assessment": {
            "overall_score": overall_threat_score,
            "threat_level": threat_level,
            "high_risk_entities": high_risk_entities,
            "connection_density": connection_density,
        },
        "statistics": {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "total_evidence": len(evidence),
            "verified_evidence": len(verified_evidence),
            "disputed_evidence": len(disputed_evidence),
            "total_leads": len(leads),
            "timeline_events": len(timeline),
            "entity_breakdown": entity_type_counts,
            "evidence_breakdown": evidence_by_type,
        },
        "key_findings": key_findings,
        "leads": [
            {
                "id": ld.get("id"),
                "type": ld.get("lead_type"),
                "title": ld.get("title"),
                "severity": ld.get("severity"),
                "status": ld.get("status"),
            }
            for ld in leads
        ],
        "entities": entities,
        "relationships": relationships,
        "evidence": evidence,
        "timeline": timeline[:100],
    }


# ===========================================================================
# LEADS ROUTES
# ===========================================================================


@router.post("/{investigation_id}/leads/generate")
async def generate_leads(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Generate investigation leads using the automated hypothesis engine."""
    await validate_api_key(x_api_key)

    entities = await db.entities.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    evidence = await db.evidence.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    timeline = (
        await db.timeline_events.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        )
        .sort("timestamp", -1)
        .to_list(100)
    )

    leads = generate_investigation_leads(entities, relationships, evidence, timeline)

    for lead in leads:
        lead["investigation_id"] = investigation_id
        lead["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.investigation_leads.update_one(
            {"id": lead["id"]}, {"$set": lead}, upsert=True
        )

    await create_timeline_event(
        investigation_id=investigation_id,
        event_type="leads_generated",
        description=f"Lead engine generated {len(leads)} investigation leads",
        metadata={
            "lead_count": len(leads),
            "lead_types": list(set(ld["lead_type"] for ld in leads)),
        },
    )

    return {"success": True, "leads_generated": len(leads), "leads": leads}


@router.get("/{investigation_id}/leads")
async def get_investigation_leads(
    investigation_id: str,
    status: Optional[str] = None,
    x_api_key: Optional[str] = Header(None),
):
    """Return all leads for an investigation, optionally filtered by status."""
    await validate_api_key(x_api_key)

    query: Dict[str, Any] = {"investigation_id": investigation_id}
    if status:
        query["status"] = status

    leads = (
        await db.investigation_leads.find(query, {"_id": 0})
        .sort("created_at", -1)
        .to_list(100)
    )

    return {"success": True, "total": len(leads), "leads": leads}


@router.patch("/{investigation_id}/leads/{lead_id}")
async def update_lead_status(
    investigation_id: str,
    lead_id: str,
    status: str,
    x_api_key: Optional[str] = Header(None),
):
    """Update the status of an investigation lead."""
    await validate_api_key(x_api_key)

    if status not in {"new", "investigating", "confirmed", "dismissed"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    result = await db.investigation_leads.update_one(
        {"id": lead_id, "investigation_id": investigation_id},
        {
            "$set": {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")

    await create_timeline_event(
        investigation_id=investigation_id,
        event_type="lead_status_updated",
        description=f"Lead status updated to: {status}",
        metadata={"lead_id": lead_id, "new_status": status},
    )

    return {"success": True, "lead_id": lead_id, "status": status}


@router.delete("/{investigation_id}/leads/{lead_id}")
async def delete_lead(
    investigation_id: str,
    lead_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Delete an investigation lead."""
    await validate_api_key(x_api_key)

    result = await db.investigation_leads.delete_one(
        {"id": lead_id, "investigation_id": investigation_id}
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")

    return {"success": True}


# ===========================================================================
# EXPORT ROUTES
# ===========================================================================


@router.get("/{investigation_id}/export/json")
async def export_investigation_json(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """
    Export a complete investigation snapshot as a structured JSON document.
    Includes investigation metadata, all entities, relationships, evidence,
    and the 100 most recent timeline events.
    """
    await validate_api_key(x_api_key)

    investigation = await db.investigations.find_one(
        {"id": investigation_id}, {"_id": 0}
    )
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    entities = await db.entities.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    evidence = await db.evidence.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    timeline = (
        await db.timeline_events.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        )
        .sort("timestamp", -1)
        .to_list(100)
    )
    leads = await db.investigation_leads.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(100)

    payload = serialize_datetime(
        {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "investigation": investigation,
            "statistics": {
                "total_entities": len(entities),
                "total_relationships": len(relationships),
                "total_evidence": len(evidence),
                "total_leads": len(leads),
            },
            "entities": entities,
            "relationships": relationships,
            "evidence": evidence,
            "leads": leads,
            "timeline": timeline,
        }
    )

    case_id = investigation.get("case_id", investigation_id)
    return JSONResponse(
        content=payload,
        headers={
            "Content-Disposition": f'attachment; filename="{case_id}_export.json"'
        },
    )


@router.get("/{investigation_id}/export/csv")
async def export_investigation_csv(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """
    Export investigation entities and relationships as a ZIP archive
    containing two CSV files: entities.csv and relationships.csv.
    """
    await validate_api_key(x_api_key)

    investigation = await db.investigations.find_one(
        {"id": investigation_id}, {"_id": 0}
    )
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    entities = await db.entities.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)

    # Build entity CSV
    entity_buf = io.StringIO()
    ent_writer = csv.DictWriter(
        entity_buf,
        fieldnames=[
            "id",
            "entity_type",
            "value",
            "label",
            "confidence",
            "risk_score",
            "notes",
            "created_at",
        ],
        extrasaction="ignore",
    )
    ent_writer.writeheader()
    for e in entities:
        ent_writer.writerow(
            {
                "id": e.get("id", ""),
                "entity_type": e.get("entity_type", ""),
                "value": e.get("value", ""),
                "label": e.get("label", ""),
                "confidence": e.get("confidence", ""),
                "risk_score": e.get("risk_score", ""),
                "notes": e.get("notes", ""),
                "created_at": e.get("created_at", ""),
            }
        )

    # Build relationship CSV
    rel_buf = io.StringIO()
    rel_writer = csv.DictWriter(
        rel_buf,
        fieldnames=[
            "id",
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            "label",
            "confidence",
            "created_at",
        ],
        extrasaction="ignore",
    )
    rel_writer.writeheader()
    for r in relationships:
        rel_writer.writerow(
            {
                "id": r.get("id", ""),
                "source_entity_id": r.get("source_entity_id", ""),
                "target_entity_id": r.get("target_entity_id", ""),
                "relationship_type": r.get("relationship_type", ""),
                "label": r.get("label", ""),
                "confidence": r.get("confidence", ""),
                "created_at": r.get("created_at", ""),
            }
        )

    # Package both CSVs into an in-memory ZIP
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("entities.csv", entity_buf.getvalue())
        zf.writestr("relationships.csv", rel_buf.getvalue())
    zip_buf.seek(0)

    case_id = investigation.get("case_id", investigation_id)
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{case_id}_export.zip"'},
    )


@router.get("/{investigation_id}/export/markdown")
async def export_investigation_markdown(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """
    Export an investigation as a human-readable Markdown report suitable for
    sharing or archival.  Includes a narrative summary, entity table,
    relationship list, evidence inventory, and active leads.
    """
    # Truncation lengths for report columns / previews
    _MD_ENTITY_VAL_LEN = 60
    _MD_ENTITY_LBL_LEN = 40
    _MD_REL_VAL_LEN = 40
    _MD_CONTENT_PREVIEW_LEN = 100

    await validate_api_key(x_api_key)

    investigation = await db.investigations.find_one(
        {"id": investigation_id}, {"_id": 0}
    )
    if not investigation:
        raise HTTPException(status_code=404, detail="Investigation not found")

    entities = await db.entities.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    evidence = await db.evidence.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    leads = (
        await db.investigation_leads.find(
            {"investigation_id": investigation_id}, {"_id": 0}
        )
        .sort("confidence", -1)
        .to_list(50)
    )

    entity_map = {e["id"]: e for e in entities}

    lines: List[str] = []
    lines.append(f"# Investigation Report: {investigation.get('name', 'Unknown')}")
    lines.append(f"\n**Case ID:** `{investigation.get('case_id', 'N/A')}`  ")
    lines.append(f"**Status:** {investigation.get('status', 'N/A')}  ")
    lines.append(f"**Created:** {investigation.get('created_at', 'N/A')}  ")
    lines.append(f"**Exported:** {datetime.now(timezone.utc).isoformat()}  ")
    if investigation.get("description"):
        lines.append(f"\n## Description\n\n{investigation['description']}")
    if investigation.get("tags"):
        lines.append(f"\n**Tags:** {', '.join(investigation['tags'])}")

    lines.append("\n## Statistics\n")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Entities | {len(entities)} |")
    lines.append(f"| Relationships | {len(relationships)} |")
    lines.append(f"| Evidence Items | {len(evidence)} |")
    lines.append(f"| Active Leads | {len(leads)} |")

    if entities:
        lines.append(f"\n## Entities ({len(entities)})\n")
        lines.append("| Type | Value | Label | Confidence | Risk |")
        lines.append("|------|-------|-------|-----------|------|")
        for e in sorted(entities, key=lambda x: x.get("risk_score", 0), reverse=True):
            conf = f"{e.get('confidence', 0):.0%}"
            risk = f"{e.get('risk_score', 0):.0%}"
            val = (e.get("value") or "")[:_MD_ENTITY_VAL_LEN]
            lbl = (e.get("label") or "")[:_MD_ENTITY_LBL_LEN]
            lines.append(
                f"| {e.get('entity_type', '')} | {val} | {lbl} | {conf} | {risk} |"
            )

    if relationships:
        lines.append(f"\n## Relationships ({len(relationships)})\n")
        for r in relationships:
            src = entity_map.get(r.get("source_entity_id", ""), {})
            tgt = entity_map.get(r.get("target_entity_id", ""), {})
            src_val = (src.get("value") or src.get("id", "?"))[:_MD_REL_VAL_LEN]
            tgt_val = (tgt.get("value") or tgt.get("id", "?"))[:_MD_REL_VAL_LEN]
            rel_type = r.get("relationship_type", "linked_to")
            conf = f"{r.get('confidence', 0):.0%}"
            lines.append(
                f"- **{src_val}** → `{rel_type}` → **{tgt_val}** *(confidence: {conf})*"
            )

    if evidence:
        lines.append(f"\n## Evidence ({len(evidence)})\n")
        status_label = {
            "verified": "[verified]",
            "unverified": "[unverified]",
            "disputed": "[disputed]",
        }
        for ev in evidence:
            status_tag = status_label.get(
                ev.get("verification_status", "unverified"), "[unverified]"
            )
            ev_type = ev.get("evidence_type", "unknown")
            url_part = (
                f" [{ev.get('source_url', '')}]({ev.get('source_url', '')})"
                if ev.get("source_url")
                else ""
            )
            content_preview = (ev.get("content") or "")[
                :_MD_CONTENT_PREVIEW_LEN
            ].replace("\n", " ")
            tags_part = f" `{'` `'.join(ev.get('tags', []))}`" if ev.get("tags") else ""
            lines.append(
                f"- {status_tag} **[{ev_type}]**{url_part}{tags_part}: {content_preview}..."
            )

    if leads:
        lines.append(f"\n## Investigation Leads ({len(leads)})\n")
        sev_label = {
            "critical": "[CRITICAL]",
            "high": "[HIGH]",
            "medium": "[MEDIUM]",
            "low": "[LOW]",
        }
        for lead in leads:
            sev_tag = sev_label.get(
                str(lead.get("severity", "medium")).lower(), "[MEDIUM]"
            )
            conf_pct = f"{lead.get('confidence', 0):.0%}"
            lines.append(
                f"### {sev_tag} {lead.get('title', 'Untitled')} *(confidence: {conf_pct})*"
            )
            lines.append(f"\n{lead.get('description', '')}\n")
            if lead.get("suggested_actions"):
                lines.append("**Suggested Actions:**")
                for action in lead["suggested_actions"][:3]:
                    lines.append(f"- {action.get('description', str(action))}")
            lines.append("")

    if investigation.get("notes"):
        lines.append(f"\n## Analyst Notes\n\n{investigation['notes']}")

    markdown_content = "\n".join(lines)
    case_id = investigation.get("case_id", investigation_id)

    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{case_id}_report.md"'},
    )


# ===========================================================================
# INGEST ROUTES
# ===========================================================================


@router.post("/{investigation_id}/ingest/url")
async def ingest_url(
    investigation_id: str,
    request: URLIngestRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Quick ingest evidence from a URL with automatic content extraction and entity detection."""
    await validate_api_key(x_api_key)

    url_data = await fetch_url_content(request.url)

    if not url_data["success"]:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to fetch URL: {url_data.get('error', 'Unknown error')}",
        )

    evidence = Evidence(
        investigation_id=investigation_id,
        evidence_type=request.evidence_type,
        source_url=request.url,
        content=url_data.get("content", "")[:10000],
        notes=request.notes
        or f"Auto-ingested from URL: {url_data.get('title', request.url)}",
    )

    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)

    full_text = (
        f"{url_data.get('title', '')} {url_data.get('content', '')} {request.url}"
    )
    detected_entities = extract_entities_from_text(full_text, evidence.id)

    await create_timeline_event(
        investigation_id,
        "evidence_ingested",
        f"URL ingested: {url_data.get('title', request.url)[:50]}",
        metadata={
            "evidence_id": evidence.id,
            "detected_entities": len(detected_entities),
        },
    )

    return {
        "success": True,
        "evidence": {
            "id": evidence.id,
            "type": evidence.evidence_type,
            "title": url_data.get("title", request.url),
            "source_url": request.url,
            "content_length": len(url_data.get("content", "")),
        },
        "detected_entities": detected_entities,
        "extraction_stats": {"total_found": len(detected_entities), "by_type": {}},
    }


@router.post("/{investigation_id}/ingest/text")
async def ingest_raw_text(
    investigation_id: str,
    request: RawTextIngestRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Quick ingest raw text with automatic entity extraction."""
    await validate_api_key(x_api_key)

    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    evidence = Evidence(
        investigation_id=investigation_id,
        evidence_type=request.evidence_type,
        content=request.content[:50000],
        notes=request.notes or f"Raw text: {request.title or 'Untitled'}",
    )

    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)

    detected_entities = extract_entities_from_text(request.content, evidence.id)

    entities_by_type: Dict[str, int] = {}
    for entity in detected_entities:
        etype = entity.get("type", "unknown")
        entities_by_type[etype] = entities_by_type.get(etype, 0) + 1

    await create_timeline_event(
        investigation_id,
        "evidence_ingested",
        f"Raw text ingested: {request.title or 'Untitled'}",
        metadata={
            "evidence_id": evidence.id,
            "detected_entities": len(detected_entities),
        },
    )

    return {
        "success": True,
        "evidence": {
            "id": evidence.id,
            "type": evidence.evidence_type,
            "title": request.title or "Raw Text",
            "content_length": len(request.content),
        },
        "detected_entities": detected_entities,
        "extraction_stats": {
            "total_found": len(detected_entities),
            "by_type": entities_by_type,
        },
    }


@router.post("/{investigation_id}/ingest/file")
async def ingest_file(
    investigation_id: str,
    file: UploadFile = File(...),
    evidence_type: str = Form("document"),
    notes: str = Form(""),
    x_api_key: Optional[str] = Header(None),
):
    """Upload and ingest a file with OCR/text extraction."""
    await validate_api_key(x_api_key)

    file_content = await file.read()
    file_size = len(file_content)

    if file_size > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    extracted_text = ""
    content_type = file.content_type or ""
    filename = file.filename or "uploaded_file"

    if "pdf" in content_type or filename.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_content)
        evidence_type = "pdf"
    elif "image" in content_type or any(
        filename.lower().endswith(ext)
        for ext in [".png", ".jpg", ".jpeg", ".gif", ".webp"]
    ):
        extracted_text = extract_text_from_image(file_content)
        evidence_type = "screenshot"
    elif "text" in content_type or any(
        filename.lower().endswith(ext) for ext in [".txt", ".log", ".csv"]
    ):
        try:
            extracted_text = file_content.decode("utf-8")
        except (UnicodeDecodeError, ValueError):
            extracted_text = file_content.decode("latin-1", errors="ignore")

    evidence = Evidence(
        investigation_id=investigation_id,
        evidence_type=evidence_type,
        content=extracted_text[:50000]
        if extracted_text
        else f"[Binary file: {filename}]",
        notes=notes or f"Uploaded file: {filename}",
    )

    doc = serialize_datetime(evidence.model_dump())
    await db.evidence.insert_one(doc)

    detected_entities = []
    if extracted_text:
        detected_entities = extract_entities_from_text(extracted_text, evidence.id)

    entities_by_type: Dict[str, int] = {}
    for entity in detected_entities:
        etype = entity.get("type", "unknown")
        entities_by_type[etype] = entities_by_type.get(etype, 0) + 1

    await create_timeline_event(
        investigation_id,
        "file_uploaded",
        f"File uploaded: {filename}",
        metadata={
            "evidence_id": evidence.id,
            "filename": filename,
            "file_size": file_size,
            "detected_entities": len(detected_entities),
        },
    )

    return {
        "success": True,
        "evidence": {
            "id": evidence.id,
            "type": evidence_type,
            "filename": filename,
            "file_size": file_size,
            "text_extracted": bool(extracted_text),
            "content_length": len(extracted_text) if extracted_text else 0,
        },
        "detected_entities": detected_entities,
        "extraction_stats": {
            "total_found": len(detected_entities),
            "by_type": entities_by_type,
            "ocr_available": OCR_AVAILABLE,
            "pdf_available": PDF_AVAILABLE,
        },
    }
