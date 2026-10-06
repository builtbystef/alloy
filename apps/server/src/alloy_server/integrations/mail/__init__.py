from typing import TYPE_CHECKING, Literal

from alloy_server.integrations.mail.base import Email, Mailer
from alloy_server.integrations.mail.console import ConsoleMailer

if TYPE_CHECKING:
    from alloy_server.config import Settings

MailProvider = Literal["console"]


def create_mailer(settings: Settings) -> Mailer:
    match settings.mail_provider:
        case "console":
            return ConsoleMailer(sender=settings.mail_from)


__all__ = ["ConsoleMailer", "Email", "MailProvider", "Mailer", "create_mailer"]
