from __future__ import annotations

from typing import Any

import requests

from .config import Settings, get_settings

OPENAI_BASE_URL = "https://api.openai.com/v1"


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _extract_output_text(payload: dict[str, Any]) -> str | None:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]

    output = payload.get("output")
    if isinstance(output, list):
        texts: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") == "output_text":
                    text = content.get("text")
                    if isinstance(text, str):
                        texts.append(text)
        if texts:
            return "\n".join(texts)

    return None


def check_openai_api(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    api_key = settings.effective_llm_api_key or settings.openai_api_key

    if not api_key:
        return {
            "ok": False,
            "status": "not_configured",
            "message": "Set OPENAI_API_KEY or LLM_API_KEY in .env.",
        }

    llm_model = settings.llm_model or "gpt-5.4-mini"
    embedding_model = settings.embedding_model or "text-embedding-3-small"

    results: dict[str, Any] = {
        "ok": True,
        "status": "reachable",
        "base_url": OPENAI_BASE_URL,
        "llm_model": llm_model,
        "embedding_model": embedding_model,
        "checks": {},
    }

    try:
        responses_request = requests.post(
            f"{OPENAI_BASE_URL}/responses",
            headers=_headers(api_key),
            json={
                "model": llm_model,
                "input": "Reply with exactly: ok",
                "max_output_tokens": 16,
            },
            timeout=60,
        )
        responses_request.raise_for_status()
        responses_payload = responses_request.json()
        results["checks"]["responses"] = {
            "ok": True,
            "status_code": responses_request.status_code,
            "output_text": _extract_output_text(responses_payload),
        }
    except Exception as exc:
        results["ok"] = False
        results["checks"]["responses"] = {
            "ok": False,
            "error": str(exc),
        }

    try:
        embeddings_request = requests.post(
            f"{OPENAI_BASE_URL}/embeddings",
            headers=_headers(api_key),
            json={
                "model": embedding_model,
                "input": "OpenAI key health check",
            },
            timeout=60,
        )
        embeddings_request.raise_for_status()
        embeddings_payload = embeddings_request.json()
        embedding_count = 0
        if isinstance(embeddings_payload, dict):
            data = embeddings_payload.get("data")
            if isinstance(data, list):
                embedding_count = len(data)
        results["checks"]["embeddings"] = {
            "ok": True,
            "status_code": embeddings_request.status_code,
            "embedding_count": embedding_count,
        }
    except Exception as exc:
        results["ok"] = False
        results["checks"]["embeddings"] = {
            "ok": False,
            "error": str(exc),
        }

    if results["ok"]:
        results["message"] = "OpenAI API key and selected models responded successfully."
    else:
        results["message"] = "One or more OpenAI API checks failed."

    return results
