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
            hits = self.rag_tool.search(plan.destination, top_k=5)
            for text, _ in hits:
                for line in text.splitlines():
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) < 2:
                        continue
                    activity_pool.append(
                        {
                            "time_of_day": "morning",
                            "title": parts[0],
                            "description": parts[1],
                            "cost_estimate": 50.0,
                            "booking_required": False,
                        }
                    )
        if not activity_pool:
            dest = self.search_tool.lookup_destination(plan.destination)
            activity_pool = dest.get("activities", [])

        if not activity_pool:
            return plan

        fixed_days: list[DayPlan] = []
        for idx, day in enumerate(plan.days):
            if day.activities:
                fixed_days.append(day)
                continue
            source = activity_pool[idx % len(activity_pool)]
            fixed_days.append(
                DayPlan(
                    date=day.date,
                    activities=[
                        Activity(
                            time_of_day=source.get("time_of_day", "morning"),
                            title=source.get("title", "Activity"),
                            description=source.get("description", ""),
                            cost_estimate=float(source.get("cost_estimate", 0.0)),
                            booking_required=bool(source.get("booking_required", False)),
                        )
                    ],
                )
            )
        plan.days = fixed_days
        return plan

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
