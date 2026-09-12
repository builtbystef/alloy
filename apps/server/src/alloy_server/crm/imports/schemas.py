from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from alloy_server.crm.imports.models import ImportKind, ImportStatus
from alloy_server.crm.schemas import Filename, ReadModel, UserRef


class ImportCreate(BaseModel):
    """What the client knows before uploading the CSV."""

    kind: ImportKind
    filename: Filename
    size: int = Field(ge=1, description="Bytes.")


class RowError(BaseModel):
    row: int = Field(description="Line number in the file; the header is line 1.")
    message: str


class ImportRead(ReadModel):
    id: UUID
    kind: ImportKind
    status: ImportStatus
    filename: str
    size: int
    requested_by: UserRef | None
    started_at: datetime | None
    finished_at: datetime | None
    total_rows: int
    created_count: int
    skipped_count: int
    failed_count: int
    errors: list[RowError]
    error: str | None = Field(description="Why the import could not finish, if it could not.")
    created_at: datetime


class ImportUpload(BaseModel):
    """Step one of an import: `PUT` the CSV to `upload_url` as `text/csv` with the
    `size` given at creation, then `POST .../imports/{id}/start`."""

    import_: ImportRead = Field(alias="import")
    upload_url: str
    expires_at: datetime

    model_config = ConfigDict(populate_by_name=True)
