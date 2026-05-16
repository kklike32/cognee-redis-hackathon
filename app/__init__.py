from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC_APP = _ROOT / "src" / "app"

if _SRC_APP.exists():
    __path__.append(str(_SRC_APP))

