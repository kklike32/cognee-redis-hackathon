from __future__ import annotations

from typing import Any

from .base import BaseAgent


class CompetitorAgent(BaseAgent):
    name = "competitor"
    description = "Focuses on competitor analysis and comparative positioning."
    focus = "competitor products, gaps, and differentiation"

    def build_recommendation(self, query: str, context: list[dict[str, Any]]) -> str:
        return (
            "Compare the target product against named competitors, then extract the most defensible "
            "differentiation points and risks."
        )

    def build_next_actions(self, query: str, context: list[dict[str, Any]]) -> list[str]:
        return [
            "List competitors and the main capability gaps.",
            "Summarize what users likely switch from and why.",
            "Turn the comparison into positioning and objection handling notes.",
        ]

