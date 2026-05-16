from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .markdown_store import append_approved_update

PENDING_PATH = Path("data") / "pending" / "pending_changes.json"
VALID_PRIORITIES = {"Critical", "Nice to have", "FYI"}
PENDING_STATUSES = {"pending", "approved", "rejected"}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_pending_changes() -> list[dict[str, Any]]:
    return [
        {
            "id": "deel-support-canada-uk-001",
            "competitor": "Deel",
            "priority": "Critical",
            "proposed_section": "Weaknesses to Attack",
            "proposed_text": (
                "Recent deal notes suggest prospects expanding into Canada and the UK "
                "are asking for more country-specific onboarding guidance. Position Oyster "
                "as the safer choice when the buyer has a lean people team and needs "
                "clear compliance handoffs after signature."
            ),
            "source_citation": "data/sources/gong_deel_transcript.md#L8-L14",
            "status": "pending",
        }
    ]


def ensure_pending_file(path: Path = PENDING_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        save_pending_changes(default_pending_changes(), path=path)


def load_pending_changes(path: Path = PENDING_PATH) -> list[dict[str, Any]]:
    ensure_pending_file(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if not isinstance(raw, list):
        return []
    return [normalize_change(change) for change in raw if isinstance(change, dict)]


def save_pending_changes(changes: list[dict[str, Any]], path: Path = PENDING_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(changes, indent=2, ensure_ascii=False), encoding="utf-8")


def upsert_pending_changes(
    new_changes: list[dict[str, Any]],
    *,
    path: Path = PENDING_PATH,
) -> list[dict[str, Any]]:
    existing = load_pending_changes(path=path)
    by_id = {change["id"]: change for change in existing if change.get("id")}

    for change in new_changes:
        normalized = normalize_change(change)
        change_id = normalized.get("id")
        if not change_id:
            continue
        current = by_id.get(change_id)
        if current and current.get("status") != "pending":
            continue
        by_id[change_id] = normalized

    merged = list(by_id.values())
    save_pending_changes(merged, path=path)
    return merged


def normalize_change(change: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(change)
    normalized.setdefault("id", "")
    normalized.setdefault("competitor", "Deel")
    normalized.setdefault("priority", "FYI")
    normalized.setdefault("proposed_section", "Recent Analyst-Approved Updates")
    normalized.setdefault("proposed_text", "")
    normalized.setdefault("source_citation", "")
    normalized.setdefault("status", "pending")
    if normalized["priority"] not in VALID_PRIORITIES:
        normalized["priority"] = "FYI"
    if normalized["status"] not in PENDING_STATUSES:
        normalized["status"] = "pending"
    return normalized


def find_change(change_id: str, changes: list[dict[str, Any]]) -> dict[str, Any]:
    for change in changes:
        if change.get("id") == change_id:
            return change
    raise KeyError(f"Pending change not found: {change_id}")


def approve_change(
    change_id: str,
    *,
    edited_text: str | None = None,
    path: Path = PENDING_PATH,
    wiki_path: Path | None = None,
) -> dict[str, Any]:
    changes = load_pending_changes(path=path)
    change = find_change(change_id, changes)
    if change.get("status") == "approved":
        save_pending_changes(changes, path=path)
        return change

    final_text = (edited_text if edited_text is not None else change.get("proposed_text", "")).strip()
    if wiki_path is None:
        append_approved_update(final_text, source_citation=str(change.get("source_citation", "")))
    else:
        append_approved_update(
            final_text,
            source_citation=str(change.get("source_citation", "")),
            path=wiki_path,
        )
    change["proposed_text"] = final_text
    change["status"] = "approved"
    change["approved_at"] = utc_timestamp()
    save_pending_changes(changes, path=path)
    return change


def reject_change(change_id: str, *, path: Path = PENDING_PATH) -> dict[str, Any]:
    changes = load_pending_changes(path=path)
    change = find_change(change_id, changes)
    change["status"] = "rejected"
    change["rejected_at"] = utc_timestamp()
    save_pending_changes(changes, path=path)
    return change


def invalidate_competitor_cache(competitor: str) -> dict[str, Any]:
    prefix = f"sherlock:brief:{competitor.strip().lower()}:"
    try:
        from app.redis_client import create_redis_client

        client = create_redis_client()
        keys = list(client.scan_iter(f"{prefix}*"))
        deleted = int(client.delete(*keys)) if keys else 0
        return {"ok": True, "deleted": deleted, "prefix": prefix}
    except Exception as exc:
        return {
            "ok": False,
            "deleted": 0,
            "prefix": prefix,
            "message": f"Cache invalidation skipped: {exc}",
        }
