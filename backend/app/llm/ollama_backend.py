  import json
  import logging
  from dataclasses import dataclass
  from typing import Tuple

  import requests

  from app.core.config import settings
  from app.llm.client import PlannerBackend, PlannerContext
  from app.llm.prompts import PLANNER_SYSTEM_PROMPT
  from app.models.domain import Activity, BudgetSummary, DayPlan, TripPlan

  logger = logging.getLogger(__name__)


  @dataclass
  class OllamaPlannerBackend(PlannerBackend):
      def _build_messages(self, context: PlannerContext) -> list[dict]:
          prefs = context.preferences
          catalog = context.search_tool.catalog  # small enough for prompt
          calendar_hint: list[Tuple[str, str]] = [
              (r[0].isoformat(), r[1].isoformat())
              for r in context.calendar_tool.get_free_date_ranges(
                  user_id=context.user_id, start=prefs.start_date or None, end=prefs.end_date or None  # type: ignore[arg-type]
              )
          ]
          user_block = {
              "preferences": prefs.dict(),
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
                  + json.dumps(user_block),
              },
          ]

      def generate_plan(self, context: PlannerContext) -> TripPlan:
          messages = self._build_messages(context)
          payload = {"model": settings.ollama_model, "messages": messages, "stream": False}
          resp = requests.post(
              f"{settings.ollama_host}/api/chat", json=payload, timeout=30
          )
          resp.raise_for_status()
          content = resp.json()["message"]["content"]
          try:
              data = json.loads(content)
          except json.JSONDecodeError as exc:
              logger.error("Invalid JSON from model: %s", content)
              raise ValueError("LLM returned invalid JSON") from exc

          return self._to_domain(data, user_id=context.user_id)

      def _to_domain(self, data: dict, user_id: str) -> TripPlan:
          days = [
              DayPlan(
                  date=day["date"],
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
              for day in data["days"]
          ]
          budget = data.get("budget_summary", {})
          return TripPlan(
              trip_id=data["trip_id"],
              user_id=user_id,
              destination=data["destination"],
              start_date=data["start_date"],
              end_date=data["end_date"],
              days=days,
              budget_summary=BudgetSummary(
                  total_estimated=float(budget.get("total_estimated", 0)),
                  breakdown=budget.get("breakdown", {}),
              ),
          )
