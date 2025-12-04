from fastapi import Depends, HTTPException
from starlette.requests import Request

from app.storage.repository import InMemoryRepository


def get_repository(request: Request) -> InMemoryRepository:
    repository = getattr(request.app.state, "repository", None)
    if repository is None:
        raise HTTPException(status_code=500, detail="Repository not initialized")
    return repository
