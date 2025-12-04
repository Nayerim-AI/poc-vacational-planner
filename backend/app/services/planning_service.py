from datetime import date, timedelta

from app.core.config import settings
from app.llm.client import PlannerContext
from app.llm.planner import LLMPlanner, MockPlannerBackend
from app.llm.tools.calendar_tool import CalendarTool
from app.llm.tools.preferences_tool import PreferencesTool
from app.llm.tools.search_tool import SearchTool
from app.models.schemas import Preferences, TripPlanSchema
from app.storage.repository import InMemoryRepository


class PlanningService:
    def __init__(self, repository: InMemoryRepository):
        self.repository = repository
        self.calendar_tool = CalendarTool()
        self._seed_calendar()
        self.search_tool = SearchTool()
        self.preferences_tool = PreferencesTool()
        self.planner = LLMPlanner(backend=MockPlannerBackend())

    def _seed_calendar(self) -> None:
        today = date.today()
        busy_ranges = [
            (today + timedelta(days=5), today + timedelta(days=7)),
            (today + timedelta(days=20), today + timedelta(days=22)),
        ]
        self.calendar_tool.seed_busy_ranges(settings.default_user_id, busy_ranges)

    def plan_trip(self, user_id: str, preferences: Preferences) -> TripPlanSchema:
        merged_preferences = self.preferences_tool.merge_with_defaults(preferences)
        context = PlannerContext(
            user_id=user_id,
            preferences=merged_preferences,
            calendar_tool=self.calendar_tool,
            search_tool=self.search_tool,
        )
        plan = self.planner.plan(context)
        self.repository.save_plan(plan)
        return TripPlanSchema.from_domain(plan)
