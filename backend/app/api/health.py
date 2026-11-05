"""Model connectivity HTTP route."""
from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import models
from backend.app.schemas.health import HealthStatus
from backend.app.services.models import ModelService

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthStatus)
async def health(service: Annotated[ModelService, Depends(models)]):
    return await service.health()
