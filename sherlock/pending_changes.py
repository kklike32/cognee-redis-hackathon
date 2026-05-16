from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .cache import invalidate_competitor_cache
from .config import Settings, get_settings
from .markdown_store import append_approved_update, apply_approved_change


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_changes(settings: Settings | None = None, path: Path | None = None) -> list[dict[str, Any]]:
    pending_path = path or (settings or get_settings()).pending_path
    if not pending_path.exists():
        return []
    raw = json.loads(pending_path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, list) else []


def save_changes(changes: list[dict[str, Any]], settings: Settings | None = None, path: Path | None = None) -> None:
    pending_path = path or (settings or get_settings()).pending_path
    pending_path.parent.mkdir(parents=True, exist_ok=True)
    pending_path.write_text(json.dumps(changes, indent=2), encoding="utf-8")


def pending_only(settings: Settings | None = None) -> list[dict[str, Any]]:
    return [change for change in load_changes(settings) if change.get("status") == "pending"]


def update_change_text(change_id: str, proposed_markdown: str, settings: Settings | None = None) -> dict[str, Any]:
    changes = load_changes(settings)
    for change in changes:
        if change.get("id") == change_id:
            change["proposed_markdown"] = proposed_markdown
            change["updated_at"] = _now()
            save_changes(changes, settings)
            return change
    raise ValueError(f"Pending change not found: {change_id}")


def approve_change(
    change_id: str,
    edited_markdown: str | None = None,
    settings: Settings | None = None,
    *,
    edited_text: str | None = None,
    path: Path | None = None,
    wiki_path: Path | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    changes = load_changes(settings=settings, path=path)
    for change in changes:
        if change.get("id") != change_id:
            continue
        final_markdown = (
            edited_text
            if edited_text is not None
            else edited_markdown
            if edited_markdown is not None
            else change.get("proposed_markdown")
            if change.get("proposed_markdown") is not None
            else str(change.get("proposed_text", ""))
        )

        if path is not None:
            target_wiki = wiki_path or settings.wiki_dir / "deel.md"
            append_approved_update(
                final_markdown,
                source_citation=str(change.get("source_citation", "")),
                path=target_wiki,
            )
        else:
            apply_approved_change(
                target_file=change["target_file"],
                target_section=change["target_section"],
                change_id=change_id,
                proposed_markdown=final_markdown,
                settings=settings,
            )

        if "proposed_markdown" in change:
            change["proposed_markdown"] = final_markdown
        if "proposed_text" in change:
            change["proposed_text"] = final_markdown
        change["status"] = "approved"
        change["resolved_at"] = _now()
        change["approved_at"] = _now()
        change["updated_at"] = _now()
        if path is None:
            invalidated = invalidate_competitor_cache(change.get("competitor", "deel"), settings=settings)
            change["cache_keys_invalidated"] = invalidated
        save_changes(changes, settings=settings, path=path)
        return change
    raise ValueError(f"Pending change not found: {change_id}")


def reject_change(change_id: str, settings: Settings | None = None, *, path: Path | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    changes = load_changes(settings=settings, path=path)
    for change in changes:
        if change.get("id") == change_id:
            change["status"] = "rejected"
            change["resolved_at"] = _now()
            change["rejected_at"] = _now()
            change["updated_at"] = _now()
            save_changes(changes, settings=settings, path=path)
            return change
    raise ValueError(f"Pending change not found: {change_id}")


def reset_pending(settings: Settings | None = None) -> list[dict[str, Any]]:
    changes = load_changes(settings)
    for change in changes:
        change["status"] = "pending"
        change.pop("resolved_at", None)
        change.pop("cache_keys_invalidated", None)
        change["updated_at"] = change.get("created_at") or _now()
    save_changes(changes, settings)
    return changes
