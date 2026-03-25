"""
TestSprite — Entity Management Tests
Validates entity create / read / delete + entity extraction endpoint.
"""
import pytest
import requests
import os
import uuid

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API_KEY = os.environ.get("API_KEY", "trace-analyst-secret-2026")
HEADERS = {"x-api-key": API_KEY, "Content-Type": "application/json"}


@pytest.fixture(scope="module")
def investigation_id():
    r = requests.post(
        f"{BASE_URL}/api/investigations",
        json={"name": f"TS_Entities_{uuid.uuid4().hex[:6]}", "description": ""},
        headers=HEADERS,
    )
    assert r.status_code == 200, r.text
    inv_id = r.json()["id"]
    yield inv_id
    requests.delete(f"{BASE_URL}/api/investigations/{inv_id}", headers=HEADERS)


class TestEntityManagement:
    def test_add_email_entity(self, investigation_id):
        r = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json={"kind": "email", "value": "suspect@example.com", "confidence": 0.9},
            headers=HEADERS,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["kind"] == "email"
        assert data["value"] == "suspect@example.com"

    def test_list_entities_not_empty(self, investigation_id):
        r = requests.get(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            headers=HEADERS,
        )
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_extract_entities_from_text(self):
        payload = {
            "text": (
                "Contact admin@darkweb.onion or visit http://evil.example.com. "
                "Wallet: 1BpEi6DfDAUFd542184yiuM3jEyXme2bank"
            )
        }
        r = requests.post(
            f"{BASE_URL}/api/extract/entities", json=payload, headers=HEADERS
        )
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["extracted_count"] >= 1

    def test_delete_entity(self, investigation_id):
        # Add then delete
        r = requests.post(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities",
            json={"kind": "domain", "value": "to-delete.com", "confidence": 0.5},
            headers=HEADERS,
        )
        eid = r.json()["id"]
        del_r = requests.delete(
            f"{BASE_URL}/api/investigations/{investigation_id}/entities/{eid}",
            headers=HEADERS,
        )
        assert del_r.status_code == 200
