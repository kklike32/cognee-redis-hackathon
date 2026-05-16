from __future__ import annotations

import json
import mimetypes
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from sherlock.briefs import generate_brief
from sherlock.markdown_store import read_battle_card
from sherlock.pending_changes import (
    approve_change,
    invalidate_competitor_cache,
    load_pending_changes,
    reject_change,
)
from sherlock.pending_generator import generate_pending_from_wiki

try:
    from app.redis_client import ping_redis
except Exception:  # pragma: no cover - UI still runs without Redis deps.
    ping_redis = None  # type: ignore[assignment]

STATIC_DIR = ROOT / "app" / "static"


def _json_bytes(payload: object) -> bytes:
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def _reset_demo() -> dict[str, object]:
    from sherlock.markdown_store import DEFAULT_WIKI_PATH, default_deel_markdown
    from sherlock.pending_changes import PENDING_PATH, default_pending_changes, save_pending_changes

    DEFAULT_WIKI_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_WIKI_PATH.write_text(default_deel_markdown(), encoding="utf-8")
    save_pending_changes(default_pending_changes(), path=PENDING_PATH)
    return {"ok": True, "message": "Demo reset complete."}


class SherlockHandler(BaseHTTPRequestHandler):
    server_version = "SherlockLocal/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_file(STATIC_DIR / "index.html")
            return
        if path.startswith("/static/"):
            self._send_file(STATIC_DIR / path.removeprefix("/static/"))
            return
        if path == "/api/state":
            self._send_json(self._state())
            return
        if path == "/api/wiki/deel":
            self._send_json({"ok": True, "competitor": "Deel", "markdown": read_battle_card()})
            return
        self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json()

        if path == "/api/brief":
            self._send_json(generate_brief(body.get("competitor", "Deel"), body.get("deal_context", "")))
            return

        if path == "/api/pending/generate":
            self._send_json(generate_pending_from_wiki(competitor=body.get("competitor", "Deel")))
            return

        if path == "/api/reset":
            self._send_json(_reset_demo())
            return

        if path.startswith("/api/pending/") and path.endswith("/approve"):
            change_id = path.removeprefix("/api/pending/").removesuffix("/approve")
            approved = approve_change(change_id, edited_text=body.get("edited_text"))
            cache_result = invalidate_competitor_cache(str(approved.get("competitor", "Deel")))
            self._send_json({"ok": True, "change": approved, "cache": cache_result})
            return

        if path.startswith("/api/pending/") and path.endswith("/reject"):
            change_id = path.removeprefix("/api/pending/").removesuffix("/reject")
            rejected = reject_change(change_id)
            self._send_json({"ok": True, "change": rejected})
            return

        self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _read_json(self) -> dict[str, object]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _state(self) -> dict[str, object]:
        redis_status = ping_redis() if ping_redis is not None else {
            "ok": False,
            "message": "Redis helpers unavailable; no-cache mode.",
        }
        return {
            "ok": True,
            "competitors": ["Deel"],
            "redis": redis_status,
            "pending": load_pending_changes(),
            "wiki": read_battle_card(),
        }

    def _send_json(self, payload: object, *, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = _json_bytes(payload)
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_file(self, path: Path) -> None:
        resolved = path.resolve()
        if not str(resolved).startswith(str(STATIC_DIR.resolve())) or not resolved.exists():
            self._send_json({"ok": False, "error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return
        content = resolved.read_bytes()
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK.value)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def main() -> None:
    host = "127.0.0.1"
    port = 8765
    server = ThreadingHTTPServer((host, port), SherlockHandler)
    print(f"Sherlock local UI running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
