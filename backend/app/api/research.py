"""Research jobs, persisted progress, and portable evaluation exports."""
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from backend.app.api.enterprise import Jobs, research_jobs
from backend.app.schemas.enterprise import BenchmarkInput, Job
from backend.app.services.evaluation import DATASET, EvaluationService
from backend.app.services.research_jobs import ResearchJobs

router = APIRouter(prefix='/api/research', tags=['research'])


@router.get('/dataset')
def dataset():
    return {'version': 'inventory-six-v1', 'cases': DATASET}


@router.get('/jobs', response_model=list[Job])
def jobs_list(jobs: Jobs, kind: str = 'benchmark'):
    return jobs.repository.jobs(kind)


@router.get('/jobs/{job_id}', response_model=Job)
def job(job_id: str, jobs: Jobs):
    return jobs.repository.job(job_id)


@router.post('/jobs/{job_id}/cancel', response_model=Job)
async def cancel(job_id: str, jobs: Jobs):
    return jobs.cancel(job_id)


@router.get('/jobs/{job_id}/export')
def export(job_id: str, jobs: Jobs):
    return JSONResponse(jobs.repository.job(job_id).model_dump(), headers={
        'Content-Disposition': f'attachment; filename="decisionmesh-research-{job_id}.json"'})


@router.post('/benchmarks', status_code=202, response_model=Job)
async def benchmark(body: BenchmarkInput, jobs: Annotated[ResearchJobs, Depends(research_jobs)]):
    return await EvaluationService(jobs).start(body)
