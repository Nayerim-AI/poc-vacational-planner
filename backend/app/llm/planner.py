import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional, Tuple
from uuid import uuid4

from app.core.config import settings
from app.llm.client import LLMClient, PlannerContext, PlannerBackend
from app.llm.prompts import PLANNER_SYSTEM_PROMPT
from app.models.domain import Activity, BudgetSummary, DayPlan, TripPlan
from app.models.schemas import Preferences

logger = logging.getLogger(__name__)


@dataclass
class PlannerTools:
    calendar: "CalendarTool"
    search: "SearchTool"


class MockPlannerBackend(PlannerBackend):
    """
    A deterministic planner that simulates LLM output. It selects the first
    preferred destination with data, finds available dates, and assembles a
    simple itinerary while honoring budget limits where possible.
    """

    def generate_plan(self, context: PlannerContext) -> TripPlan:
        preferences = context.preferences
        destination = self._select_destination(preferences, context.search_tool)
        start_date, end_date = self._select_dates(preferences, context.calendar_tool)
        day_count = (end_date - start_date).days + 1
        destination_data = context.search_tool.lookup_destination(destination)
        activities = destination_data["activities"]
        rag_tip = self._rag_tip(context, destination)

        day_plans: List[DayPlan] = []
        for i in range(day_count):
            current_date = start_date + timedelta(days=i)
            activity = activities[i % len(activities)]
            description = activity["description"]
            if rag_tip:
                description = f"{description} | Local tip: {rag_tip}"
            day_plans.append(
                DayPlan(
                    date=current_date,
                    activities=[
                        Activity(
                            time_of_day="morning",
                            title=activity["title"],
                            description=description,
                            cost_estimate=activity["price"],
                            booking_required=activity["booking_required"],
                        )
                    ],
                )
            )

        budget_summary = self._build_budget(preferences, destination_data, day_plans)

        trip_id = str(uuid4())
        logger.info(
            "Generated plan %s for user %s to %s",
            trip_id,
            context.user_id,
            destination,
        )

        return TripPlan(
            trip_id=trip_id,
            user_id=context.user_id,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            days=day_plans,
            budget_summary=budget_summary,
        )

    def _rag_tip(self, context: PlannerContext, destination: str) -> Optional[str]:
        if not context.rag_tool:
            return None
        hits = context.rag_tool.search(destination, top_k=1)
        if not hits:
            return None
        snippet = hits[0][0].strip()
        # Use first line to keep context small
        return snippet.splitlines()[0][:200]

    def _select_destination(
        self, preferences: Preferences, search_tool: "SearchTool"
    ) -> str:
        for dest in preferences.destination_preferences:
            if search_tool.has_destination(dest):
                return dest
        return search_tool.default_destination()

    def _select_dates(
        self, preferences: Preferences, calendar_tool: "CalendarTool"
    ) -> Tuple[date, date]:
        if preferences.start_date and preferences.end_date:
            if calendar_tool.is_range_available(
                user_id=settings.default_user_id,
                start=preferences.start_date,
                end=preferences.end_date,
            ):
                return preferences.start_date, preferences.end_date
            raise ValueError("Requested dates are not available")

        start_search = date.today()
        end_search = start_search + timedelta(days=90)
        free_ranges = calendar_tool.get_free_date_ranges(
            user_id=settings.default_user_id, start=start_search, end=end_search
        )
        desired_min = preferences.min_duration_days
        desired_max = preferences.max_duration_days
        for rng_start, rng_end in free_ranges:
            rng_length = (rng_end - rng_start).days + 1
            if rng_length >= desired_min:
                duration = min(rng_length, desired_max)
                return rng_start, rng_start + timedelta(days=duration - 1)
        raise ValueError("No available dates found")

    def _build_budget(
        self, preferences: Preferences, destination_data: dict, days: List[DayPlan]
    ) -> BudgetSummary:
        flight_price = destination_data["flight"]["price"]
        hotel_price_per_night = destination_data["hotel"]["price_per_night"]
        activity_total = sum(a.cost_estimate for d in days for a in d.activities)
        night_count = len(days) - 1 if len(days) > 1 else 1
        hotel_total = night_count * hotel_price_per_night
        total = flight_price + hotel_total + activity_total
        constrained_total = min(total, preferences.budget_max)
        return BudgetSummary(
            total_estimated=constrained_total,
            breakdown={
                "flight": flight_price,
                "hotel": hotel_total,
                "activities": activity_total,
            },
        )


class LLMPlanner:
    def __init__(self, backend: PlannerBackend):
        self.client = LLMClient(backend=backend)
        self.system_prompt = PLANNER_SYSTEM_PROMPT

    def plan(self, context: PlannerContext) -> TripPlan:
        try:
            return self.client.plan_trip(context)
        except Exception as exc:  # noqa: BLE001
            logger.error("Planner failed: %s", exc)
            raise
