"""The centralized API error envelope, without exception or request payloads."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str
    retryable: bool


class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: str
