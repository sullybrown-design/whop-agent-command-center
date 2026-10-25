"""Durable review jobs and activity history; no publishing side effects."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from uuid import uuid4
from backend.graph import graph

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def database():
    path = Path(os.getenv("DATABASE_PATH", "data/jobs.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, campaign TEXT NOT NULL, source_url TEXT NOT NULL,
                status TEXT NOT NULL, notes TEXT NOT NULL, created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, review TEXT
            );
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES jobs(id),
                kind TEXT NOT NULL, created_at TEXT NOT NULL, details TEXT NOT NULL
            );
        """)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def decode(row):
    if row is None:
        return None
    job = dict(row)
    job["notes"] = json.loads(job["notes"])
    job["review"] = json.loads(job["review"]) if job["review"] else None
    return job

def list_jobs():
    with database() as db:
        return [decode(row) for row in db.execute("SELECT * FROM jobs ORDER BY created_at DESC, id DESC")]

def get_job(job_id):
    with database() as db:
        return decode(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())

def list_events(job_id):
    with database() as db:
        return [{**dict(row), "details": json.loads(row["details"])} for row in db.execute(
            "SELECT * FROM events WHERE job_id=? ORDER BY id", (job_id,)
        )]

def create_job(campaign, source_url):
    job_id, timestamp = str(uuid4()), now()
    result = graph.invoke({"job_id": job_id, "campaign": campaign, "source_url": source_url, "approved": False})
    with database() as db:
        db.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)", (
            job_id, campaign, source_url, result["status"], json.dumps(result.get("notes", [])),
            timestamp, timestamp, None
        ))
        db.execute("INSERT INTO events(job_id,kind,created_at,details) VALUES (?,?,?,?)", (
            job_id, "created", timestamp, json.dumps({"status": result["status"]})
        ))
    return get_job(job_id)

def review_job(job_id, review):
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        job = decode(db.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone())
        if job is None:
            return None
        if job["review"] == review:
            return job
        status = "approved_for_future_processing" if review["decision"] == "approve" else "needs_rework"
        timestamp = now()
        notes = ["Review recorded. Publishing is not connected; no upload or post was created."]
        db.execute("UPDATE jobs SET status=?,notes=?,updated_at=?,review=? WHERE id=?", (
            status, json.dumps(notes), timestamp, json.dumps(review), job_id
        ))
        db.execute("INSERT INTO events(job_id,kind,created_at,details) VALUES (?,?,?,?)", (
            job_id, "reviewed", timestamp, json.dumps(review)
        ))
    return get_job(job_id)
