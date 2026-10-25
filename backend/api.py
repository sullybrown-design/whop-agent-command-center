"""Local-only prototype API. Add authentication before any public deployment."""
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from backend import store

app = FastAPI(title="Whop Agent Command Center", version="0.1.0")
DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

class JobRequest(BaseModel):
    campaign: str = Field(min_length=1, max_length=160)
    source_url: HttpUrl

@app.get("/")
def home():
    return FileResponse(DASHBOARD)

@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "prototype", "publishing_enabled": False}

@app.get("/api/agents")
def agents():
    return [{"name": name, "status": "not_connected"} for name in ["Campaign Scout", "Rights & Rules", "Clip Producer", "Quality Control", "Publisher", "Revenue Analyst"]]

@app.get("/api/jobs")
def jobs():
    return store.list_jobs()

@app.post("/api/jobs", status_code=201)
def new_job(request: JobRequest):
    return store.create_job(request.campaign, str(request.source_url))

@app.post("/api/jobs/{job_id}/approve")
def approve(job_id: str):
    result = store.approve_job(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result
