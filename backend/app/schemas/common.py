from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard successful API envelope."""

    success: bool = True
    data: T
    error: None = None
    request_id: str


class HealthData(BaseModel):
    status: str
    service: str
    environment: str
    database: str | None = None


def success_response(data: BaseModel | dict[str, Any], request_id: str) -> dict[str, Any]:
    """Build a serializable response while keeping endpoint code concise."""

    payload = data.model_dump() if isinstance(data, BaseModel) else data
    return {"success": True, "data": payload, "error": None, "request_id": request_id}
