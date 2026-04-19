from fastapi.testclient import TestClient

from core.app import app

client = TestClient(app)


def test_healthcheck():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


def test_upload_non_pdf():
    import io
    resp = client.post(
        "/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert resp.status_code == 400
    assert "PDF" in resp.json()["detail"]


def test_status_not_found():
    resp = client.get("/status/nonexistent-id")
    assert resp.status_code == 404


def test_download_not_found():
    resp = client.get("/download/nonexistent-id")
    assert resp.status_code == 404
