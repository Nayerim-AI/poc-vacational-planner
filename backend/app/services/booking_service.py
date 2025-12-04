from fastapi import HTTPException

from app.llm.tools.booking_tool import BookingTool
from app.models.schemas import BookingRecordSchema, BookingResponse
from app.storage.repository import InMemoryRepository


class BookingService:
    def __init__(self, repository: InMemoryRepository):
        self.repository = repository

    def book_trip(self, trip_id: str, payment_allowed: bool = True) -> BookingResponse:
        plan = self.repository.get_plan(trip_id)
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        tool = BookingTool(repository=self.repository)
        bookings = tool.reserve_trip(plan=plan, payment_allowed=payment_allowed)
        booking_schemas = [BookingRecordSchema.from_domain(b) for b in bookings]
        return BookingResponse(bookings=booking_schemas)
