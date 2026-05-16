from __future__ import annotations

from typing import Any

from .base import BaseAgent


class GTMResearchAgent(BaseAgent):
    name = "gtm"
    description = "Answers GTM research questions using retrieved memory and notes."
    focus = "market, ICP, customer pain points, positioning, and channels"

    def build_recommendation(self, query: str, context: list[dict[str, Any]]) -> str:
        return (
            "Synthesize the strongest recurring market themes, identify the clearest ICP signals, "
            "and connect them to a simple wedge and channel hypothesis."
        )

    def build_next_actions(self, query: str, context: list[dict[str, Any]]) -> list[str]:
        return [
            "Extract the strongest pain points and repeat mentions.",
            "Identify the narrowest believable ICP.",
            "Convert the evidence into a wedge, positioning statement, and first channel test.",
        ]

