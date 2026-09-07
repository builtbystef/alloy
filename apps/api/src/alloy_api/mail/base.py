from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Email:
    """One outgoing message. `text` is always set; `html` is an optional richer copy."""

    to: str
    subject: str
    text: str
    html: str | None = None


class Mailer(Protocol):
    """What the app needs from an email provider. Implement it to add one.

    Implementations take their credentials in `__init__` and are chosen by
    `create_mailer` from `ALLOY_MAIL_PROVIDER`; nothing else in the app knows
    which one is in use.
    """

    async def send(self, email: Email) -> None: ...
