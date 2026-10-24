import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

client = TestClient(app)
AUTH_HEADERS = {"X-Device-Token": settings.device_pairing_token}


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_desktop_status_endpoint():
    res = client.get("/api/v1/desktop/status")
    assert res.status_code == 200
    data = res.json()
    assert "operating_system" in data
    assert "backend_connected" in data
    assert data["backend_connected"] is True


def test_desktop_screen_endpoint():
    res = client.get("/api/v1/desktop/screen")
    assert res.status_code == 200
    data = res.json()
    assert "base64_preview" in data
    assert "width" in data


def test_task_creation_unauthorized():
    # Attempting to submit task without token
    res = client.post("/api/v1/tasks", json={"request": "Take a screenshot"})
    assert res.status_code == 401


def test_task_creation_and_lifecycle():
    # Submit task with valid token
    res = client.post(
        "/api/v1/tasks",
        json={"request": "Take a screenshot and explain what is on my screen"},
        headers=AUTH_HEADERS
    )
    assert res.status_code == 200
    data = res.json()
    assert "task_id" in data
    task_id = data["task_id"]

    # Check detail
    res_detail = client.get(f"/api/v1/tasks/{task_id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["task_id"] == task_id


def test_emergency_stop_cancel():
    res = client.post(
        "/api/v1/tasks",
        json={"request": "Open Terminal and run the tests in my selected project"},
        headers=AUTH_HEADERS
    )
    task_id = res.json()["task_id"]

    # Cancel task immediately
    cancel_res = client.post(f"/api/v1/tasks/{task_id}/cancel", headers=AUTH_HEADERS)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["cancelled"] is True


def test_voice_transcribe_empty():
    res = client.post(
        "/api/v1/voice/transcribe",
        files={"file": ("empty.wav", b"", "audio/wav")},
        headers=AUTH_HEADERS
    )
    assert res.status_code == 400
