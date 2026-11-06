"""Resolve per-application services for HTTP handlers."""
from fastapi import Request

from backend.app.agents.registry import AgentRegistry
from backend.app.orchestration.coordinator import Coordinator
from backend.app.services.models import ModelService
from backend.app.services.analytics import AnalyticsService
from backend.app.services.runs import RunService
from backend.app.storage.runs import RunRepository


def registry(request: Request) -> AgentRegistry:
    return request.app.state.registry


def models(request: Request) -> ModelService:
    return request.app.state.models


def coordinator(request: Request) -> Coordinator:
    return request.app.state.coordinator


def history(request: Request) -> RunRepository:
    return request.app.state.history


def analytics(request: Request) -> AnalyticsService:
    return request.app.state.analytics


def run_service(request: Request) -> RunService:
    return RunService(registry(request), models(request), coordinator(request), history(request), request.app.state.enterprise)
