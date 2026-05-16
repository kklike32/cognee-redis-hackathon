from __future__ import annotations

from abc import ABC
from typing import Any

from ..retrieve import retrieve_context


class BaseAgent(ABC):
    name = "base"
    description = "Generic context-driven agent scaffold."
    focus = "general"
    top_k = 5

    def build_recommendation(self, query: str, context: list[dict[str, Any]]) -> str:
        return f"Use the retrieved context to answer: {query}"

    def build_next_actions(self, query: str, context: list[dict[str, Any]]) -> list[str]:
        return [
            "Review the retrieved notes for supporting evidence.",
            "Turn the evidence into a concise draft answer.",
        ]

    def run(self, query: str) -> dict[str, Any]:
        context = retrieve_context(query, top_k=self.top_k)
        return {
            "agent": self.name,
            "description": self.description,
            "focus": self.focus,
            "query": query,
            "context": context,
            "recommendation": self.build_recommendation(query, context),
            "next_actions": self.build_next_actions(query, context),
        }

