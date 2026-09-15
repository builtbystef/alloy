from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from alloy_server.integrations.mail import Email
from alloy_server.jobs.app import RETRY_ON_ERROR, defer, task
from alloy_server.jobs.resources import Resources

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@task("mail.send", retry=RETRY_ON_ERROR)
async def send_email(res: Resources, email: dict[str, Any]) -> None:
    await res.mailer.send(Email(**email))


async def queue_email(session: AsyncSession, email: Email) -> int:
    """Hands `email` to the worker's mailer, retried with backoff. Queued in
    `session`'s transaction, so nothing is sent if that does not commit."""
    return await defer(session, send_email, email=asdict(email))
