from typing import Any, Generic, TypeVar
from pydantic import BaseModel

DataT = TypeVar("DataT")

class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool
    event_id: str | None = None

class ErrorResponse(BaseModel):
    error: ErrorDetail

class SuccessResponse(BaseModel, Generic[DataT]):
    data: DataT

def success(data: Any) -> dict[str, Any]:
    return {"data": data}

def error(code: str, message: str, retryable: bool, event_id: str | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "retryable": retryable, "event_id": event_id}}
