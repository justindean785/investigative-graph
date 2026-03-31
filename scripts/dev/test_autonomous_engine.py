"""
Manual autonomous-engine exercise. Requires backend + Mongo. Not part of pytest.
Run: python scripts/dev/test_autonomous_engine.py

Set API_KEY env var before running:
  Windows:  set API_KEY=your-key-here
  Linux/Mac: export API_KEY=your-key-here
"""

import os
import time

import requests

API_URL = "http://localhost:8001/api"
API_KEY = os.environ.get("API_KEY", "")
if not API_KEY:
    raise SystemExit(
        "ERROR: API_KEY environment variable is not set. See script docstring."
    )
HEADERS = {"x-api-key": API_KEY}


def create_test_investigation():
    """Create a test investigation."""
    response = requests.post(
        f"{API_URL}/investigations",
        headers=HEADERS,
        json={
            "name": "Auto Engine Test",
            "description": "Testing autonomous investigation engine",
            "tags": ["test", "auto"],
        },
    )
    response.raise_for_status()
    return response.json()["id"]


def start_investigation(inv_id, seed_input):
    """Start autonomous investigation."""
    response = requests.post(
        f"{API_URL}/investigations/{inv_id}/auto-investigate",
        headers=HEADERS,
        json={
            "seed_input": seed_input,
            "max_depth": 5,
            "max_entities": 100,
            "confidence_threshold": 0.3,
        },
    )
    response.raise_for_status()
    return response.json()


def check_status(inv_id):
    """Check investigation status."""
    response = requests.get(
        f"{API_URL}/investigations/{inv_id}/auto-status",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_entities(inv_id):
    """Get discovered entities."""
    response = requests.get(
        f"{API_URL}/investigations/{inv_id}/entities",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def get_relationships(inv_id):
    """Get created relationships."""
    response = requests.get(
        f"{API_URL}/investigations/{inv_id}/relationships",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response.json()


def main():
    print("=" * 60)
    print("AUTONOMOUS INVESTIGATION ENGINE TEST")
    print("=" * 60)

    print("\n[1/5] Creating test investigation...")
    inv_id = create_test_investigation()
    print(f"[OK] Investigation ID: {inv_id}")

    print("\n[2/5] Starting autonomous investigation...")
    seed_input = "+19168658384 Sacramento possible gmail telegram"
    print(f"Seed input: {seed_input}")

    result = start_investigation(inv_id, seed_input)
    print("Investigation started")
    print(f"Stream URL: {result['stream_url']}")

    print("\n[3/5] Monitoring investigation progress...")
    print("─" * 60)

    last_processed = 0
    last_discovered = 0
    start_time = time.time()

    while True:
        time.sleep(2)

        status = check_status(inv_id)

        if status["status"] == "not_started":
            print("⚠ Investigation not started yet")
            continue

        if (
            status["processed_count"] != last_processed
            or status["entities_discovered"] != last_discovered
        ):
            print(f"Status: {status['status']}")
            print(f"  Processed: {status['processed_count']}")
            print(f"  Discovered: {status['entities_discovered']}")
            print(f"  Depth: {status['current_depth']}/{status['max_depth']}")
            print(f"  Queue: {status.get('queue_size', 0)}")
            print()

            last_processed = status["processed_count"]
            last_discovered = status["entities_discovered"]

        if status["status"] in ["completed", "error"]:
            print(f"Investigation {status['status']}")
            if status.get("error"):
                print(f"  Error: {status['error']}")
            break

        if time.time() - start_time > 120:
            print("⚠ Timeout - investigation taking too long")
            break

    print("\n[4/5] Fetching results...")
    entities = get_entities(inv_id)
    relationships = get_relationships(inv_id)

    print(f"Found {len(entities)} entities")
    print(f"Found {len(relationships)} relationships")

    print("\n[5/5] Analysis...")
    print("─" * 60)

    entity_types = {}
    for ent in entities:
        etype = ent["entity_type"]
        entity_types[etype] = entity_types.get(etype, 0) + 1

    print("Entity Types:")
    for etype, count in sorted(entity_types.items()):
        print(f"  {etype}: {count}")

    print("\nSample Entities:")
    for ent in entities[:5]:
        print(
            f"  [{ent['entity_type']}] {ent['value']} (confidence: {ent.get('confidence', 0):.2f})"
        )

    rel_types = {}
    for rel in relationships:
        rtype = rel["relationship_type"]
        rel_types[rtype] = rel_types.get(rtype, 0) + 1

    print("\nRelationship Types:")
    for rtype, count in sorted(rel_types.items()):
        print(f"  {rtype}: {count}")

    if entities:
        max_depth_reached = max(
            (e.get("metadata", {}).get("depth", 0) for e in entities), default=0
        )
        print(f"\nMax Pivot Depth: {max_depth_reached}")

    derived_entities = [
        e
        for e in entities
        if e.get("sources")
        and any("derived_from" in str(s) for s in e.get("sources", []))
    ]
    print(f"Derived Entities: {len(derived_entities)}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    print("\nVALIDATION CHECKS:")
    checks = {
        "Entities extracted": len(entities) > 1,
        "Multi-type entities": len(entity_types) > 1,
        "Relationships created": len(relationships) > 0,
        "Pivoting occurred": last_processed > 1,
        "High confidence entities": any(e.get("confidence", 0) > 0.5 for e in entities),
    }

    for check, passed in checks.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {check}")

    if all(checks.values()):
        print("\nALL CHECKS PASSED - Engine is functional!")
    else:
        print("\nSOME CHECKS FAILED - Review needed")

    return inv_id


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback

        traceback.print_exc()
