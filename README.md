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
uvicorn backend.api:app --reload
```

Open http://localhost:8000 for Mission Control, or http://localhost:8000/docs for API documentation.

Run tests: `pip install -e '.[dev]' && pytest`.

## Architecture
- `backend/graph.py`: LangGraph workflow with explicit review gate
- `backend/api.py`: FastAPI status, job creation and approval endpoints
- `backend/store.py`: in-memory demo job store (restart clears jobs)
- `dashboard/index.html`: simple responsive Mission Control
- `integrations/`: interfaces for future official API integrations
- `tests/`: smoke tests

## Safety and platform rules
Use only footage you are authorized to clip. Follow each campaign's current terms and social-platform API rules. Do not automate fake engagement, duplicate spam, scraping behind access controls, or unsupported Whop submission endpoints. Human approval is required before any future publish action. Never commit credentials; use environment variables.

## Next milestones
1. Durable PostgreSQL job store and LangGraph checkpointer.
2. Verified campaign data ingestion with explicit source and rule tracking.
3. OpusClip integration and asset storage.
4. OAuth-based platform publishing, campaign compliance validation, deadline alerts.
5. Confirmed authorized Whop submission integration and actual payout reconciliation.
