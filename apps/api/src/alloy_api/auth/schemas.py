from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Password = Field(min_length=8, max_length=128)


class Credentials(BaseModel):
    email: EmailStr
    password: str = Password


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Password


class EmailVerification(BaseModel):
    """The token from the verification link."""

    token: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    email_verified_at: datetime | None
    created_at: datetime
