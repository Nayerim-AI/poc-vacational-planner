import logging
import re
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
        activities_pool = self._activity_pool(context, destination, destination_data)
        rag_tip = self._rag_tip(context, destination)

        day_plans: List[DayPlan] = []
        for i in range(day_count):
            current_date = start_date + timedelta(days=i)
            activity = activities_pool[i % len(activities_pool)]
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

    def _activity_pool(
        self, context: PlannerContext, destination: str, destination_data: dict
    ) -> List[dict]:
        rag_activities = self._activities_from_rag(context, destination)
        if rag_activities:
            return rag_activities
        return destination_data["activities"]

    def _activities_from_rag(self, context: PlannerContext, destination: str) -> List[dict]:
        if not context.rag_tool:
            return []
        hits = context.rag_tool.search(destination, top_k=5)
        activities: List[dict] = []
        for text, _score in hits:
            for line in text.splitlines():
                parts = [p.strip() for p in line.split("|")]
                if len(parts) < 2:
                    continue
                title = parts[0]
                description = parts[1]
                cost = self._parse_cost(parts[2] if len(parts) > 2 else None)
                time_of_day = self._parse_time(parts[3] if len(parts) > 3 else None)
                activities.append(
                    {
                        "time_of_day": time_of_day or "morning",
                        "title": title,
                        "description": description,
                        "cost_estimate": cost or 50.0,
                        "booking_required": False,
                    }
                )
        return activities

    @staticmethod
    def _parse_cost(raw: Optional[str]) -> Optional[float]:
        if not raw:
            return None
        match = re.search(r"(\d+(?:\.\d+)?)", raw.replace(",", ""))
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    @staticmethod
    def _parse_time(raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        lower = raw.lower()
        for slot in ["morning", "afternoon", "evening"]:
            if slot in lower:
                return slot
        return None

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
