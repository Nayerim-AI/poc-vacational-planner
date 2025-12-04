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
from app.storage.repository import InMemoryRepository


class PlanningService:
    def __init__(self, repository: InMemoryRepository):
        self.repository = repository
        self.calendar_tool = CalendarTool()
        self._seed_calendar()
        self._load_calendar_from_ics()
        self.search_tool = SearchTool()
        self.preferences_tool = PreferencesTool()
        self.rag_tool = self._init_rag_tool()
        backend = (
            OllamaPlannerBackend()
            if settings.llm_provider.lower() == "ollama"
            else MockPlannerBackend()
        )
        self.planner = LLMPlanner(backend=backend)

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

    def plan_trip(self, user_id: str, preferences: Preferences) -> TripPlanSchema:
        merged_preferences = self.preferences_tool.merge_with_defaults(preferences)
        context = PlannerContext(
            user_id=user_id,
            preferences=merged_preferences,
            calendar_tool=self.calendar_tool,
            search_tool=self.search_tool,
            rag_tool=self.rag_tool,
        )
        plan = self.planner.plan(context)
        self.repository.save_plan(plan)
        return TripPlanSchema.from_domain(plan)
