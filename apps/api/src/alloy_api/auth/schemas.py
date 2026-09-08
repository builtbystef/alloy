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


Token = Field(min_length=1, max_length=128)


class EmailVerification(BaseModel):
    """The token from the verification link."""

    token: str = Token


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordReset(BaseModel):
    """The token from the reset link, and the password to set."""

    token: str = Token
    new_password: str = Password


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    email_verified_at: datetime | None
    created_at: datetime
