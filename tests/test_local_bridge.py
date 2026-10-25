import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.api import app
from backend import local_bridge

@pytest.fixture
def setup(tmp_path, monkeypatch):
    base = tmp_path / "outputs" / "Clipforge"
    (base / "data").mkdir(parents=True)
    monkeypatch.setenv("CLIPFORGE_ROOT", str(base))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("ADMIN_TOKEN", "test-only-token")
    monkeypatch.setattr(local_bridge, "worker", lambda *args: {"metaConfigured": True, "provider": "deepseek", "model": "test"})
    with TestClient(app) as client:
        client.auth = ("admin", "test-only-token")
        yield client, base, tmp_path

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")

def test_snapshot_records_are_not_live_platform_claims(setup):
    client, base, tmp = setup
    (base / ".env").write_text("DEEPSEEK_API_KEY=NEVER_EXPOSE_THIS", encoding="utf-8")
    write(base / "data/jobs.json", [{"id": "run", "status": "awaiting_human_review",
          "DEEPSEEK_API_KEY": "NEVER_EXPOSE_THIS", "input": {"niche": "streamers"},
          "result": {"research": "One lead", "script": "Verify", "review": "Needs evidence"}}])
    folder = base.parent / "Clip-Receipts" / "Backlog-01"
    folder.mkdir(parents=True)
    video = folder / "clip.mp4"
    video.write_bytes(b"test-media")
    write(folder / "Queue-entry.json", {"title": "Example", "scheduled": True,
          "scheduledFor": "2026-10-25T12:30:00-04:00", "video": str(video),
          "platforms": ["youtube"], "youtubeUrl": "https://www.youtube.com/shorts/example",
          "permissionUrl": "javascript:alert(1)"})
    write(tmp / "work/clipreceipts-production-state.json", {"resumeOnUsageReturn": True, "nextAction": "Continue"})
    response = client.get("/api/local/state")
    assert response.status_code == 200
    state = response.json()
    assert state["worker"]["connected"] is True
    assert "not a fresh platform check" in state["notice"]
    assert state["clips"][0]["scheduled"] is True
    assert state["clips"][0]["permission_url"] is None
    assert state["recovery"]["resume_on_usage_return"] is True
    assert "NEVER_EXPOSE_THIS" not in response.text
    assert str(tmp) not in response.text
    assert client.get(state["clips"][0]["video_url"]).content == b"test-media"

def test_media_does_not_serve_files_outside_package(setup):
    client, base, tmp = setup
    secret = tmp / "secret.mp4"
    secret.write_bytes(b"private")
    write(base.parent / "Clip-Receipts" / "Unsafe" / "Queue-entry.json", {"video": str(secret)})
    state = client.get("/api/local/state").json()
    assert state["clips"][0]["video_url"] is None
    assert client.get("/api/local/clips/Unsafe/video").status_code == 404
    assert local_bridge.video_path(base, "../Unsafe") is None

def test_local_routes_are_authenticated(setup):
    client, _, _ = setup
    assert client.get("/api/local/state", auth=("bad", "bad")).status_code == 401
    assert client.post("/api/local/research", json={}, auth=("bad", "bad")).status_code == 401

def test_start_research_reuses_worker_with_constraints(setup, monkeypatch):
    client, _, _ = setup
    captured = []
    def worker(path, payload=None):
        captured.append((path, payload))
        return {"id": "new-job", "status": "running"}
    monkeypatch.setattr(local_bridge, "worker", worker)
    response = client.post("/api/local/research", json={"topic": "Funny moments"})
    assert response.status_code == 202
    assert captured[0][0] == "/api/run"
    assert "primary documented clipping permission" in captured[0][1]["direction"]
    assert "do not publish" in captured[0][1]["direction"]
    assert response.json() == {"id": "new-job", "status": "running"}

def test_disconnected_and_missing_files_are_not_failures(setup, monkeypatch):
    client, base, _ = setup
    monkeypatch.delenv("CLIPFORGE_ROOT")
    assert client.get("/api/local/state").json()["configured"] is False
    assert client.post("/api/local/research", json={}).status_code == 409
    monkeypatch.setenv("CLIPFORGE_ROOT", str(base))
    def offline(*args):
        raise ValueError("offline")
    monkeypatch.setattr(local_bridge, "worker", offline)
    state = client.get("/api/local/state").json()
    assert state["worker"]["online"] is False
    assert state["jobs"] == []
    assert state["clips"] == []
    assert client.post("/api/local/research", json={}).status_code == 409

def test_partial_or_malformed_records_do_not_break_snapshot(setup):
    client, base, tmp = setup
    write(base / 'data/jobs.json', [None, {'id': 'bad', 'input': [], 'result': []}])
    write(base / 'data/operations.json', {'slots': [None, {'deliveries': {'youtube': None}}]})
    write(tmp / 'work/clipreceipts-production-state.json', None)
    write(base.parent / 'Clip-Receipts' / 'Broken' / 'Queue-entry.json', None)
    assert client.get('/api/local/state').status_code == 200
    assert client.get('/api/local/clips/Broken/video').status_code == 404
