"""Field types and read models shared by every CRM entity's schemas."""

from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, HttpUrl, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]
Industry = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]
Notes = Annotated[str, StringConstraints(max_length=10_000)]


def check_url(value: str) -> str:
    """Validated as an http(s) URL, stored as typed (no trailing slash added)."""
    HttpUrl(value)
    return value


Website = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500), AfterValidator(check_url)
]

Filename = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
# `type/subtype`, as the browser reports it. The store pins the upload to it.
ContentType = Annotated[str, StringConstraints(max_length=255, pattern=r"^[\w.+-]+/[\w.+-]+$")]


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRef(ReadModel):
    """Enough to name the user who made or uploaded something."""

    id: UUID
    email: str
