"""
TestSprite — Authentication Tests
Validates API key gate: valid key accepted, invalid/missing keys rejected.
"""
import pytest
import requests
import os

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001").rstrip("/")
API_KEY = os.environ.get("API_KEY", "trace-analyst-secret-2026")


def headers(key=API_KEY):
    return {"x-api-key": key, "Content-Type": "application/json"}


class TestAuthentication:
    """Verify the x-api-key header gate on all protected routes."""

    def test_root_with_valid_key(self):
        r = requests.get(f"{BASE_URL}/api/", headers=headers())
        assert r.status_code == 200
        data = r.json()
        assert "message" in data

    def test_root_with_invalid_key_is_rejected(self):
        r = requests.get(f"{BASE_URL}/api/", headers=headers("wrong-key"))
        assert r.status_code == 403

    def test_validate_endpoint_accepts_correct_key(self):
        r = requests.post(f"{BASE_URL}/api/auth/validate", headers=headers())
        assert r.status_code == 200
        assert r.json().get("valid") is True

    def test_validate_endpoint_rejects_wrong_key(self):
        r = requests.post(
            f"{BASE_URL}/api/auth/validate", headers=headers("bad-key")
        )
        assert r.status_code == 200
        assert r.json().get("valid") is False

    def test_missing_api_key_returns_403(self):
        r = requests.get(f"{BASE_URL}/api/")
        assert r.status_code == 403
