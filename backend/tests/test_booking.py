from app.models.schemas import Preferences
from app.services.booking_service import BookingService
from app.services.planning_service import PlanningService
from app.storage.repository import InMemoryRepository


def test_booking_creates_records():
    repository = InMemoryRepository()
    planning_service = PlanningService(repository=repository)
    booking_service = BookingService(repository=repository)

    preferences = Preferences(destination_preferences=["Lisbon"], budget_max=1200.0)
    plan = planning_service.plan_trip(user_id="demo-user", preferences=preferences)

    response = booking_service.book_trip(trip_id=plan.trip_id, payment_allowed=True)

    assert response.bookings
    assert any(b.type == "flight" for b in response.bookings)
