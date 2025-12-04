from app.models.schemas import Preferences
from app.services.planning_service import PlanningService
from app.storage.repository import InMemoryRepository


def test_plan_respects_budget_and_destination():
    repository = InMemoryRepository()
    service = PlanningService(repository=repository)
    preferences = Preferences(
        destination_preferences=["Lisbon"],
        budget_max=900.0,
    )

    plan = service.plan_trip(user_id="demo-user", preferences=preferences)

    assert plan.destination == "Lisbon"
    assert plan.budget_summary.total_estimated <= preferences.budget_max
    assert len(plan.days) >= preferences.min_duration_days
