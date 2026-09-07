from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from alloy_api.config import Settings

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient
    from tests.conftest import Actor, Outbox

    NewLogin = Callable[[str], dict[str, str]]
    NewActor = Callable[[str], Actor]


def token_from(outbox: Outbox) -> str:
    return outbox[-1].text.split("/invites/")[1].split()[0]


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
    names = [w["name"] for w in client.get("/workspaces/", headers=grace).json()]
    assert names == ["My Workspace", "My Workspace"]  # her own, and Alice's

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


def test_one_pending_invitation_per_address(alice: Actor, bob: Actor):
    assert alice.post("/invites", json={"email": "grace@example.com"}).status_code == 201
    assert alice.post("/invites", json={"email": "GRACE@example.com"}).status_code == 409
    # Members cannot be invited again.
    assert alice.post("/invites", json={"email": "alice@example.com"}).status_code == 409
    # Another workspace's invitation is separate.
    assert bob.post("/invites", json={"email": "grace@example.com"}).status_code == 201


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
