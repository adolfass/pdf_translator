import io

import pytest
from fastapi.testclient import TestClient

from core.app import app
from shared.auth import create_access_token


@pytest.fixture(autouse=True)
def disable_auth():
    from shared import config
    original = config.settings.auth_enabled
    config.settings.auth_enabled = False
    yield
    config.settings.auth_enabled = original


client = TestClient(app)


def test_healthcheck():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_upload_non_pdf(disable_auth):
    resp = client.post(
        "/api/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_upload_no_file(disable_auth):
    resp = client.post("/api/upload")
    assert resp.status_code == 422


def test_status_not_found(disable_auth):
    resp = client.get("/api/status/nonexistent-id")
    assert resp.status_code == 404


def test_download_not_found(disable_auth):
    resp = client.get("/api/download/nonexistent-id")
    assert resp.status_code == 404


def test_auth_telegram_invalid(disable_auth):
    resp = client.post("/api/auth/telegram", params={"id": "123", "hash": "bad"})
    assert resp.status_code == 401


def test_admin_stats_forbidden(disable_auth):
    resp = client.get("/api/admin/stats")
    assert resp.status_code == 200
