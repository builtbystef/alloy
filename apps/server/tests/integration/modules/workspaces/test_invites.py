from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from alloy_server.config import Settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient
    from tests.integration.conftest import Actor, Outbox

    NewLogin = Callable[[str], dict[str, str]]
    NewActor = Callable[[str], Actor]
    Join = Callable[[Actor, str, str], Actor]


GRACE = {"email": "grace@example.com", "password": "correct horse battery", "name": "Grace"}


def token_from(outbox: Outbox) -> str:
    return outbox[-1].text.split("/invites/")[1].split()[0]


def test_invite_email_escapes_the_workspace_name(alice: Actor, outbox: Outbox):
    """An admin picks the name; it must not become markup in an email from our domain."""
    name = '<a href="https://evil.example">Reset your password</a>'
    assert alice.patch("", json={"name": name}).status_code == 200
    created = alice.post("/invites", json={"email": "grace@example.com", "role": "member"})
    assert created.status_code == 201, created.text

    email = outbox[-1]
    assert email.html is not None
    assert 'evil.example">' not in email.html
    assert "&lt;a href=&quot;https://evil.example&quot;&gt;" in email.html
    # The plain-text body and the subject are not HTML, so they carry the name as typed.
    assert name in email.text
    assert name in email.subject


def test_invite_emails_a_link_the_invitee_accepts(
    client: TestClient, alice: Actor, outbox: Outbox, new_login: NewLogin
):
    created = alice.post("/invites", json={"email": "Grace@Example.com", "role": "member"})
    assert created.status_code == 201, created.text
    invite = created.json()
    assert invite["email"] == "grace@example.com"
    assert invite["role"] == "member"
    assert invite["invited_by"] == "alice@example.com"
    assert [i["id"] for i in alice.get("/invites").json()] == [invite["id"]]

    assert len(outbox) == 1
    email = outbox[0]
    assert email.to == "grace@example.com"
    assert "My Workspace" in email.subject
    token = token_from(outbox)
    assert f"http://localhost:3000/invites/{token}" in email.text
    assert email.html is not None
    assert token in email.html

    # The page shows the invitation before login.
    preview = client.get(f"/invites/{token}")
    assert preview.status_code == 200
    assert preview.json()["workspace_name"] == "My Workspace"
    assert preview.json()["email"] == "grace@example.com"
    assert preview.json()["role"] == "member"
    assert preview.json()["invited_by"] == "alice@example.com"

    # Accepting needs a login, with the invited email.
    assert client.post(f"/invites/{token}/accept").status_code == 401
    grace = new_login("grace@example.com")
    accepted = client.post(f"/invites/{token}/accept", headers=grace)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["id"] == alice.workspace
    assert accepted.json()["role"] == "member"
    assert client.get(alice.ws("/companies/"), headers=grace).status_code == 200
    joined = client.get("/workspaces/", headers=grace).json()
    assert [w["id"] for w in joined] == [alice.workspace]

    # Used up: no longer listed, no longer accepted.
    assert alice.get("/invites").json() == []
    assert client.get(f"/invites/{token}").status_code == 404
    assert client.post(f"/invites/{token}/accept", headers=grace).status_code == 404


def test_invitation_is_bound_to_the_email(
    client: TestClient, alice: Actor, outbox: Outbox, new_login: NewLogin
):
    alice.post("/invites", json={"email": "grace@example.com"})
    token = token_from(outbox)
    bob = new_login("bob@example.com")
    response = client.post(f"/invites/{token}/accept", headers=bob)
    assert response.status_code == 403
    assert client.get(alice.ws(), headers=bob).status_code == 404


def test_unknown_and_revoked_tokens(client: TestClient, alice: Actor, outbox: Outbox):
    assert client.get("/invites/nope").status_code == 404
    invite = alice.post("/invites", json={"email": "grace@example.com"}).json()
    token = token_from(outbox)
    assert alice.delete(f"/invites/{invite['id']}").status_code == 204
    assert alice.get("/invites").json() == []
    assert client.get(f"/invites/{token}").status_code == 404
    assert alice.delete(f"/invites/{invite['id']}").status_code == 404
    # Revoked: the address can be invited again.
    assert alice.post("/invites", json={"email": "grace@example.com"}).status_code == 201


def test_resend_issues_a_fresh_link_and_voids_the_old_one(
    client: TestClient, alice: Actor, outbox: Outbox, join: Join
):
    invite = alice.post("/invites", json={"email": "grace@example.com", "role": "admin"}).json()
    first = token_from(outbox)

    resent = alice.post(f"/invites/{invite['id']}/resend")
    assert resent.status_code == 200, resent.text
    assert resent.json()["id"] == invite["id"]
    assert resent.json()["expires_at"] > invite["expires_at"]
    assert len(outbox) == 2
    assert outbox[-1].to == "grace@example.com"
    second = token_from(outbox)
    assert second != first
    assert client.get(f"/invites/{first}").status_code == 404
    assert client.get(f"/invites/{second}").status_code == 200
    # Still one pending invitation for the address.
    assert [i["id"] for i in alice.get("/invites").json()] == [invite["id"]]

    # An admin may not resend an invitation for a role above their own.
    admin = join(alice, "admin@example.com", "admin")
    assert admin.post(f"/invites/{invite['id']}/resend").status_code == 403
    # Only pending invitations can be resent.
    assert alice.delete(f"/invites/{invite['id']}").status_code == 204
    assert alice.post(f"/invites/{invite['id']}/resend").status_code == 404
    assert alice.post(f"/invites/{admin.workspace}/resend").status_code == 404


def test_one_pending_invitation_per_address(alice: Actor, bob: Actor):
    assert alice.post("/invites", json={"email": "grace@example.com"}).status_code == 201
    assert alice.post("/invites", json={"email": "GRACE@example.com"}).status_code == 409
    # Members cannot be invited again.
    assert alice.post("/invites", json={"email": "alice@example.com"}).status_code == 409
    # Another workspace's invitation is separate.
    assert bob.post("/invites", json={"email": "grace@example.com"}).status_code == 201


def test_accepting_an_invitation_verifies_the_email(
    client: TestClient, alice: Actor, outbox: Outbox
):
    """The token reached the invitee's inbox, so no separate verification is needed."""
    alice.post("/invites", json={"email": "grace@example.com"})
    token = token_from(outbox)
    signup = client.post(
        "/auth/signup",
        json={**GRACE, "email": "Grace@example.com", "invite_token": token},
    )
    assert signup.status_code == 201
    assert signup.json()["email_verified_at"] is None
    assert len(outbox) == 1  # the invitation; no verification email for an invitee
    assert client.get("/workspaces/").status_code == 403
    # Until they accept, a link is still available on request.
    assert client.post("/auth/resend-verification").status_code == 204
    assert outbox[-1].subject == "Verify your email"

    accepted = client.post(f"/invites/{token}/accept")
    assert accepted.status_code == 200, accepted.text
    assert client.get("/auth/me").json()["email_verified_at"] is not None
    assert client.get("/workspaces/").status_code == 200
    # The requested verification link is spent.
    stale = outbox[-1].text.split("/verify-email?token=")[1].split()[0]
    assert client.post("/auth/verify-email", json={"token": stale}).status_code == 404


def test_signup_without_a_matching_link_still_gets_a_verification_email(
    client: TestClient, alice: Actor, outbox: Outbox
):
    """The token is what proves the inbox. A pending invitation alone, a stale
    token, or one for another address changes nothing about the signup."""
    alice.post("/invites", json={"email": "grace@example.com"})
    token = token_from(outbox)

    signup = client.post("/auth/signup", json=GRACE)
    assert signup.status_code == 201, signup.text
    assert outbox[-1].subject == "Verify your email"
    assert outbox[-1].to == "grace@example.com"

    client.cookies.clear()
    other = client.post(
        "/auth/signup", json={**GRACE, "email": "bob@example.com", "invite_token": token}
    )
    assert other.status_code == 201, other.text
    assert outbox[-1].to == "bob@example.com"

    client.cookies.clear()
    stale = client.post(
        "/auth/signup", json={**GRACE, "email": "carol@example.com", "invite_token": "nope"}
    )
    assert stale.status_code == 201, stale.text
    assert outbox[-1].to == "carol@example.com"


class TestPending:
    """The caller's own invitations, by id: the flow for someone who signed up
    without following the link, and the account settings page."""

    def test_list_accept_and_decline(
        self, client: TestClient, alice: Actor, bob: Actor, outbox: Outbox, new_login: NewLogin
    ):
        from_alice = alice.post("/invites", json={"email": "grace@example.com", "role": "admin"})
        from_bob = bob.post("/invites", json={"email": "grace@example.com"})
        assert from_alice.status_code == 201, from_alice.text
        assert from_bob.status_code == 201, from_bob.text
        # Someone else's invitation is not Grace's business.
        other = bob.post("/invites", json={"email": "other@example.com"}).json()

        grace = new_login("grace@example.com")
        pending = client.get("/invites/pending", headers=grace)
        assert pending.status_code == 200, pending.text
        assert [(i["workspace_name"], i["role"], i["invited_by"]) for i in pending.json()] == [
            ("My Workspace", "admin", "alice@example.com"),
            ("My Workspace", "member", "bob@example.com"),
        ]
        assert pending.json()[0]["id"] == from_alice.json()["id"]
        for invite in pending.json():
            assert invite["email"] == "grace@example.com"
            assert "expires_at" in invite

        accepted = client.post(f"/invites/pending/{from_alice.json()['id']}/accept", headers=grace)
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["id"] == alice.workspace
        assert accepted.json()["role"] == "admin"
        assert client.get(alice.ws(), headers=grace).status_code == 200
        assert alice.get("/invites").json() == []

        declined = client.post(f"/invites/pending/{from_bob.json()['id']}/decline", headers=grace)
        assert declined.status_code == 204, declined.text
        assert client.get("/invites/pending", headers=grace).json() == []
        assert client.get(bob.ws(), headers=grace).status_code == 404
        # Bob sees the refusal until he dismisses it; the link is dead meanwhile.
        listed = bob.get("/invites").json()
        assert [(i["id"], i["declined_at"] is not None) for i in listed] == [
            (from_bob.json()["id"], True),
            (other["id"], False),
        ]
        token = outbox[1].text.split("/invites/")[1].split()[0]
        assert client.get(f"/invites/{token}").status_code == 404
        assert bob.post(f"/invites/{from_bob.json()['id']}/resend").status_code == 404
        # A declined address can be invited again; the old row is not "pending".
        assert bob.post("/invites", json={"email": "grace@example.com"}).status_code == 201
        assert bob.delete(f"/invites/{from_bob.json()['id']}").status_code == 204
        assert all(i["declined_at"] is None for i in bob.get("/invites").json())

        # Gone from the list: neither can be acted on again.
        for invite in (from_alice, from_bob):
            url = f"/invites/pending/{invite.json()['id']}"
            assert client.post(f"{url}/accept", headers=grace).status_code == 404
            assert client.post(f"{url}/decline", headers=grace).status_code == 404

    def test_needs_a_verified_email(self, client: TestClient, alice: Actor):
        """An id proves nothing about the inbox, unlike the emailed token: anyone
        could sign up with the invited address and take the seat."""
        invite = alice.post("/invites", json={"email": "grace@example.com"}).json()
        assert client.post("/auth/signup", json=GRACE).status_code == 201
        url = f"/invites/pending/{invite['id']}"
        assert client.get("/invites/pending").status_code == 403
        assert client.post(f"{url}/accept").status_code == 403
        assert client.post(f"{url}/decline").status_code == 403
        client.cookies.clear()
        assert client.get("/invites/pending").status_code == 401

    def test_another_address_gets_404(self, client: TestClient, alice: Actor, new_login: NewLogin):
        invite = alice.post("/invites", json={"email": "grace@example.com"}).json()
        bob = new_login("bob@example.com")
        assert client.get("/invites/pending", headers=bob).json() == []
        assert (
            client.post(f"/invites/pending/{invite['id']}/accept", headers=bob).status_code == 404
        )
        assert (
            client.post(f"/invites/pending/{invite['id']}/decline", headers=bob).status_code == 404
        )
        assert alice.get("/invites").json()[0]["declined_at"] is None


def test_invitation_role_defaults_to_member_and_is_validated(alice: Actor):
    assert alice.post("/invites", json={"email": "a@example.com"}).json()["role"] == "member"
    assert alice.post("/invites", json={"email": "b@example.com", "role": "god"}).status_code == 422
    assert alice.post("/invites", json={"email": "not-an-email"}).status_code == 422


class TestExpired:
    @pytest.fixture
    def settings(self) -> Settings:
        """Invitations expire at once. Scoped to this class, not the module."""
        return Settings(app_name="Test API", invite_ttl=timedelta(seconds=-1))

    def test_expired_invitations(
        self, client: TestClient, alice: Actor, outbox: Outbox, new_actor: NewActor
    ):
        alice.post("/invites", json={"email": "grace@example.com"})
        token = token_from(outbox)
        assert alice.get("/invites").json() == []
        assert client.get(f"/invites/{token}").status_code == 410
        grace = new_actor("grace@example.com")
        assert client.post(f"/invites/{token}/accept", headers=grace.headers).status_code == 410
        # Expired: the address can be invited again.
        assert alice.post("/invites", json={"email": "grace@example.com"}).status_code == 201
