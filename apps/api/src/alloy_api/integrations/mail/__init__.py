from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import Depends, Request

from alloy_api.integrations.mail.base import Email, Mailer
from alloy_api.integrations.mail.console import ConsoleMailer

if TYPE_CHECKING:
    from alloy_api.config import Settings

MailProvider = Literal["console"]


def create_mailer(settings: Settings) -> Mailer:
    match settings.mail_provider:
        case "console":
            return ConsoleMailer(sender=settings.mail_from)


async def get_mailer(request: Request) -> Mailer:
    mailer: Mailer = request.state.mailer
    return mailer


MailerDep = Annotated[Mailer, Depends(get_mailer)]

__all__ = ["ConsoleMailer", "Email", "MailProvider", "Mailer", "MailerDep", "create_mailer"]
