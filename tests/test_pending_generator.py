from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from sherlock.pending_generator import generate_pending_from_wiki


def _scratch_dir() -> Path:
    path = Path(".cache") / "test-scratch" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cleanup(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def test_generate_pending_from_wiki_creates_structured_proposal():
    scratch = _scratch_dir()
    try:
        wiki_path = scratch / "deel.md"
        wiki_path.write_text(
            "# Deel Battle Card\n\n## Weaknesses to Attack\n- Existing note.\n",
            encoding="utf-8",
        )
        source_path = scratch / "incoming.md"
        source_path.write_text(
            "# Incoming\n\n"
            "- Buyer asked for a clearer country-by-country onboarding plan before choosing between Oyster and Deel.\n",
            encoding="utf-8",
        )

        result = generate_pending_from_wiki(
            competitor="Deel",
            wiki_path=wiki_path,
            source_paths=[source_path],
            persist=False,
        )

        assert result["ok"] is True
        assert result["generated"] == 1
        proposal = result["proposals"][0]
        assert proposal["competitor"] == "Deel"
        assert proposal["status"] == "pending"
        assert proposal["priority"] == "Critical"
        assert proposal["source_citation"].endswith("incoming.md#L3")
    finally:
        _cleanup(scratch)


def test_generate_pending_from_wiki_skips_lines_already_in_card():
    scratch = _scratch_dir()
    try:
        line = "Buyer asked for a clearer country-by-country onboarding plan before choosing between Oyster and Deel."
        wiki_path = scratch / "deel.md"
        wiki_path.write_text(f"# Deel Battle Card\n\n- {line}\n", encoding="utf-8")
        source_path = scratch / "incoming.md"
        source_path.write_text(f"# Incoming\n\n- {line}\n", encoding="utf-8")

        result = generate_pending_from_wiki(
            competitor="Deel",
            wiki_path=wiki_path,
            source_paths=[source_path],
            persist=False,
        )

        assert result["generated"] == 0
        assert result["proposals"] == []
    finally:
        _cleanup(scratch)
