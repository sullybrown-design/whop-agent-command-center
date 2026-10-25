"""Ephemeral local demo store. Replace with durable database before production."""
from threading import Lock
from uuid import uuid4
from datetime import datetime, timezone
from backend.graph import graph

_lock = Lock()
_jobs: dict[str, dict] = {}

def list_jobs() -> list[dict]:
    with _lock:
        return list(reversed(list(_jobs.values())))

def create_job(campaign: str, source_url: str) -> dict:
    job_id = str(uuid4())
    result = graph.invoke({"job_id": job_id, "campaign": campaign, "source_url": source_url, "approved": False})
    job = {"id": job_id, "campaign": campaign, "source_url": source_url, "status": result["status"], "notes": result.get("notes", []), "created_at": datetime.now(timezone.utc).isoformat()}
    with _lock:
        _jobs[job_id] = job
    return job

def approve_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            return None
        result = graph.invoke({"job_id": job_id, "campaign": job["campaign"], "source_url": job["source_url"], "approved": True})
        job["status"] = result["status"]
        job["notes"] = result.get("notes", [])
        return dict(job)
