from typing import TYPE_CHECKING

from alloy_api.mail import Email

if TYPE_CHECKING:
    from datetime import timedelta

    from alloy_api.auth.models import User


def verification_link(frontend_url: str, token: str) -> str:
    return f"{frontend_url.rstrip('/')}/verify-email?token={token}"


def verification_email(user: User, token: str, frontend_url: str) -> Email:
    link = verification_link(frontend_url, token)
    text = (
        f"Confirm that {user.email} is your email address to finish setting up your account.\n"
        f"\n"
        f"Verify your email here:\n"
        f"{link}\n"
        f"\n"
        f"The link works once. If you did not create an account, you can ignore this email."
    )
    html = (
        f"<p>Confirm that <strong>{user.email}</strong> is your email address to finish "
        f"setting up your account.</p>"
        f'<p><a href="{link}">Verify your email</a></p>'
        f"<p>The link works once. If you did not create an account, "
        f"you can ignore this email.</p>"
    )
    return Email(to=user.email, subject="Verify your email", text=text, html=html)


def password_reset_link(frontend_url: str, token: str) -> str:
    return f"{frontend_url.rstrip('/')}/reset-password?token={token}"


def password_reset_email(user: User, token: str, frontend_url: str, ttl: timedelta) -> Email:
    link = password_reset_link(frontend_url, token)
    validity = describe_duration(ttl)
    text = (
        f"Someone asked to reset the password for {user.email}.\n"
        f"\n"
        f"Choose a new password here:\n"
        f"{link}\n"
        f"\n"
        f"The link works once, for {validity}. If you did not ask for this, you can "
        f"ignore this email: your password stays as it is."
    )
    html = (
        f"<p>Someone asked to reset the password for <strong>{user.email}</strong>.</p>"
        f'<p><a href="{link}">Choose a new password</a></p>'
        f"<p>The link works once, for {validity}. If you did not ask for this, you can "
        f"ignore this email: your password stays as it is.</p>"
    )
    return Email(to=user.email, subject="Reset your password", text=text, html=html)


def email_change_link(frontend_url: str, token: str) -> str:
    return f"{frontend_url.rstrip('/')}/confirm-email?token={token}"


def email_change_email(new_email: str, token: str, frontend_url: str, ttl: timedelta) -> Email:
    link = email_change_link(frontend_url, token)
    validity = describe_duration(ttl)
    text = (
        f"Someone asked to move their account to {new_email}.\n"
        f"\n"
        f"Confirm the new address here:\n"
        f"{link}\n"
        f"\n"
        f"The link works once, for {validity}. If this was not you, you can ignore "
        f"this email: nothing changes."
    )
    html = (
        f"<p>Someone asked to move their account to <strong>{new_email}</strong>.</p>"
        f'<p><a href="{link}">Confirm the new address</a></p>'
        f"<p>The link works once, for {validity}. If this was not you, you can ignore "
        f"this email: nothing changes.</p>"
    )
    return Email(to=new_email, subject="Confirm your new email", text=text, html=html)


def email_changed_notice(old_email: str, new_email: str) -> Email:
    """So a hijacked account is noticed."""
    text = (
        f"The email address of your account was changed from {old_email} to {new_email}.\n"
        f"\n"
        f"If you made this change, there is nothing to do. If you did not, reply to this "
        f"email as soon as possible."
    )
    html = (
        f"<p>The email address of your account was changed from <strong>{old_email}</strong> "
        f"to <strong>{new_email}</strong>.</p>"
        f"<p>If you made this change, there is nothing to do. If you did not, reply to this "
        f"email as soon as possible.</p>"
    )
    return Email(to=old_email, subject="Your email address was changed", text=text, html=html)


def account_deletion_email(user: User, frontend_url: str, grace: timedelta) -> Email:
    link = f"{frontend_url.rstrip('/')}/login"
    validity = describe_duration(grace)
    text = (
        f"Your account {user.email} is scheduled for deletion.\n"
        f"\n"
        f"It will be removed for good in {validity}, along with every workspace where you "
        f"were the only member. To keep it, log in before then:\n"
        f"{link}\n"
        f"\n"
        f"If you did not ask for this, log in now and change your password."
    )
    html = (
        f"<p>Your account <strong>{user.email}</strong> is scheduled for deletion.</p>"
        f"<p>It will be removed for good in {validity}, along with every workspace where "
        f'you were the only member. To keep it, <a href="{link}">log in</a> before then.</p>'
        f"<p>If you did not ask for this, log in now and change your password.</p>"
    )
    return Email(to=user.email, subject="Your account will be deleted", text=text, html=html)


def describe_duration(duration: timedelta) -> str:
    """`timedelta(hours=1)` → "1 hour"; `timedelta(days=2)` → "2 days"; else minutes."""
    seconds = int(duration.total_seconds())
    for unit, size in (("day", 86400), ("hour", 3600), ("minute", 60)):
        if seconds >= size and seconds % size == 0:
            count = seconds // size
            return f"{count} {unit}" if count == 1 else f"{count} {unit}s"
    return f"{max(seconds, 1)} seconds"
