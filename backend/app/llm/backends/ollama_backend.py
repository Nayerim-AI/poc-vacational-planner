from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Tuple
from uuid import uuid4

import requests

from app.core.config import settings
from app.llm.client import PlannerBackend, PlannerContext
from app.llm.prompts import PLANNER_SYSTEM_PROMPT
from app.models.domain import Activity, BudgetSummary, DayPlan, TripPlan

logger = logging.getLogger(__name__)


def _serialize_preferences(preferences) -> dict:
    data = preferences.dict()
    if preferences.start_date:
        data["start_date"] = preferences.start_date.isoformat()
    if preferences.end_date:
        data["end_date"] = preferences.end_date.isoformat()
    return data


@dataclass
class OllamaPlannerBackend(PlannerBackend):
    """
    Planner backend using Ollama's chat API.
    Expects the model to return a TripPlan-compatible JSON object.
    """

    def _build_messages(self, context: PlannerContext) -> List[dict]:
        prefs = context.preferences
        catalog = context.search_tool.catalog  # small enough for prompt
        calendar_hint = self._calendar_hint(context)
        user_block = {
            "preferences": _serialize_preferences(prefs),
            "catalog": catalog,
            "calendar_free": calendar_hint,
            "requirements": {
                "budget_max": prefs.budget_max,
                "min_days": prefs.min_duration_days,
                "max_days": prefs.max_duration_days,
            },
        }
        return [
            {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Return a valid TripPlan JSON object only (no prose). Input:\n"
                + json.dumps(user_block, default=str),
            },
        ]

    def _calendar_hint(self, context: PlannerContext) -> List[Tuple[str, str]]:
        prefs = context.preferences
        start = prefs.start_date or date.today()
        end = prefs.end_date or date.today() + timedelta(days=90)
        ranges = context.calendar_tool.get_free_date_ranges(
            user_id=context.user_id, start=start, end=end
        )
        return [(rng[0].isoformat(), rng[1].isoformat()) for rng in ranges]

    def generate_plan(self, context: PlannerContext) -> TripPlan:
        messages = self._build_messages(context)
        payload = {"model": settings.ollama_model, "messages": messages, "stream": False}
        try:
            resp = requests.post(
                f"{settings.ollama_host}/api/chat", json=payload, timeout=30
            )
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            logger.error("Ollama request failed: %s", exc)
            raise

        content = resp.json().get("message", {}).get("content", "")
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON from model: %s", content)
            raise ValueError("LLM returned invalid JSON") from exc

        return self._to_domain(data, user_id=context.user_id)

    def _to_domain(self, data: dict, user_id: str) -> TripPlan:
        def _parse_date(value) -> date:
            if isinstance(value, date):
                return value
            return date.fromisoformat(value)

        days = [
            DayPlan(
                date=_parse_date(day["date"]),
                activities=[
                    Activity(
                        time_of_day=a["time_of_day"],
                        title=a["title"],
                        description=a["description"],
                        cost_estimate=float(a["cost_estimate"]),
                        booking_required=bool(a["booking_required"]),
                    )
                    for a in day["activities"]
                ],
            )
            for day in data.get("days", [])
        ]
        budget = data.get("budget_summary", {})
        trip_id = data.get("trip_id") or str(uuid4())
        return TripPlan(
            trip_id=trip_id,
            user_id=user_id,
            destination=data["destination"],
            start_date=_parse_date(data["start_date"]),
            end_date=_parse_date(data["end_date"]),
            days=days,
            budget_summary=BudgetSummary(
                total_estimated=float(budget.get("total_estimated", 0.0)),
                breakdown=budget.get("breakdown", {}),
            ),
        )
