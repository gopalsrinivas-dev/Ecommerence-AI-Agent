import uuid

from pydantic import BaseModel, Field

from app.schemas.base import StrictInput


class Login(StrictInput):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserSummary(BaseModel):
    id: uuid.UUID
    email: str


class IdentityResponse(BaseModel):
    user: UserSummary
    provider_mode: str
