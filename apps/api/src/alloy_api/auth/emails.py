from typing import TYPE_CHECKING

from alloy_api.mail import Email

if TYPE_CHECKING:
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
