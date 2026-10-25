import importlib
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from backend import store
from backend.api import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("ADMIN_TOKEN", "test-only-token")
    with TestClient(app) as session:
        session.auth = ("admin", "test-only-token")
        yield session

def candidate(client):
    response = client.post("/api/jobs", json={"campaign": "Test campaign", "source_url": "https://example.com/source"})
    assert response.status_code == 201
    return response.json()

def evidence(**changes):
    return {"decision": "approve", "reviewer": "Test reviewer",
            "permission_url": "https://example.com/permission",
            "evidence": "Test fixture: creator allows edited excerpts on YouTube with attribution.",
            "platforms": ["youtube"], "rights_checked": True, "context_checked": True,
            "captions_checked": True, "quality_checked": True, **changes}

def test_auth_and_health(client):
    assert client.get("/api/health", auth=("bad", "bad")).json()["storage"] == "sqlite"
    assert client.get("/api/jobs", auth=("bad", "bad")).status_code == 401
    assert client.post("/api/jobs", auth=("bad", "bad"), json={}).status_code == 401
    assert client.get("/api/jobs", auth=("nonascii-ñ", "bad")).status_code == 401

def test_jobs_survive_store_reload(client):
    job = candidate(client)
    importlib.reload(store)
    assert client.get("/api/jobs").json()[0]["id"] == job["id"]
    assert store.get_job(job["id"])["status"] == "awaiting_approval"
    assert len(store.list_events(job["id"])) == 1

@pytest.mark.parametrize("change", [
    {"permission_url": None}, {"evidence": " "}, {"platforms": []},
    {"rights_checked": False}, {"context_checked": False},
    {"captions_checked": False}, {"quality_checked": False}, {"reviewer": " "},
    {"platforms": ["unsupported"]}, {"permission_url": "javascript:alert(1)"}
])
def test_incomplete_approval_is_rejected(client, change):
    job = candidate(client)
    assert client.post(f"/api/jobs/{job['id']}/review", json=evidence(**change)).status_code == 422
    assert store.get_job(job["id"])["status"] == "awaiting_approval"
    assert len(store.list_events(job["id"])) == 1

def test_single_platform_review_and_rework(client):
    job = candidate(client)
    path = f"/api/jobs/{job['id']}/review"
    result = client.post(path, json=evidence())
    assert result.status_code == 200
    assert result.json()["review"]["platforms"] == ["youtube"]
    assert result.json()["status"] == "approved_for_future_processing"
    assert client.get("/api/health").json()["publishing_enabled"] is False
    assert client.post(path, json=evidence()).status_code == 200
    assert len(store.list_events(job["id"])) == 2
    result = client.post(path, json={"decision": "rework", "reviewer": "Reviewer", "evidence": "Captions need a correction."})
    assert result.json()["status"] == "needs_rework"
    events = client.get(f"/api/jobs/{job['id']}/events").json()
    assert [e["kind"] for e in events] == ["created", "reviewed", "reviewed"]
    assert events[-1]["details"]["decision"] == "rework"

def test_legacy_approve_cannot_bypass_review(client):
    job = candidate(client)
    assert client.post(f"/api/jobs/{job['id']}/approve").status_code == 422
    assert client.post(f"/api/jobs/{job['id']}/approve", json=evidence(evidence="")).status_code == 422

def test_not_found_and_blank_campaign(client):
    assert client.get("/api/jobs/missing/events").status_code == 404
    assert client.post("/api/jobs/missing/review", json=evidence()).status_code == 404
    assert client.post("/api/jobs", json={"campaign": " ", "source_url": "https://example.com"}).status_code == 422

def test_concurrent_duplicate_reviews_have_one_event(client):
    job = candidate(client)
    review = evidence()
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: store.review_job(job["id"], review), range(4)))
    assert all(r["status"] == "approved_for_future_processing" for r in results)
    assert len(store.list_events(job["id"])) == 2
