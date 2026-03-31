"""Manual OSINT smoke test. Requires backend on localhost:8001. Not part of pytest.

Set API_KEY env var before running:
  Windows:  set API_KEY=your-key-here
  Linux/Mac: export API_KEY=your-key-here
"""

import json
import os

import requests

BASE = "http://localhost:8001"
_api_key = os.environ.get("API_KEY", "")
if not _api_key:
    raise SystemExit(
        "ERROR: API_KEY environment variable is not set. See script docstring."
    )
H = {"x-api-key": _api_key, "Content-Type": "application/json"}

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
