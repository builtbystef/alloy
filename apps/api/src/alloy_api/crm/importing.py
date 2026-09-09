import csv
import io
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import ValidationError
from sqlalchemy import select

from alloy_api.crm.models import Company, Contact, Import, ImportKind, ImportStatus
from alloy_api.crm.schemas import CompanyCreate, ContactCreate
from alloy_api.models import utcnow

if TYPE_CHECKING:
    from collections.abc import Iterator
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

    from alloy_api.storage import ObjectStore

logger = logging.getLogger(__name__)

# Enough to show what is wrong with a file without storing one message per row.
MAX_ROW_ERRORS = 100

CONTACT_COLUMNS = frozenset({"name", "email", "phone", "job_title", "status", "company"})
COMPANY_COLUMNS = frozenset({"name", "website", "industry", "notes"})


class ImportFileError(ValueError):
    """The file cannot be read at all, as opposed to one row being wrong."""

    NOT_UTF8 = "The file is not UTF-8 encoded"
    NO_NAME_COLUMN = "The header row has no 'name' column"


@dataclass(slots=True)
class ImportReport:
    total_rows: int = 0
    created: int = 0
    skipped: int = 0
    failed: int = 0
    errors: list[dict[str, object]] = field(default_factory=list)

    def fail(self, row: int, message: str) -> None:
        self.failed += 1
        if len(self.errors) < MAX_ROW_ERRORS:
            self.errors.append({"row": row, "message": message})


def normalize_header(name: str | None) -> str:
    return (name or "").strip().lower().replace(" ", "_")


def read_rows(data: bytes, columns: frozenset[str]) -> Iterator[tuple[int, dict[str, str]]]:
    """`(line number, {column: value})` per row, with only the known columns and
    without blank cells, so a blank takes the field's default the way a `POST` body
    without it would. Raises `ImportFileError` for bad encoding or a missing header."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportFileError(ImportFileError.NOT_UTF8) from exc
    reader = csv.reader(io.StringIO(text, newline=""))
    header = [normalize_header(name) for name in next(reader, [])]
    if "name" not in header:
        raise ImportFileError(ImportFileError.NO_NAME_COLUMN)
    wanted = [(index, name) for index, name in enumerate(header) if name in columns]
    for values in reader:
        if not any(value.strip() for value in values):
            continue  # a blank line
        row = {
            name: values[index].strip()
            for index, name in wanted
            if index < len(values) and values[index].strip()
        }
        yield reader.line_num, row


def validation_message(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc']) or 'row'}: {error['msg']}"
        for error in exc.errors()
    )


async def import_companies(
    session: AsyncSession, workspace_id: UUID, data: bytes, created_by_user_id: UUID | None
) -> ImportReport:
    """Rows are credited to the user who requested the import."""
    report = ImportReport()
    existing = {
        name.lower()
        for name in await session.scalars(
            select(Company.name).where(Company.workspace_id == workspace_id)
        )
    }
    for line, row in read_rows(data, COMPANY_COLUMNS):
        report.total_rows += 1
        try:
            body = CompanyCreate.model_validate(row)
        except ValidationError as exc:
            report.fail(line, validation_message(exc))
            continue
        if body.name.lower() in existing:
            report.skipped += 1
            continue
        session.add(
            Company(
                workspace_id=workspace_id,
                created_by_user_id=created_by_user_id,
                **body.model_dump(),
            )
        )
        existing.add(body.name.lower())
        report.created += 1
    return report


async def import_contacts(
    session: AsyncSession, workspace_id: UUID, data: bytes, created_by_user_id: UUID | None
) -> ImportReport:
    report = ImportReport()
    existing_emails = {
        email.lower()
        for email in await session.scalars(
            select(Contact.email).where(Contact.workspace_id == workspace_id)
        )
        if email
    }
    companies: dict[str, Company] = {
        company.name.lower(): company
        for company in await session.scalars(
            select(Company).where(Company.workspace_id == workspace_id)
        )
    }
    for line, row in read_rows(data, CONTACT_COLUMNS):
        report.total_rows += 1
        company_name = row.pop("company", None)
        try:
            body = ContactCreate.model_validate(row)
        except ValidationError as exc:
            report.fail(line, validation_message(exc))
            continue
        if body.email is not None and body.email.lower() in existing_emails:
            report.skipped += 1
            continue
        contact = Contact(
            workspace_id=workspace_id, created_by_user_id=created_by_user_id, **body.model_dump()
        )
        if company_name is not None:
            company = companies.get(company_name.lower())
            if company is None:
                company = Company(
                    workspace_id=workspace_id,
                    created_by_user_id=created_by_user_id,
                    name=company_name[:200],
                )
                session.add(company)
                companies[company_name.lower()] = company
            contact.company = company
        session.add(contact)
        if body.email is not None:
            existing_emails.add(body.email.lower())
        report.created += 1
    return report


async def run_import(session: AsyncSession, store: ObjectStore, import_id: UUID) -> None:
    """Load the file of `import_id` and record the outcome on the row.

    Rows are written in one transaction with the final status, so a run that dies
    halfway leaves nothing behind and can simply be run again. The CSV is removed
    from the store at the end either way.
    """
    record = await session.get(Import, import_id)
    if record is None or record.status not in {ImportStatus.QUEUED, ImportStatus.RUNNING}:
        logger.warning("Import %s is not waiting to run; skipping", import_id)
        return
    record.status = ImportStatus.RUNNING
    record.started_at = utcnow()
    await session.commit()

    try:
        data = await store.get(record.key)
        if record.kind is ImportKind.CONTACTS:
            report = await import_contacts(
                session, record.workspace_id, data, record.requested_by_user_id
            )
        else:
            report = await import_companies(
                session, record.workspace_id, data, record.requested_by_user_id
            )
    except Exception as exc:
        logger.exception("Import %s failed", import_id)
        await session.rollback()
        record = await session.get_one(Import, import_id)
        record.status = ImportStatus.FAILED
        record.error = str(exc)[:1000] or type(exc).__name__
    else:
        record.status = ImportStatus.DONE
        record.total_rows = report.total_rows
        record.created_count = report.created
        record.skipped_count = report.skipped
        record.failed_count = report.failed
        record.errors = report.errors
    record.finished_at = utcnow()
    await session.commit()
    await store.delete(record.key)
