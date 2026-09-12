from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Email:
    to: str
    subject: str
    text: str
    html: str | None = None


class Mailer(Protocol):
    """Implement this to add a provider, then return it from `create_mailer`.
    Nothing else in the app knows which one is in use."""

    async def send(self, email: Email) -> None: ...
