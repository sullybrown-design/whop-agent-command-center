"""Authenticated review workspace. Publishing integrations remain disconnected."""
from base64 import b64decode
from pathlib import Path
import os
import secrets
from typing import Literal
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator
from backend import store

app = FastAPI(title="Whop Agent Command Center", version="0.2.0")

@app.middleware("http")
async def auth_gate(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)
    scheme, param = get_authorization_scheme_param(request.headers.get("authorization", ""))
    try:
        decoded = b64decode(param, validate=True).decode("utf-8") if scheme.lower() == "basic" else ""
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeError):
        username, password = "", ""
    token = os.getenv("ADMIN_TOKEN", "")
    if not token or not (
        secrets.compare_digest(username.encode(), b"admin")
        and secrets.compare_digest(password.encode(), token.encode())
    ):
        return JSONResponse({"detail": "Authentication required"}, status_code=401,
                            headers={"WWW-Authenticate": 'Basic realm="Mission Control"'})
    return await call_next(request)

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

class JobRequest(BaseModel):
    campaign: str = Field(min_length=1, max_length=160)
    source_url: HttpUrl

    @field_validator("campaign")
    @classmethod
    def clean_campaign(cls, value):
        if not value.strip():
            raise ValueError("Campaign name cannot be blank")
        return value.strip()

class ReviewRequest(BaseModel):
    decision: Literal["approve", "rework"]
    reviewer: str = Field(min_length=1, max_length=160)
    permission_url: HttpUrl | None = None
    evidence: str = Field(default="", max_length=4000)
    platforms: list[Literal["youtube", "tiktok"]] = Field(default_factory=list)
    rights_checked: bool = False
    context_checked: bool = False
    captions_checked: bool = False
    quality_checked: bool = False

    @model_validator(mode="after")
    def require_evidence(self):
        self.reviewer = self.reviewer.strip()
        self.evidence = self.evidence.strip()
        self.platforms = sorted(set(self.platforms))
        if not self.reviewer:
            raise ValueError("Record the reviewer")
        if self.decision == "approve" and not (
            self.permission_url and self.evidence and self.platforms
            and self.rights_checked and self.context_checked
            and self.captions_checked and self.quality_checked
        ):
            raise ValueError("Approval requires a permission URL, evidence, a cleared platform and all review checks")
        if self.decision == "rework" and not self.evidence:
            raise ValueError("Describe what needs rework")
        return self

@app.get("/")
def home():
    return FileResponse(DASHBOARD)

@app.get("/api/health")
def health():
    with store.database() as db:
        db.execute("SELECT 1")
    return {"status": "ok", "mode": "review_workspace", "storage": "sqlite", "publishing_enabled": False}

@app.get("/api/agents")
def agents():
    return [{"name": name, "status": "not_connected"} for name in [
        "Campaign Scout", "Rights & Rules", "Clip Producer", "Quality Control", "Publisher", "Revenue Analyst"
    ]]

@app.get("/api/jobs")
def jobs():
    return store.list_jobs()

@app.post("/api/jobs", status_code=201)
def new_job(request: JobRequest):
    return store.create_job(request.campaign, str(request.source_url))

@app.get("/api/jobs/{job_id}/events")
def events(job_id: str):
    if store.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return store.list_events(job_id)

@app.post("/api/jobs/{job_id}/review")
def review(job_id: str, request: ReviewRequest):
    result = store.review_job(job_id, request.model_dump(mode="json"))
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return result

@app.post("/api/jobs/{job_id}/approve", deprecated=True)
def approve(job_id: str, request: ReviewRequest):
    if request.decision != "approve":
        raise HTTPException(status_code=422, detail="Use /review for a rework decision")
    return review(job_id, request)

from backend import local_bridge

class ResearchRequest(BaseModel):
    niche: str = Field(default="Streamer moments", min_length=1, max_length=200)
    topic: str = Field(default="", max_length=1500)
    direction: str = Field(default="", max_length=2500)

@app.get("/api/local/state")
def local_state():
    return local_bridge.snapshot()

@app.post("/api/local/research", status_code=202)
def local_research(request: ResearchRequest):
    try:
        result = local_bridge.start_research(request.model_dump())
        return {"id": result.get("id"), "status": result.get("status")}
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None

@app.get("/api/local/clips/{clip_id}/video")
def local_video(clip_id: str):
    base = local_bridge.root()
    path = local_bridge.video_path(base, clip_id) if base else None
    if path is None:
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(path, media_type="video/mp4", headers={"Cache-Control": "private, no-store"})
