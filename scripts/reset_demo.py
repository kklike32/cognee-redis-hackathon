from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sherlock.cache import clear_demo_redis_keys
from sherlock.config import get_settings
from sherlock.markdown_store import reset_wiki
from sherlock.pending_changes import reset_pending


def reset_demo() -> dict:
    settings = get_settings()
    if settings.local_chunk_path.exists():
        settings.local_chunk_path.unlink()
    wiki = reset_wiki("deel", settings=settings)
    pending = reset_pending(settings=settings)
    deleted = clear_demo_redis_keys(settings=settings)
    return {
        "ok": True,
        "wiki": str(wiki),
        "pending_changes": len(pending),
        "local_chunks_removed": not settings.local_chunk_path.exists(),
        "redis_keys_deleted": deleted,
    }


if __name__ == "__main__":
    print(json.dumps(reset_demo(), indent=2))
