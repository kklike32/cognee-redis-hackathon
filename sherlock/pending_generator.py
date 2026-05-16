from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

from .markdown_store import DEFAULT_WIKI_PATH, read_battle_card
from .pending_changes import upsert_pending_changes

INCOMING_DIR = Path("data") / "incoming"
SOURCE_DIR = Path("data") / "sources"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def _source_files() -> list[Path]:
    files: list[Path] = []
    for folder in (INCOMING_DIR, SOURCE_DIR):
        if folder.exists():
            files.extend(sorted(folder.glob("*.md")))
    return files


def _meaningful_lines(text: str) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for index, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip().lstrip("- ").strip()
        if not line or line.startswith("#"):
            continue
        if re.match(r"^(account|summary|notes|sales interpretation):", line, re.IGNORECASE):
            continue
        if len(line) < 32:
            continue
        lines.append((index, line))
    return lines


def _priority_for(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("risk", "compliance", "asked", "concern", "cfo")):
        return "Critical"
    if any(token in lowered for token in ("support", "onboarding", "implementation")):
        return "Nice to have"
    return "FYI"


def _section_for(text: str) -> str:
    lowered = text.lower()
    if any(token in lowered for token in ("risk", "concern", "weak", "support", "compliance")):
        return "Weaknesses to Attack"
    if any(token in lowered for token in ("question", "asked", "cfo")):
        return "Trap-Setting Discovery Questions"
    if any(token in lowered for token in ("launch", "announced", "automation")):
        return "Recent Activity"
    return "Customer Evidence"


def _proposal_text(line: str) -> str:
    return (
        f"New local wiki/source signal: {line} "
        "Use this in the Deel battle card if the analyst agrees it changes sales guidance."
    )


def generate_pending_from_wiki(
    *,
    competitor: str = "Deel",
    wiki_path: Path = DEFAULT_WIKI_PATH,
    source_paths: list[Path] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    card = read_battle_card(wiki_path).lower()
    files = source_paths if source_paths is not None else _source_files()
    proposals: list[dict[str, Any]] = []

    for source_path in files:
        if not source_path.exists():
            continue
        text = source_path.read_text(encoding="utf-8")
        for line_number, line in _meaningful_lines(text):
            if line.lower() in card:
                continue
            digest = hashlib.sha1(f"{source_path}:{line}".encode("utf-8")).hexdigest()[:10]
            proposals.append(
                {
                    "id": f"{_slug(competitor)}-{_slug(source_path.stem)}-{digest}",
                    "competitor": competitor,
                    "priority": _priority_for(line),
                    "proposed_section": _section_for(line),
                    "proposed_text": _proposal_text(line),
                    "source_citation": f"{source_path.as_posix()}#L{line_number}",
                    "status": "pending",
                }
            )
            break

    if persist and proposals:
        merged = upsert_pending_changes(proposals)
    else:
        merged = []

    return {
        "ok": True,
        "competitor": competitor,
        "generated": len(proposals),
        "persisted": bool(persist),
        "proposals": proposals,
        "pending_total": len(merged) if persist and proposals else None,
    }
