from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sherlock.ingest import ingest_demo_data
from sherlock.wiki_builder import build_company_wiki


if __name__ == "__main__":
    print(
        json.dumps(
            {
                "wiki": build_company_wiki(company="deel", use_llm=True),
                "ingest": ingest_demo_data(),
            },
            indent=2,
        )
    )
