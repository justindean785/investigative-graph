"""
routers/graph.py — Graph intelligence analysis endpoints.

Routes (all nested under /api/investigations):
  POST /{investigation_id}/graph/analyze           — full analysis
  GET  /{investigation_id}/graph/clusters          — cluster detection
  GET  /{investigation_id}/graph/suspicious-patterns — pattern detection

Business logic (analyze_graph_intelligence) lives here because it is
only called from this router.  No behavior changes from server.py.
"""

from __future__ import annotations

import collections
from typing import Any, Dict, List, Optional

from core.deps import create_timeline_event, db
from core.security import validate_api_key
from fastapi import APIRouter, Header

router = APIRouter(prefix="/api/investigations", tags=["graph"])


# ---------------------------------------------------------------------------
# Graph intelligence algorithm — preserved verbatim from server.py
# ---------------------------------------------------------------------------


def analyze_graph_intelligence(
    entities: List[Dict],
    relationships: List[Dict],
) -> Dict[str, Any]:
    """Perform graph analysis to detect clusters, central nodes, and suspicious patterns."""
    if not entities:
        return {
            "clusters": [],
            "central_nodes": [],
            "suspicious_patterns": [],
            "shortest_paths": [],
            "summary": "No entities to analyze",
        }

    # Build adjacency list
    entity_map = {e["id"]: e for e in entities}
    adjacency: Dict[str, list] = {e["id"]: [] for e in entities}

    for rel in relationships:
        source = rel.get("source_entity_id")
        target = rel.get("target_entity_id")
        if source in adjacency and target in adjacency:
            adjacency[source].append(target)
            adjacency[target].append(source)

    # Degree centrality
    centrality_scores: Dict[str, int] = {
        entity_id: len(connections) for entity_id, connections in adjacency.items()
    }

    # Top-3 central nodes
    central_nodes: List[Dict[str, Any]] = []
    sorted_by_centrality = sorted(
        centrality_scores.items(), key=lambda x: x[1], reverse=True
    )
    for entity_id, degree in sorted_by_centrality[:3]:
        if degree > 0 and entity_id in entity_map:
            entity = entity_map[entity_id]
            central_nodes.append(
                {
                    "entity_id": entity_id,
                    "label": entity.get("label") or entity.get("value"),
                    "type": entity.get("entity_type"),
                    "connection_count": degree,
                    "importance": "high" if degree >= 3 else "medium",
                }
            )

    # Iterative BFS cluster detection (avoids recursion stack overflow on large graphs)
    visited: set = set()
    clusters: List[Dict[str, Any]] = []

    for entity_id in adjacency:
        if entity_id not in visited:
            cluster: List[str] = []
            queue: collections.deque = collections.deque([entity_id])
            visited.add(entity_id)
            while queue:
                node = queue.popleft()
                cluster.append(node)
                for neighbor in adjacency.get(node, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            if len(cluster) > 1:
                cluster_entities = [
                    entity_map[eid] for eid in cluster if eid in entity_map
                ]
                clusters.append(
                    {
                        "id": f"cluster_{len(clusters) + 1}",
                        "size": len(cluster),
                        "entity_types": list(
                            set(e.get("entity_type") for e in cluster_entities)
                        ),
                        "entities": [
                            {
                                "id": e["id"],
                                "label": e.get("label") or e.get("value"),
                                "type": e.get("entity_type"),
                            }
                            for e in cluster_entities
                        ],
                        "cohesion": "tight" if len(cluster) <= 4 else "loose",
                    }
                )

    # Suspicious pattern detection
    suspicious_patterns: List[Dict[str, Any]] = []

    # Pattern 1: high-risk entity clusters
    for cluster in clusters:
        high_risk_types = {"wallet", "domain"}
        cluster_types = set(cluster["entity_types"])
        if cluster_types & high_risk_types:
            suspicious_patterns.append(
                {
                    "type": "high_risk_cluster",
                    "severity": "high",
                    "description": (
                        f"Cluster contains {', '.join(cluster_types & high_risk_types)} "
                        "entities that may indicate financial or infrastructure connections"
                    ),
                    "affected_entities": [e["id"] for e in cluster["entities"]],
                }
            )

    # Pattern 2: hub entities (many connections)
    for entity_id, degree in centrality_scores.items():
        if degree >= 3 and entity_id in entity_map:
            entity = entity_map[entity_id]
            if entity.get("entity_type") in {"email", "wallet", "domain"}:
                suspicious_patterns.append(
                    {
                        "type": "hub_entity",
                        "severity": "medium",
                        "description": (
                            f"Entity '{entity.get('label') or entity.get('value')}' "
                            "connects multiple entities - potential key actor or infrastructure"
                        ),
                        "affected_entities": [entity_id] + adjacency[entity_id],
                    }
                )

    # Shortest paths between high-risk entities
    shortest_paths: List[Dict[str, Any]] = []
    high_risk_entities = [
        e for e in entities if e.get("entity_type") in {"wallet", "person"}
    ]

    if len(high_risk_entities) >= 2:

        def find_path(start: str, end: str) -> Optional[List[str]]:
            if start == end:
                return [start]
            queue_p: List[List[str]] = [[start]]
            visited_paths: set = {start}
            while queue_p:
                path = queue_p.pop(0)
                node = path[-1]
                for neighbor in adjacency.get(node, []):
                    if neighbor == end:
                        return path + [neighbor]
                    if neighbor not in visited_paths:
                        visited_paths.add(neighbor)
                        queue_p.append(path + [neighbor])
            return None

        for i, e1 in enumerate(high_risk_entities[:3]):
            for e2 in high_risk_entities[i + 1 : 3]:
                path = find_path(e1["id"], e2["id"])
                if path and len(path) > 1:
                    path_entities = [
                        entity_map.get(eid) for eid in path if eid in entity_map
                    ]
                    shortest_paths.append(
                        {
                            "from": e1.get("label") or e1.get("value"),
                            "to": e2.get("label") or e2.get("value"),
                            "length": len(path) - 1,
                            "path": [
                                {
                                    "id": e["id"],
                                    "label": e.get("label") or e.get("value"),
                                    "type": e.get("entity_type"),
                                }
                                for e in path_entities
                                if e
                            ],
                        }
                    )

    return {
        "clusters": clusters,
        "central_nodes": central_nodes,
        "suspicious_patterns": suspicious_patterns,
        "shortest_paths": shortest_paths,
        "summary": (
            f"Found {len(clusters)} cluster(s), "
            f"{len(central_nodes)} central node(s), "
            f"{len(suspicious_patterns)} suspicious pattern(s)"
        ),
        "graph_stats": {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "avg_connections": (
                sum(centrality_scores.values()) / len(entities) if entities else 0
            ),
        },
    }


# ---------------------------------------------------------------------------
# Route helpers
# ---------------------------------------------------------------------------


async def _load_graph(investigation_id: str) -> tuple:
    """Fetch entities and relationships for *investigation_id* from MongoDB."""
    entities = await db.entities.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    relationships = await db.relationships.find(
        {"investigation_id": investigation_id}, {"_id": 0}
    ).to_list(10000)
    return entities, relationships


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/{investigation_id}/graph/analyze")
async def analyze_investigation_graph(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Perform full graph intelligence analysis on an investigation."""
    await validate_api_key(x_api_key)

    entities, relationships = await _load_graph(investigation_id)
    analysis = analyze_graph_intelligence(entities, relationships)

    await create_timeline_event(
        investigation_id=investigation_id,
        event_type="graph_analysis",
        description=f"Graph analysis performed: {analysis['summary']}",
        metadata={
            "clusters_found": len(analysis["clusters"]),
            "patterns_found": len(analysis["suspicious_patterns"]),
        },
    )

    return {"success": True, "investigation_id": investigation_id, "analysis": analysis}


@router.get("/{investigation_id}/graph/clusters")
async def get_graph_clusters(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Return detected entity clusters for an investigation."""
    await validate_api_key(x_api_key)

    entities, relationships = await _load_graph(investigation_id)
    analysis = analyze_graph_intelligence(entities, relationships)

    return {
        "success": True,
        "clusters": analysis["clusters"],
        "central_nodes": analysis["central_nodes"],
    }


@router.get("/{investigation_id}/graph/suspicious-patterns")
async def get_suspicious_patterns(
    investigation_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Return suspicious patterns and shortest paths for an investigation."""
    await validate_api_key(x_api_key)

    entities, relationships = await _load_graph(investigation_id)
    analysis = analyze_graph_intelligence(entities, relationships)

    return {
        "success": True,
        "patterns": analysis["suspicious_patterns"],
        "paths": analysis["shortest_paths"],
    }
