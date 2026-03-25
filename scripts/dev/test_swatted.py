"""Manual OSINT smoke test. Requires backend on localhost:8001. Not part of pytest."""
import requests
import json

BASE = "http://localhost:8001"
H = {"x-api-key": "trace-analyst-secret-2026", "Content-Type": "application/json"}

r = requests.post(
    f"{BASE}/api/osint/search",
    json={"query": "test@gmail.com", "search_type": "email"},
    headers=H,
    timeout=60,
)
print(f"Status: {r.status_code}")
data = r.json()
print(f"Live: {data.get('live_data')} | Results: {len(data.get('results', []))}")
for res in data.get("results", []):
    src = res.get("source", "?")
    d = res.get("data")
    preview = json.dumps(d)[:150] if isinstance(d, (dict, list)) else str(d)[:150]
    print(f"  [{src}] {preview}")
