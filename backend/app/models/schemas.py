from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from app.models.domain import (
    Activity,
    BookingRecord,
    BookingStatus,
    BookingType,
    DayPlan,
    PaymentStatus,
    TripPlan,
)


class Preferences(BaseModel):
    destination_preferences: List[str] = Field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    min_duration_days: int = 3
    max_duration_days: int = 5
    budget_min: float = 800.0
    budget_max: float = 2000.0
    travel_style: str = "relaxing"
    max_flight_hours: Optional[int] = None
    notes: Optional[str] = None


class ActivitySchema(BaseModel):
    time_of_day: str
    title: str
    description: str
    cost_estimate: float
    booking_required: bool

    @classmethod
    def from_domain(cls, obj: Activity) -> "ActivitySchema":
        return cls(
            time_of_day=obj.time_of_day,
            title=obj.title,
            description=obj.description,
            cost_estimate=obj.cost_estimate,
            booking_required=obj.booking_required,
        )


class DayPlanSchema(BaseModel):
    date: date
    activities: List[ActivitySchema]

    @classmethod
    def from_domain(cls, obj: DayPlan) -> "DayPlanSchema":
        return cls(
            date=obj.date,
            activities=[ActivitySchema.from_domain(a) for a in obj.activities],
        )


class BudgetSummarySchema(BaseModel):
    total_estimated: float
    breakdown: Dict[str, float]


class TripPlanSchema(BaseModel):
    trip_id: str
    user_id: str
    destination: str
    start_date: date
    end_date: date
    days: List[DayPlanSchema]
    budget_summary: BudgetSummarySchema

    @classmethod
    def from_domain(cls, obj: TripPlan) -> "TripPlanSchema":
        return cls(
            trip_id=obj.trip_id,
            user_id=obj.user_id,
            destination=obj.destination,
            start_date=obj.start_date,
            end_date=obj.end_date,
            days=[DayPlanSchema.from_domain(d) for d in obj.days],
            budget_summary=BudgetSummarySchema(
                total_estimated=obj.budget_summary.total_estimated,
                breakdown=obj.budget_summary.breakdown,
            ),
        )


class PlanResponse(BaseModel):
    plan: TripPlanSchema


class BookingRecordSchema(BaseModel):
    booking_id: str
    user_id: str
    trip_id: str
    type: BookingType
    status: BookingStatus
    provider: str
    price: float
    created_at: datetime
    payment_status: PaymentStatus
    reference: Optional[str] = None

    @classmethod
    def from_domain(cls, obj: BookingRecord) -> "BookingRecordSchema":
        return cls(
            booking_id=obj.booking_id,
            user_id=obj.user_id,
            trip_id=obj.trip_id,
            type=obj.type,
            status=obj.status,
            provider=obj.provider,
            price=obj.price,
            created_at=obj.created_at,
            payment_status=obj.payment_status,
            reference=obj.reference,
        )


class BookingResponse(BaseModel):
    bookings: List[BookingRecordSchema]
