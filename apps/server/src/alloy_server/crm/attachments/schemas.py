from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from alloy_server.crm.schemas import ContentType, Filename, ReadModel, UserRef


class AttachmentCreate(BaseModel):
    """What the client knows before uploading. `size` is checked against the limit
    here and again against the stored object on completion."""

    filename: Filename
    content_type: ContentType
    size: int = Field(ge=1, description="Bytes.")


class AttachmentRead(ReadModel):
    id: UUID
    contact_id: UUID | None
    company_id: UUID | None
    filename: str
    content_type: str
    size: int
    uploaded_by: UserRef | None
    uploaded_at: datetime | None
    created_at: datetime


class AttachmentUpload(BaseModel):
    """Step one of an upload: `PUT` the file to `upload_url` with the `Content-Type`
    and `size` given at creation (the URL accepts nothing else), then
    `POST .../attachments/{id}/complete`."""

    attachment: AttachmentRead
    upload_url: str
    expires_at: datetime
