from typing import TYPE_CHECKING

from alloy_api.mail import Email

if TYPE_CHECKING:
    from alloy_api.workspaces.models import WorkspaceInvite


def invite_link(frontend_url: str, token: str) -> str:
    return f"{frontend_url.rstrip('/')}/invites/{token}"


def invite_email(invite: WorkspaceInvite, token: str, frontend_url: str) -> Email:
    """Needs `invite.workspace` and `invite.invited_by` loaded."""
    workspace = invite.workspace.name
    inviter = invite.invited_by.email if invite.invited_by else "Someone"
    link = invite_link(frontend_url, token)
    expires = invite.expires_at.strftime("%d %B %Y")
    text = (
        f'{inviter} invited you to join the workspace "{workspace}" as {invite.role.value}.\n'
        f"\n"
        f"Accept the invitation here:\n"
        f"{link}\n"
        f"\n"
        f"The link works until {expires} and only for {invite.email}.\n"
        f"If you were not expecting this, you can ignore this email."
    )
    html = (
        f"<p>{inviter} invited you to join the workspace <strong>{workspace}</strong> "
        f"as <strong>{invite.role.value}</strong>.</p>"
        f'<p><a href="{link}">Accept the invitation</a></p>'
        f"<p>The link works until {expires} and only for {invite.email}. "
        f"If you were not expecting this, you can ignore this email.</p>"
    )
    return Email(to=invite.email, subject=f"You're invited to {workspace}", text=text, html=html)
