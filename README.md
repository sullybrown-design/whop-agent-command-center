# Whop Agent Command Center

An early-stage LangGraph content operations system for authorized creator clipping campaigns.

## Status
Working local foundation: LangGraph workflow, FastAPI endpoints, and a lightweight Mission Control UI. Campaign discovery, OpusClip, social publishing, Whop submissions, and earnings are **not connected** yet. No automatic publishing or submissions occur.

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
