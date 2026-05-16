from __future__ import annotations

import re
from pathlib import Path

from .config import Settings, get_settings


APPROVED_BLOCK_RE = re.compile(
    r"\n?<!-- sherlock-approved:[^:]+:start -->.*?<!-- sherlock-approved:[^:]+:end -->\n?",
    re.DOTALL,
)


def wiki_path(competitor: str = "deel", settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    return settings.wiki_dir / f"{competitor.lower()}.md"


def read_wiki(competitor: str = "deel", settings: Settings | None = None) -> str:
    path = wiki_path(competitor, settings)
    return path.read_text(encoding="utf-8")


def _section_bounds(markdown: str, heading: str) -> tuple[int, int]:
    start = markdown.find(heading)
    if start == -1:
        raise ValueError(f"Heading not found: {heading}")
    next_match = re.search(r"\n##\s+", markdown[start + len(heading) :])
    if not next_match:
        return start, len(markdown)
    return start, start + len(heading) + next_match.start()


def remove_approved_blocks(markdown: str) -> str:
    return APPROVED_BLOCK_RE.sub("\n", markdown).replace("\n\n\n", "\n\n")


def apply_approved_change(
    target_file: str,
    target_section: str,
    change_id: str,
    proposed_markdown: str,
    settings: Settings | None = None,
) -> Path:
    settings = settings or get_settings()
    path = settings.root_dir / target_file
    markdown = path.read_text(encoding="utf-8")
    markdown = re.sub(
        rf"\n?<!-- sherlock-approved:{re.escape(change_id)}:start -->.*?"
        rf"<!-- sherlock-approved:{re.escape(change_id)}:end -->\n?",
        "\n",
        markdown,
        flags=re.DOTALL,
    )
    start, end = _section_bounds(markdown, target_section)
    section = markdown[start:end].rstrip()
    rest = markdown[end:]
    block = (
        f"\n\n<!-- sherlock-approved:{change_id}:start -->\n"
        f"{proposed_markdown.strip()}\n"
        f"<!-- sherlock-approved:{change_id}:end -->"
    )
    updated = markdown[:start] + section + block + rest
    path.write_text(updated, encoding="utf-8")
    return path


def reset_wiki(competitor: str = "deel", settings: Settings | None = None) -> Path:
    path = wiki_path(competitor, settings)
    markdown = path.read_text(encoding="utf-8")
    path.write_text(remove_approved_blocks(markdown), encoding="utf-8")
    return path
