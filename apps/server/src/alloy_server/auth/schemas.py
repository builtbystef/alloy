from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

Password = Field(min_length=8, max_length=128)
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class Credentials(BaseModel):
    email: EmailStr
    password: str = Password


class Signup(Credentials):
    name: Name
    invite_token: str | None = Field(default=None, min_length=1, max_length=128)


class ProfileUpdate(BaseModel):
    name: Name


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


class EmailChangeRequest(BaseModel):
    new_email: EmailStr
    current_password: str


class EmailChangeConfirmation(BaseModel):
    token: str = Token


class AccountDeletion(BaseModel):
    current_password: str


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    email_verified_at: datetime | None
    pending_email: str | None
    created_at: datetime
