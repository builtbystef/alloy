import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alloy_api.mail.base import Email

logger = logging.getLogger(__name__)


class ConsoleMailer:
    """Logs each message instead of sending it. The default for development and tests."""

    def __init__(self, sender: str) -> None:
        self.sender = sender

    async def send(self, email: Email) -> None:
        logger.info(
            "Outgoing email\n  From: %s\n  To: %s\n  Subject: %s\n\n%s",
            self.sender,
            email.to,
            email.subject,
            email.text,
        )
