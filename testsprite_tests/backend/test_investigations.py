"""
TestSprite — Investigation CRUD Tests
Validates create / read / update / delete lifecycle for investigations.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API_KEY = os.environ.get("API_KEY", "trace-analyst-secret-2026")
HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def investigation():
    """Create a fresh investigation for this test module and delete it afterward."""
    payload = {
        "name": f"TestSprite_{uuid.uuid4().hex[:8]}",
        "description": "Created by TestSprite automated test",
        "tags": ["testsprite", "automated"],
    }
    r = requests.post(f"{BASE_URL}/api/investigations", json=payload, headers=HEADERS)
    assert r.status_code == 200, r.text
    data = r.json()
    yield data
    # Teardown
    requests.delete(
        f"{BASE_URL}/api/investigations/{data['id']}", headers=HEADERS
    )


class TestInvestigationCRUD:
    def test_create_returns_id(self, investigation):
        assert "id" in investigation
        assert investigation["name"].startswith("TestSprite_")

    def test_list_includes_created(self, investigation):
        r = requests.get(f"{BASE_URL}/api/investigations", headers=HEADERS)
        assert r.status_code == 200
        ids = [i["id"] for i in r.json()]
        assert investigation["id"] in ids

    def test_get_by_id(self, investigation):
        r = requests.get(
            f"{BASE_URL}/api/investigations/{investigation['id']}", headers=HEADERS
        )
        assert r.status_code == 200
        assert r.json()["id"] == investigation["id"]

    def test_patch_name(self, investigation):
        new_name = f"Updated_{uuid.uuid4().hex[:6]}"
        r = requests.patch(
            f"{BASE_URL}/api/investigations/{investigation['id']}",
            json={"name": new_name},
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert r.json()["name"] == new_name

    def test_delete_removes_investigation(self):
        # Create a temporary investigation and delete it
        r = requests.post(
            f"{BASE_URL}/api/investigations",
            json={"name": "ToDelete", "description": ""},
            headers=HEADERS,
        )
        inv_id = r.json()["id"]
        del_r = requests.delete(
            f"{BASE_URL}/api/investigations/{inv_id}", headers=HEADERS
        )
        assert del_r.status_code == 200
        get_r = requests.get(
            f"{BASE_URL}/api/investigations/{inv_id}", headers=HEADERS
        )
        assert get_r.status_code == 404
