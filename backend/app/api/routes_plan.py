from fastapi import APIRouter, Depends, HTTPException

from app.api import get_repository
from app.core.config import settings
from app.models.schemas import PlanResponse, Preferences, TripPlanSchema
from app.services.planning_service import PlanningService
from app.storage.repository import InMemoryRepository

router = APIRouter()


def get_planning_service(
    repository: InMemoryRepository = Depends(get_repository),
) -> PlanningService:
    return PlanningService(repository=repository)


@router.post("/", response_model=PlanResponse)
def create_plan(
    preferences: Preferences,
    service: PlanningService = Depends(get_planning_service),
) -> PlanResponse:
    plan = service.plan_trip(user_id=settings.default_user_id, preferences=preferences)
    return PlanResponse(plan=plan)


@router.get("/{trip_id}", response_model=TripPlanSchema)
def get_plan(
    trip_id: str, repository: InMemoryRepository = Depends(get_repository)
) -> TripPlanSchema:
    plan = repository.get_plan(trip_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return TripPlanSchema.from_domain(plan)
