"""Local-only prototype API. Add authentication before any public deployment."""
from pathlib import Path
import os
import secrets
from fastapi import Depends, Header, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import JSONResponse
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, HttpUrl
from backend import store

security = HTTPBasic(auto_error=False)

def require_admin(credentials: HTTPBasicCredentials | None = Depends(security)):
    token = os.getenv("ADMIN_TOKEN", "")
    if not token or credentials is None or not (secrets.compare_digest(credentials.username, "admin") and secrets.compare_digest(credentials.password, token)):
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Basic"})

app = FastAPI(title="Whop Agent Command Center", version="0.1.0")
@app.middleware("http")
async def auth_gate(request: Request, call_next):
    if request.url.path == "/api/health":
        return await call_next(request)
    from fastapi.security.utils import get_authorization_scheme_param
    from base64 import b64decode
    auth = request.headers.get("authorization", "")
    scheme, param = get_authorization_scheme_param(auth)
    try:
        decoded = b64decode(param, validate=True).decode("utf-8") if scheme.lower() == "basic" else ""
        username, password = decoded.split(":", 1)
    except (ValueError, UnicodeError):
        username, password = "", ""
    token = os.getenv("ADMIN_TOKEN", "")
    if not token or not (secrets.compare_digest(username, "admin") and secrets.compare_digest(password, token)):
        return JSONResponse({"detail": "Authentication required"}, status_code=401, headers={"WWW-Authenticate": 'Basic realm="Mission Control"'})
    return await call_next(request)

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"

class JobRequest(BaseModel):
    campaign: str = Field(min_length=1, max_length=160)
    source_url: HttpUrl

@app.get("/")
def home():
    return FileResponse(DASHBOARD)

@app.get("/api/health", dependencies=[])
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
