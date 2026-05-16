from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sherlock.markdown_store import DEFAULT_WIKI_PATH, default_deel_markdown
from sherlock.pending_changes import PENDING_PATH, default_pending_changes, save_pending_changes


def main() -> None:
    DEFAULT_WIKI_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_WIKI_PATH.write_text(default_deel_markdown(), encoding="utf-8")
    save_pending_changes(default_pending_changes(), path=PENDING_PATH)
    print("Demo reset complete.")
    print(f"Reset wiki: {DEFAULT_WIKI_PATH}")
    print(f"Reset pending changes: {PENDING_PATH}")


if __name__ == "__main__":
    main()
