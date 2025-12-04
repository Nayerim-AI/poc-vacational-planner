from __future__ import annotations

from typing import Dict, List, Optional

from app.models.domain import BookingRecord, TripPlan


class InMemoryRepository:
    def __init__(self) -> None:
        self.plans: Dict[str, TripPlan] = {}
        self.bookings: Dict[str, BookingRecord] = {}

    def save_plan(self, plan: TripPlan) -> TripPlan:
        self.plans[plan.trip_id] = plan
        return plan

    def get_plan(self, trip_id: str) -> Optional[TripPlan]:
        return self.plans.get(trip_id)

    def list_plans(self) -> List[TripPlan]:
        return list(self.plans.values())

    def save_booking(self, booking: BookingRecord) -> BookingRecord:
        self.bookings[booking.booking_id] = booking
        return booking

    def list_bookings_for_trip(self, trip_id: str) -> List[BookingRecord]:
        return [b for b in self.bookings.values() if b.trip_id == trip_id]
