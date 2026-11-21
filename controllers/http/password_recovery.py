from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from pydantic import BaseModel, Field

from application.services.authentication_service import TooManyLoginAttempts
from application.services.password_recovery_service import InvalidRecoveryToken


router = APIRouter(prefix="/auth/password", tags=["password recovery"])


class RecoveryRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ResetRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    new_password: str = Field(min_length=8, max_length=1024)


@router.post("/recovery", status_code=202)
def request_recovery(payload: RecoveryRequest, request: Request, tasks: BackgroundTasks):
    service = request.app.state.password_recovery_service
    attempt_key = request.client.host if request.client else "local"
    tasks.add_task(service.request, payload.email, attempt_key)
    return {"data": {"status": "accepted"}}


@router.post("/reset")
def reset_password(payload: ResetRequest, request: Request):
    service = request.app.state.password_recovery_service
    attempt_key = request.client.host if request.client else "local"
    try:
        service.reset(payload.token, payload.new_password, attempt_key)
    except InvalidRecoveryToken:
        raise HTTPException(status_code=400, detail="Código inválido, expirado ou já utilizado.") from None
    except TooManyLoginAttempts:
        raise HTTPException(status_code=429, detail="Muitas tentativas. Aguarde e tente novamente.") from None
    return {"data": {"status": "password_changed"}}
