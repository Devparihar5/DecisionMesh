"""Aggregate and per-agent performance analytics HTTP route."""
from typing import Annotated, Literal

from fastapi import APIRouter, Depends

from backend.app.api.dependencies import analytics
from backend.app.schemas.analytics import AnalyticsReport
from backend.app.services.analytics import AnalyticsService

router = APIRouter(tags=['analytics'])


@router.get('/api/analytics', response_model=AnalyticsReport)
def report(service: Annotated[AnalyticsService, Depends(analytics)], days: Literal['0', '7', '30', '90'] = '30'):
    return service.report(int(days))
