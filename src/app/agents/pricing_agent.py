from __future__ import annotations

from typing import Any

from .base import BaseAgent


class PricingAgent(BaseAgent):
    name = "pricing"
    description = "Focuses on pricing models, willingness to pay, packaging, and monetization."
    focus = "pricing, packaging, willingness to pay, and monetization"

    def build_recommendation(self, query: str, context: list[dict[str, Any]]) -> str:
        return (
            "Use the evidence to infer value metrics, likely package boundaries, and the simplest "
            "pricing test worth running first."
        )

    def build_next_actions(self, query: str, context: list[dict[str, Any]]) -> list[str]:
        return [
            "Identify the value metric implied by the notes.",
            "List any packaging constraints or expansion levers.",
            "Draft a first-pass pricing hypothesis and validation test.",
        ]

