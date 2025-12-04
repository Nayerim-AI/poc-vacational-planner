from dataclasses import dataclass
from typing import Protocol

from app.models.domain import TripPlan


class PlannerBackend(Protocol):
    def generate_plan(self, context: "PlannerContext") -> TripPlan:
        ...


@dataclass
class PlannerContext:
    user_id: str
    preferences: "Preferences"
    calendar_tool: "CalendarTool"
    search_tool: "SearchTool"
    rag_tool: "RAGTool | None" = None


class LLMClient:
    """
    Pluggable LLM client abstraction. For the PoC we ship a mock backend that
    uses deterministic logic; swapping to a real model would be done by
    implementing PlannerBackend.generate_plan.
    """

    def __init__(self, backend: PlannerBackend):
        self.backend = backend

    def plan_trip(self, context: PlannerContext) -> TripPlan:
        return self.backend.generate_plan(context)
