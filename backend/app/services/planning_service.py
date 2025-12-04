import logging
from datetime import date, timedelta
from pathlib import Path

from app.core.config import settings
from app.llm.client import PlannerContext
from app.llm.planner import LLMPlanner, MockPlannerBackend
from app.llm.backends.ollama_backend import OllamaPlannerBackend
from app.llm.tools.calendar_tool import CalendarTool
from app.llm.tools.preferences_tool import PreferencesTool
from app.llm.tools.search_tool import SearchTool
from app.llm.tools.rag_store import RAGTool
from app.models.schemas import Preferences, TripPlanSchema
from app.models.domain import Activity, DayPlan
from app.storage.repository import InMemoryRepository
import re

logger = logging.getLogger(__name__)


class PlanningService:
    def __init__(self, repository: InMemoryRepository):
        self.repository = repository
        self.calendar_tool = CalendarTool()
        self._seed_calendar()
        self._load_calendar_from_ics()
        self.search_tool = SearchTool()
        self.preferences_tool = PreferencesTool()
        self.rag_tool = self._init_rag_tool()
        primary_backend = (
            OllamaPlannerBackend()
            if settings.llm_provider.lower() == "ollama"
            else MockPlannerBackend()
        )
        self.planner = LLMPlanner(backend=primary_backend)
        self.fallback_planner = (
            LLMPlanner(backend=MockPlannerBackend())
            if not isinstance(primary_backend, MockPlannerBackend)
            else None
        )

    def _seed_calendar(self) -> None:
        today = date.today()
        busy_ranges = [
            (today + timedelta(days=5), today + timedelta(days=7)),
            (today + timedelta(days=20), today + timedelta(days=22)),
        ]
        self.calendar_tool.seed_busy_ranges(settings.default_user_id, busy_ranges)

    def _load_calendar_from_ics(self) -> None:
        if settings.calendar_ics_url:
            self.calendar_tool.load_from_ics(
                user_id=settings.default_user_id,
                url=settings.calendar_ics_url,
            )

    def _init_rag_tool(self) -> RAGTool | None:
        path = Path(settings.rag_docs_path)
        if not path.exists():
            return None
        rag = RAGTool(store_path=path)
        rag.load_dir()
        return rag

    def _fill_empty_days(self, plan):
        """If planner returns empty activities, backfill from RAG or catalog to avoid blank days."""
        activity_pool: list[dict] = []
        if self.rag_tool:
            hits = self.rag_tool.search(plan.destination, top_k=10)
            for text, _ in hits:
                for line in text.splitlines():
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) < 2:
                        continue
                    activity_pool.append(
                        {
                            "time_of_day": self._parse_time(parts[3] if len(parts) > 3 else None),
                            "title": parts[0],
                            "description": parts[1],
                            "cost_estimate": self._parse_cost(parts[2] if len(parts) > 2 else None),
                            "booking_required": False,
                        }
                    )
        if not activity_pool:
            dest = self.search_tool.lookup_destination(plan.destination)
            activity_pool = dest.get("activities", [])

        fixed_days: list[DayPlan] = []
        for idx, day in enumerate(plan.days):
            activities = [
                a for a in getattr(day, "activities", []) if not self._is_placeholder(a.title, a.description)
            ]
            if activities:
                fixed_days.append(DayPlan(date=day.date, activities=activities))
                continue
            source = activity_pool[idx % len(activity_pool)] if activity_pool else self._synth_activity(plan.destination)
            fixed_days.append(
                DayPlan(
                    date=day.date,
                    activities=[
                        Activity(
                            time_of_day=source.get("time_of_day") or "morning",
                            title=source.get("title") or self._synthetic_title(plan.destination),
                            description=source.get("description") or self._synthetic_description(plan.destination),
                            cost_estimate=float(source.get("cost_estimate") or 50.0),
                            booking_required=bool(source.get("booking_required", False)),
                        )
                    ],
                )
            )
        plan.days = fixed_days
        self._rebalance_budget(plan)
        return plan

    @staticmethod
    def _is_placeholder(title: str, description: str) -> bool:
        combined = (title or "") + " " + (description or "")
        return any(token in combined.lower() for token in ["sample activity", "short description", "placeholder"])

    @staticmethod
    def _parse_cost(raw: str | None) -> float:
        if not raw:
            return 0.0
        match = re.search(r"(\\d+(?:\\.\\d+)?)", raw.replace(",", ""))
        return float(match.group(1)) if match else 0.0

    @staticmethod
    def _parse_time(raw: str | None) -> str | None:
        if not raw:
            return None
        lower = raw.lower()
        for slot in ["morning", "afternoon", "evening"]:
            if slot in lower:
                return slot
        return None

    @staticmethod
    def _synthetic_title(destination: str) -> str:
        return f"{destination} city walk"

    @staticmethod
    def _synthetic_description(destination: str) -> str:
        return f"Explore notable spots in {destination}, with local food or views."

    def _synth_activity(self, destination: str) -> dict:
        return {
            "time_of_day": "afternoon",
            "title": self._synthetic_title(destination),
            "description": self._synthetic_description(destination),
            "cost_estimate": 60.0,
            "booking_required": False,
        }

    def _rebalance_budget(self, plan) -> None:
        activity_total = sum(a.cost_estimate for d in plan.days for a in d.activities)
        breakdown = plan.budget_summary.breakdown or {}
        flight = float(breakdown.get("flight", 0.0))
        hotel = float(breakdown.get("hotel", 0.0))
        breakdown["activities"] = activity_total
        plan.budget_summary.breakdown = breakdown
        plan.budget_summary.total_estimated = flight + hotel + activity_total

    def plan_trip(self, user_id: str, preferences: Preferences) -> TripPlanSchema:
        merged_preferences = self.preferences_tool.merge_with_defaults(preferences)
        context = PlannerContext(
            user_id=user_id,
            preferences=merged_preferences,
            calendar_tool=self.calendar_tool,
            search_tool=self.search_tool,
            rag_tool=self.rag_tool,
        )
        try:
            plan = self.planner.plan(context)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Primary planner failed, fallback to mock: %s", exc)
            if self.fallback_planner:
                plan = self.fallback_planner.plan(context)
            else:
                raise
        self.repository.save_plan(plan)
        return TripPlanSchema.from_domain(plan)
