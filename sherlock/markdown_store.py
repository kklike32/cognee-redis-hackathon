from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

WIKI_DIR = Path("data") / "wiki"
DEFAULT_WIKI_PATH = WIKI_DIR / "deel.md"
APPROVED_UPDATES_HEADING = "## Recent Analyst-Approved Updates"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_wiki_file(path: Path = DEFAULT_WIKI_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(default_deel_markdown(), encoding="utf-8")


def read_battle_card(path: Path = DEFAULT_WIKI_PATH) -> str:
    ensure_wiki_file(path)
    return path.read_text(encoding="utf-8")


def append_approved_update(
    text: str,
    *,
    source_citation: str,
    path: Path = DEFAULT_WIKI_PATH,
    timestamp: str | None = None,
) -> str:
    ensure_wiki_file(path)
    content = path.read_text(encoding="utf-8").rstrip()
    timestamp = timestamp or utc_timestamp()

    if APPROVED_UPDATES_HEADING not in content:
        content = f"{content}\n\n{APPROVED_UPDATES_HEADING}"

    update_block = (
        f"\n\n### {timestamp}\n\n"
        f"{text.strip()}\n\n"
        f"_Source: {source_citation.strip()}_\n"
    )
    updated = f"{content}{update_block}"
    path.write_text(updated, encoding="utf-8")
    return updated


def default_deel_markdown() -> str:
    return """# Deel Battle Card

## Metadata
- Owner: Competitive Intelligence
- Last reviewed: 2026-05-16
- Confidence score: Medium
- Pending changes: 1

## Positioning Headline
Oyster is the steadier global employment partner for teams that need hands-on compliance support, predictable expansion guidance, and a sales motion built around trust.

## Quantitative Fields
- Customer count: Internal demo placeholder
- Countries served: Global employment coverage for distributed teams
- Funding / valuation: Not used in this demo
- Headcount: Not used in this demo
- Pricing: Validate during discovery
- Average deal size in Oyster funnel: Internal demo placeholder
- Win rate vs Deel last 90 days: Internal demo placeholder

## Strengths to Acknowledge
- Deel is well known and often enters deals through brand recognition.
- Buyers may perceive Deel as broad and fast-moving.
- Deel can be attractive when a prospect wants a single vendor shortlist quickly.

## Weaknesses to Attack
- Prospects may worry about support consistency after implementation.
- Complex cross-border hiring plans create room to emphasize Oyster's guided compliance posture.
- Fast platform breadth can make the buying conversation feel less consultative.

## Common Objections and Responses
- Objection: Deel seems bigger and more established.
  Response: Acknowledge the brand, then reframe around implementation confidence, compliance guidance, and the buyer's specific expansion plan.
- Objection: We need to move quickly.
  Response: Tie speed to fewer downstream mistakes, not only contract signature speed.

## Trap-Setting Discovery Questions
- Which countries are highest risk for your first wave of hiring?
- Who owns local compliance decisions after the contract is signed?
- What would a bad onboarding experience cost your team in the first 90 days?

## Customer Evidence
- Synthetic Gong note: prospects expanding into Canada and the UK asked for more country-specific onboarding support.
- Synthetic review signal: support responsiveness is a deciding factor for lean people teams.

## Segment-Specific Talk Track
For Seed to Series B startups, lead with risk reduction and implementation confidence. The buyer wants to expand quickly, but they usually lack a large internal legal or people operations team.

## Recent Activity
- Synthetic product launch note: Deel announced new workflow automation capabilities.

## Sources
- data/sources/gong_deel_transcript.md
- data/sources/g2_deel_review.md
- data/sources/deel_product_launch.md
"""
