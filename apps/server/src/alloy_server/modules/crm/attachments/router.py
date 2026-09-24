from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from fastapi.responses import RedirectResponse

from alloy_server.db.session import SessionDep
from alloy_server.modules.crm.attachments import service
from alloy_server.modules.crm.attachments.dependencies import AttachmentStoreDep
from alloy_server.modules.crm.attachments.schemas import (
    AttachmentCreate,
    AttachmentResponse,
    AttachmentUpload,
)
from alloy_server.modules.crm.companies import service as companies
from alloy_server.modules.crm.contacts import service as contacts
from alloy_server.modules.crm.pagination import Page, PageOf, paginate
from alloy_server.modules.workspaces.dependencies import CanReadCrm, CanWriteCrm

router = APIRouter(tags=["attachments"])


@router.get("/contacts/{contact_id}/attachments")
async def list_contact_attachments(
    contact_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[AttachmentResponse]:
    """Newest first. Files whose upload never completed are left out."""
    contact = await contacts.get_contact(session, membership, contact_id)
    return await paginate(session, service.attachments_query(contact), page, AttachmentResponse)


@router.post("/contacts/{contact_id}/attachments", status_code=status.HTTP_201_CREATED)
async def create_contact_attachment(
    contact_id: UUID,
    body: AttachmentCreate,
    session: SessionDep,
    uploads: AttachmentStoreDep,
    membership: CanWriteCrm,
) -> AttachmentUpload:
    """Start an upload: the row is created and an upload URL returned. 413 when
    `size` is over the limit."""
    contact = await contacts.get_contact(session, membership, contact_id)
    return await service.start_upload(session, uploads, membership, contact, body)


@router.get("/companies/{company_id}/attachments")
async def list_company_attachments(
    company_id: UUID, session: SessionDep, membership: CanReadCrm, page: Annotated[Page, Query()]
) -> PageOf[AttachmentResponse]:
    """Newest first. Files whose upload never completed are left out."""
    company = await companies.get_company(session, membership, company_id)
    return await paginate(session, service.attachments_query(company), page, AttachmentResponse)


@router.post("/companies/{company_id}/attachments", status_code=status.HTTP_201_CREATED)
async def create_company_attachment(
    company_id: UUID,
    body: AttachmentCreate,
    session: SessionDep,
    uploads: AttachmentStoreDep,
    membership: CanWriteCrm,
) -> AttachmentUpload:
    """Start an upload: the row is created and an upload URL returned. 413 when
    `size` is over the limit."""
    company = await companies.get_company(session, membership, company_id)
    return await service.start_upload(session, uploads, membership, company, body)


@router.post("/attachments/{attachment_id}/complete")
async def complete_attachment(
    attachment_id: UUID,
    session: SessionDep,
    uploads: AttachmentStoreDep,
    membership: CanWriteCrm,
) -> AttachmentResponse:
    """Called after the `PUT`. 409 when the object is not in the store yet; 413, and
    the object is removed, when it is bigger than allowed. Repeating it is harmless."""
    attachment = await service.complete_upload(session, uploads, membership, attachment_id)
    return AttachmentResponse.model_validate(attachment)


@router.get("/attachments/{attachment_id}/download", status_code=status.HTTP_307_TEMPORARY_REDIRECT)
async def download_attachment(
    attachment_id: UUID,
    session: SessionDep,
    uploads: AttachmentStoreDep,
    membership: CanReadCrm,
) -> RedirectResponse:
    """Redirects to a short-lived URL that serves the file as a download."""
    url = await service.download_url(session, uploads, membership, attachment_id)
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_attachment(
    attachment_id: UUID,
    session: SessionDep,
    uploads: AttachmentStoreDep,
    membership: CanWriteCrm,
) -> Response:
    """Removes the row, then the file from the store."""
    await service.delete_attachment(session, uploads.objects, membership, attachment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
