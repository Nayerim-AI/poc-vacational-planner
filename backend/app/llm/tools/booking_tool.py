from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import uuid4

from app.models.domain import (
    Activity,
    BookingRecord,
    BookingStatus,
    BookingType,
    DayPlan,
    PaymentStatus,
    TripPlan,
)
from app.storage.repository import InMemoryRepository


class BookingTool:
    def __init__(self, repository: InMemoryRepository):
        self.repository = repository

    def reserve_trip(self, plan: TripPlan, payment_allowed: bool = True) -> List[BookingRecord]:
        bookings: List[BookingRecord] = []
        bookings.append(
            self._create_booking(
                user_id=plan.user_id,
                trip_id=plan.trip_id,
                booking_type=BookingType.flight,
                price=plan.budget_summary.breakdown.get("flight", 0.0),
                provider="mock-air",
                payment_allowed=payment_allowed,
            )
        )
        bookings.append(
            self._create_booking(
                user_id=plan.user_id,
                trip_id=plan.trip_id,
                booking_type=BookingType.hotel,
                price=plan.budget_summary.breakdown.get("hotel", 0.0),
                provider="mock-hotel",
                payment_allowed=payment_allowed,
            )
        )

        for day in plan.days:
            bookings.extend(
                self._create_activity_bookings(
                    plan=plan,
                    day=day,
                    payment_allowed=payment_allowed,
                )
            )

        for booking in bookings:
            self.repository.save_booking(booking)
        return bookings

    def _create_activity_bookings(
        self, plan: TripPlan, day: DayPlan, payment_allowed: bool
    ) -> List[BookingRecord]:
        records: List[BookingRecord] = []
        for activity in day.activities:
            if not activity.booking_required:
                continue
            records.append(
                self._create_booking(
                    user_id=plan.user_id,
                    trip_id=plan.trip_id,
                    booking_type=BookingType.activity,
                    price=activity.cost_estimate,
                    provider="mock-activity",
                    payment_allowed=payment_allowed,
                    reference=activity.title,
                )
            )
        return records

    def _create_booking(
        self,
        user_id: str,
        trip_id: str,
        booking_type: BookingType,
        price: float,
        provider: str,
        payment_allowed: bool,
        reference: str | None = None,
    ) -> BookingRecord:
        payment_status = (
            PaymentStatus.authorized if payment_allowed else PaymentStatus.failed
        )
        status = BookingStatus.confirmed if payment_allowed else BookingStatus.failed
        return BookingRecord(
            booking_id=str(uuid4()),
            user_id=user_id,
            trip_id=trip_id,
            type=booking_type,
            status=status,
            provider=provider,
            price=price,
            created_at=datetime.utcnow(),
            payment_status=payment_status,
            reference=reference,
        )
