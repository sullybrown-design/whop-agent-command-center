# Whop Agent Command Center

An early-stage LangGraph content operations system for authorized creator clipping campaigns.

## Status
Working local foundation: LangGraph workflow, FastAPI endpoints, and a lightweight Mission Control UI. An optional local bridge reuses the running Clipforge DeepSeek worker and reads its backlog and saved schedules. OpusClip, direct social publishing, Whop API submissions, and earnings are **not connected** in this repository. No automatic publishing or submissions occur.

## Quick start
Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
export ADMIN_TOKEN="choose-a-private-admin-token"
uvicorn backend.api:app --reload
```

Open http://localhost:8000 for Mission Control, or http://localhost:8000/docs for API documentation. Sign in as admin with ADMIN_TOKEN. Keep the token private; without it, access is denied. On Windows PowerShell set $env:ADMIN_TOKEN instead of using export.

Run tests: `pip install -e '.[dev]' && pytest`.

## Architecture
- `backend/graph.py`: LangGraph workflow with explicit review gate
- `backend/api.py`: FastAPI status, job creation and approval endpoints
- `backend/store.py`: SQLite job store with persisted review records and activity history
- `dashboard/index.html`: simple responsive Mission Control
- `integrations/`: interfaces for future official API integrations
- `tests/`: smoke tests

## Safety and platform rules
Use only footage you are authorized to clip. Follow each campaign's current terms and social-platform API rules. Do not automate fake engagement, duplicate spam, scraping behind access controls, or unsupported Whop submission endpoints. A recorded reviewer decision with permission evidence is required before any future publish action. The reviewer can be the user or an authorized reviewing agent; this repository does not publish. Never commit credentials; use environment variables.

## Next milestones
1. Production PostgreSQL support and durable LangGraph checkpointing. SQLite review records are implemented; graph checkpoints are not.
2. Verified campaign data ingestion with explicit source and rule tracking.
3. OpusClip integration and asset storage.
4. OAuth-based platform publishing, campaign compliance validation, deadline alerts.
5. Confirmed authorized Whop submission integration and actual payout reconciliation.

## Saved jobs and reviews
Set DATABASE_PATH to a writable SQLite file (default: data/jobs.sqlite3). Jobs, permission URLs, cleared destinations, reviewer checks and activity events survive process restarts. POST /api/jobs/{id}/review accepts approve or rework. Approval requires evidence and all four checks; one cleared platform is sufficient. Repeating the same decision does not duplicate history. The older /approve route now requires the same evidence body.

SQLite is a single-instance foundation. On Render, use a persistent disk and point DATABASE_PATH to its mount, or adopt a managed database before relying on records across redeploys. The existing blueprint does not provision a disk automatically. No Whop, DeepSeek, rendering or social integrations are connected by this change.

## Connect the local operation
On Windows, run Start-Mission-Control.cmd. Choose a private dashboard password and sign in as admin. The launcher binds only to 127.0.0.1:4185. It detects the nearby Clipforge output folder in the Codex workspace, or set CLIPFORGE_ROOT to the absolute folder containing Clipforge data/jobs.json and data/operations.json.

The dashboard reads selected local job fields, clip packages and recovery metadata. It previews only MP4 files inside each package and does not expose worker keys, environment files or arbitrary filesystem paths. A research button calls the existing loopback worker; it may incur DeepSeek charges and does not publish. The worker must already be running with its own key configured. Saved schedules are labelled as recorded local evidence, not live platform status. Local files are not uploaded to GitHub.

The original Clipforge worker still has a fixed narration-oriented script prompt: treat its edit plan as a draft and discard replacement narration. This bridge does not change that worker or connect the Whop API.
