"""Narrow local bridge. Reuses the running worker without reading its credentials."""
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

WORKER = "http://127.0.0.1:4180"

def mapping(value):
    return value if isinstance(value, dict) else {}

def sequence(value):
    return value if isinstance(value, list) else []

def root():
    value = os.getenv("CLIPFORGE_ROOT")
    return Path(value).resolve() if value else None

def read_json(path, default):
    try:
        if path.stat().st_size > 8 * 1024 * 1024:
            return default
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default

def worker(path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Origin": WORKER}
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = Request(WORKER + path, data=data, headers=headers)
    try:
        with urlopen(request, timeout=3) as response:
            return json.loads(response.read(8 * 1024 * 1024))
    except HTTPError as error:
        try:
            detail = json.loads(error.read(4000)).get("error", "Worker rejected the request")
        except ValueError:
            detail = "Worker rejected the request"
        raise ValueError(str(detail)) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise ValueError("Local Clipforge worker is unavailable") from None

def safe_url(value):
    return value if isinstance(value, str) and urlparse(value).scheme in ("https", "http") else None

def packages(base):
    folder = base.parent / "Clip-Receipts"
    if not folder.is_dir():
        return []
    items = []
    for record in sorted(folder.glob("*/Queue-entry.json")):
        if not record.resolve().is_relative_to(folder.resolve()):
            continue
        q = read_json(record, {})
        if not isinstance(q, dict):
            continue
        slug = record.parent.name
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", slug):
            continue
        item = {"id": slug, "title": str(q.get("title", slug))[:500],
                "status": str(q.get("status", "unknown"))[:100],
                "platforms": [p for p in sequence(q.get("platforms", [])) if p in ("youtube", "tiktok")],
                "duration": q.get("actualDurationSeconds", q.get("durationSeconds")),
                "source_url": safe_url(q.get("sourceUrl")),
                "permission_url": safe_url(q.get("permissionUrl")),
                "youtube_url": safe_url(q.get("youtubeUrl")),
                "scheduled_for": q.get("scheduledFor"),
                "scheduled": q.get("scheduled") is True,
                "published": q.get("published") is True,
                "video_url": None}
        if video_path(base, slug):
            item["video_url"] = "/api/local/clips/" + slug + "/video"
        items.append(item)
    return items

def video_path(base, slug):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", slug):
        return None
    folder = (base.parent / "Clip-Receipts" / slug).resolve()
    media_root = (base.parent / "Clip-Receipts").resolve()
    if not folder.is_relative_to(media_root):
        return None
    q = mapping(read_json(folder / "Queue-entry.json", {}))
    try:
        video = Path(q.get("video", "")).resolve()
        if video.is_relative_to(folder) and video.is_file() and video.suffix.lower() == ".mp4":
            return video
    except (OSError, TypeError, ValueError):
        pass
    return None

def snapshot():
    base = root()
    if base is None:
        return {"configured": False, "worker": {"connected": False},
                "jobs": [], "clips": [], "slots": [], "recovery": {},
                "notice": "Set CLIPFORGE_ROOT to connect the existing local operation."}
    try:
        status = mapping(worker("/api/status"))
        worker_status = {"connected": status.get("metaConfigured") is True,
                         "online": True, "provider": status.get("provider"),
                         "model": status.get("model")}
    except ValueError:
        worker_status = {"connected": False, "online": False}
    raw_jobs = read_json(base / "data/jobs.json", [])
    jobs = []
    for j in raw_jobs[:50] if isinstance(raw_jobs, list) else []:
        if not isinstance(j, dict):
            continue
        result = mapping(j.get("result"))
        brief = mapping(j.get("input"))
        jobs.append({"id": j.get("id"), "status": j.get("status"), "created": j.get("created"),
                     "niche": str(brief.get("niche", ""))[:200],
                     "topic": str(brief.get("topic", ""))[:4000],
                     "research": str(result.get("research", ""))[:30000],
                     "plan": str(result.get("script", ""))[:30000],
                     "review": str(result.get("review", ""))[:30000],
                     "error": str(j.get("error", ""))[:1000]})
    ledger = mapping(read_json(base / "data/operations.json", {}))
    slots = []
    for s in sequence(ledger.get("slots"))[:100]:
        if not isinstance(s, dict):
            continue
        deliveries = mapping(s.get("deliveries"))
        slots.append({"id": s.get("id"), "date": s.get("date"), "time": s.get("time"),
                      "title": str(s.get("title", ""))[:500],
                      "approved": s.get("approved") is True,
                      "deliveries": {p: {"status": mapping(deliveries.get(p)).get("status"),
                                          "url": safe_url(mapping(deliveries.get(p)).get("url"))}
                                     for p in ("youtube", "tiktok")}})
    saved = mapping(read_json(base.parent.parent / "work/clipreceipts-production-state.json", {}))
    recovery = {"resume_on_usage_return": saved.get("resumeOnUsageReturn") is True,
                "next_action": str(saved.get("nextAction", ""))[:2000]}
    return {"configured": True, "worker": worker_status, "jobs": jobs, "clips": packages(base),
            "slots": slots, "recovery": recovery,
            "notice": "Recorded local state, not a fresh platform check. Scheduling/publishing still uses the authorized platform workflow."}

def start_research(brief):
    if root() is None:
        raise ValueError("Configure the local Clipforge connection first")
    instruction = ("Use real streamer footage and original speech, 60–90 seconds. "
                   "Require primary documented clipping permission; clear each platform separately. "
                   "No synthetic narration, invented captions/timestamps, paid sources or misleading edits. "
                   "A public video or third-party clipping directory is not permission. "
                   "Codex performs final review. Research only; do not publish. ")
    return worker("/api/run", {**brief, "direction": instruction + brief.get("direction", "")})
