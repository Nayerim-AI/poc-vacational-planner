from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional


class BookingStatus(str, Enum):
    pending = "pending"
    confirmed = "confirmed"
    failed = "failed"


class BookingType(str, Enum):
    flight = "flight"
    hotel = "hotel"
    activity = "activity"


class PaymentStatus(str, Enum):
    not_required = "not_required"
    authorized = "authorized"
    captured = "captured"
    failed = "failed"


@dataclass
class Activity:
    time_of_day: str
    title: str
    description: str
    cost_estimate: float
    booking_required: bool


@dataclass
class DayPlan:
    date: date
    activities: List[Activity] = field(default_factory=list)


@dataclass
class BudgetSummary:
    total_estimated: float
    breakdown: Dict[str, float]


@dataclass
class TripPlan:
    trip_id: str
    user_id: str
    destination: str
    start_date: date
    end_date: date
    days: List[DayPlan]
    budget_summary: BudgetSummary


@dataclass
class BookingRecord:
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
