import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from alloy_api.models import Base, Timestamps, UUIDPrimaryKey


class User(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "users"

    # Stored lower-cased; the API normalizes on signup and login.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))

    # Null until the user follows the link emailed at signup (or accepts an
    # invitation sent to this address, which proves the same thing).
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The pending verification link, at most one at a time: a resend replaces it.
    # The email holds a random token; only its SHA-256 is stored here.
    verification_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    verification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # The pending "forgot password" link, kept the same way. Using it, or changing
    # the password while logged in, clears it.
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    password_reset_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # A requested email change, kept the same way; `email` only changes once the
    # link sent to the new address is followed.
    pending_email: Mapped[str | None] = mapped_column(String(320))
    email_change_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    email_change_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Sessions are revoked at once, but the row stays for `account_deletion_grace`
    # so logging in can undo the deletion. The purge job removes it after that.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class UserSession(UUIDPrimaryKey, Base):
    """A login. The cookie holds a random token; only its SHA-256 is stored here.

    Valid while `revoked_at` is null and `expires_at` is in the future. Logout sets
    `revoked_at` rather than deleting, so the row stays as a record of the login.
    """

    __tablename__ = "user_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="sessions")
