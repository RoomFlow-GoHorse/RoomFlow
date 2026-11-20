from fastapi import Request

from application.services.space_service import SpaceService


def get_space_service(request: Request) -> SpaceService:
    return SpaceService(repository=request.app.state.space_repository)
