"""Paginated durable run history and detailed findings."""
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.app.api.dependencies import history
from backend.app.schemas.history import RunDetail, RunPage, StoredRunStatus
from backend.app.storage.runs import RunRepository

router = APIRouter(prefix='/api/runs', tags=['history'])


@router.get('', response_model=RunPage)
def list_runs(
    repository: Annotated[RunRepository, Depends(history)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: StoredRunStatus | None = None,
    search: Annotated[str, Query(max_length=200)] = '',
):
    return repository.list_runs(limit, offset, status, search)


@router.get('/{run_id}', response_model=RunDetail)
def run_detail(run_id: str, repository: Annotated[RunRepository, Depends(history)]):
    return repository.detail(run_id)
