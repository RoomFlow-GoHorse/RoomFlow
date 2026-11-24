from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from infrastructure.persistence.readiness import DatabaseNotReady


class HealthData(BaseModel):
    status: str


class HealthResponse(BaseModel):
    data: HealthData


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(data=HealthData(status="ok"))


@router.get("/ready")
def readiness_check(request: Request) -> dict:
    check = getattr(request.app.state, "readiness", None)
    try:
        if check:
            check()
    except DatabaseNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return {"data": {"status": "ready", "persistence": request.app.state.persistence}}
