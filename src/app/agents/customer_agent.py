from __future__ import annotations

from typing import Any

from .base import BaseAgent


class CustomerAgent(BaseAgent):
    name = "customer"
    description = "Focuses on ICP, personas, objections, and buying triggers."
    focus = "customer personas, buying triggers, and objections"

    def build_recommendation(self, query: str, context: list[dict[str, Any]]) -> str:
        return (
            "Translate the notes into a crisp ICP profile, key objections, and the triggers that make "
            "buyers act now."
        )

    def build_next_actions(self, query: str, context: list[dict[str, Any]]) -> list[str]:
        return [
            "Extract persona clues and company-stage clues.",
            "Summarize buyer objections and approval friction.",
            "Identify the trigger events that should activate outreach or conversion.",
        ]

