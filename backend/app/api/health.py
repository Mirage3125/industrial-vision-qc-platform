from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.config import Settings, get_settings
from backend.app.db.session import get_db
from backend.app.schemas.common import HealthData, success_response

router = APIRouter(tags=["system"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
DatabaseDependency = Annotated[Session, Depends(get_db)]


@router.get("/health")
def health(request: Request, settings: SettingsDependency) -> dict[str, object]:
    """Liveness probe: the API process can serve requests."""

    return success_response(
        HealthData(status="healthy", service=settings.app_name, environment=settings.environment),
        request.state.request_id,
    )


@router.get("/ready", response_model=None)
def ready(
    request: Request,
    settings: SettingsDependency,
    db: DatabaseDependency,
) -> Any:
    """Readiness probe: required database connectivity is available."""

    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "success": False,
                "data": None,
                "error": {"code": "DATABASE_NOT_READY", "message": "Database is unavailable"},
                "request_id": request.state.request_id,
            },
        )
    return success_response(
        HealthData(
            status="ready",
            service=settings.app_name,
            environment=settings.environment,
            database="reachable",
        ),
        request.state.request_id,
    )
