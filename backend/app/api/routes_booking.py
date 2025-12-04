from fastapi import APIRouter, Depends

from app.api import get_repository
from app.models.schemas import BookingResponse
from app.services.booking_service import BookingService
from app.storage.repository import InMemoryRepository

router = APIRouter()


def get_booking_service(
    repository: InMemoryRepository = Depends(get_repository),
) -> BookingService:
    return BookingService(repository=repository)


@router.post("/{trip_id}/book", response_model=BookingResponse)
def book_trip(
    trip_id: str,
    service: BookingService = Depends(get_booking_service),
) -> BookingResponse:
    return service.book_trip(trip_id=trip_id)
