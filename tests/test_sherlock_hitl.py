from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from sherlock.markdown_store import append_approved_update
from sherlock.pending_changes import approve_change, reject_change


def _scratch_dir() -> Path:
    path = Path(".cache") / "test-scratch" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def _pending_payload() -> list[dict[str, str]]:
    return [
        {
            "id": "change-1",
            "competitor": "Deel",
            "priority": "Critical",
            "proposed_section": "Weaknesses to Attack",
            "proposed_text": "Original proposed text.",
            "source_citation": "data/sources/test.md#L1",
            "status": "pending",
        }
    ]


def test_append_approved_update_adds_timestamped_section():
    scratch = _scratch_dir()
    try:
        wiki_path = scratch / "deel.md"
        wiki_path.write_text("# Deel Battle Card\n\n## Sources\n- source\n", encoding="utf-8")

        updated = append_approved_update(
            "Approved update text.",
            source_citation="data/sources/test.md#L1",
            path=wiki_path,
            timestamp="2026-05-16T12:00:00+00:00",
        )

        assert "## Recent Analyst-Approved Updates" in updated
        assert "### 2026-05-16T12:00:00+00:00" in updated
        assert "Approved update text." in updated
        assert "data/sources/test.md#L1" in updated
    finally:
        _cleanup(scratch)


def test_approve_change_mutates_wiki_and_marks_approved():
    scratch = _scratch_dir()
    try:
        pending_path = scratch / "pending_changes.json"
        pending_path.write_text(json.dumps(_pending_payload()), encoding="utf-8")
        wiki_path = scratch / "deel.md"
        wiki_path.write_text("# Deel Battle Card\n", encoding="utf-8")

        approved = approve_change(
            "change-1",
            edited_text="Edited analyst text.",
            path=pending_path,
            wiki_path=wiki_path,
        )

        wiki_text = wiki_path.read_text(encoding="utf-8")
        stored = json.loads(pending_path.read_text(encoding="utf-8"))[0]
        assert approved["status"] == "approved"
        assert stored["status"] == "approved"
        assert stored["approved_at"]
        assert "Edited analyst text." in wiki_text
    finally:
        _cleanup(scratch)


def test_reject_change_does_not_mutate_wiki():
    scratch = _scratch_dir()
    try:
        pending_path = scratch / "pending_changes.json"
        pending_path.write_text(json.dumps(_pending_payload()), encoding="utf-8")
        wiki_path = scratch / "deel.md"
        original = "# Deel Battle Card\n"
        wiki_path.write_text(original, encoding="utf-8")

        rejected = reject_change("change-1", path=pending_path)

        stored = json.loads(pending_path.read_text(encoding="utf-8"))[0]
        assert rejected["status"] == "rejected"
        assert stored["status"] == "rejected"
        assert stored["rejected_at"]
        assert wiki_path.read_text(encoding="utf-8") == original
    finally:
        _cleanup(scratch)
