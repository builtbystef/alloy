from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, HttpUrl, StringConstraints
from pydantic_core import PydanticCustomError

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

# No control characters: the name ends up in a `Content-Disposition` header.
Filename = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=255, pattern=r"^[^\x00-\x1f\x7f]+$"
    ),
]
# `type/subtype`, as the browser reports it. The store pins the upload to it.
ContentType = Annotated[str, StringConstraints(max_length=255, pattern=r"^[\w.+-]+/[\w.+-]+$")]


def reject_null(value: object) -> object:
    if value is None:
        raise PydanticCustomError("null_not_allowed", "Field may be left out, but not null")
    return value


# `Annotated[Name | None, NotNull] = None` in a PATCH body: may be left out, not
# sent as null. The other optional fields take null to clear them.
NotNull = AfterValidator(reject_null)


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserRef(ResponseModel):
    id: UUID
    email: str
