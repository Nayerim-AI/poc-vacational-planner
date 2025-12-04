from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_health, routes_plan, routes_booking
from app.core.config import settings
from app.core.logging import configure_logging
from app.storage.repository import InMemoryRepository


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Vacation Planner LLM PoC", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    repository = InMemoryRepository()

    app.include_router(routes_health.router, tags=["health"])
    app.include_router(
        routes_plan.router, prefix="/plan", tags=["planning"], dependencies=[]
    )
    app.include_router(
        routes_booking.router,
        prefix="/plan",
        tags=["booking"],
        dependencies=[],
    )

    # Inject repository into state for dependencies
    app.state.repository = repository
    app.state.settings = settings
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
