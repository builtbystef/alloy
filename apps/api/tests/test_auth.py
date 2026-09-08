from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

from alloy_api.auth.cookies import SESSION_COOKIE
from alloy_api.config import Settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.conftest import Outbox

CREDENTIALS = {"email": "ada@example.com", "password": "correct horse battery"}


def verification_token(outbox: Outbox) -> str:
    return outbox[-1].text.split("/verify-email?token=")[1].split()[0]


def test_signup_sets_a_session_cookie_and_returns_the_user(client: TestClient):
    response = client.post("/auth/signup", json=CREDENTIALS)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
    assert body["email_verified_at"] is None
    assert "password" not in body
    assert "password_hash" not in body
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f"{SESSION_COOKIE}=")
    for attribute in ("HttpOnly", "Secure", "SameSite=lax", "Path=/", "Max-Age="):
        assert attribute in cookie, cookie
    assert "Domain" not in cookie  # `__Host-` cookies are bound to the exact host


def test_signup_rejects_a_taken_email(client: TestClient):
    client.post("/auth/signup", json=CREDENTIALS)
    response = client.post("/auth/signup", json={**CREDENTIALS, "email": "ADA@example.com"})
    assert response.status_code == 409


def test_signup_rejects_a_short_password(client: TestClient):
    response = client.post("/auth/signup", json={**CREDENTIALS, "password": "short"})
    assert response.status_code == 422


def test_login_with_the_right_password(client: TestClient):
    client.post("/auth/signup", json=CREDENTIALS)
    client.cookies.clear()
    response = client.post("/auth/login", json=CREDENTIALS)
    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"
    assert response.cookies[SESSION_COOKIE]


def test_login_with_the_wrong_password_or_unknown_email(client: TestClient):
    client.post("/auth/signup", json=CREDENTIALS)
    wrong = client.post("/auth/login", json={**CREDENTIALS, "password": "wrong password"})
    unknown = client.post("/auth/login", json={**CREDENTIALS, "email": "nobody@example.com"})
    assert wrong.status_code == 401
    assert unknown.status_code == 401
    assert SESSION_COOKIE not in wrong.cookies


def test_me_requires_a_valid_session_cookie(client: TestClient):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Cookie": f"{SESSION_COOKIE}=nope"}).status_code == 401
    # The token is never accepted as a bearer token.
    token = client.post("/auth/signup", json=CREDENTIALS).cookies[SESSION_COOKIE]
    client.cookies.clear()
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_me_returns_the_logged_in_user(client: TestClient):
    """The browser flow: the cookie jar carries the session."""
    client.post("/auth/signup", json=CREDENTIALS)
    response = client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "ada@example.com"


def test_logout_revokes_the_session_and_clears_the_cookie(client: TestClient):
    client.post("/auth/signup", json=CREDENTIALS)
    token = client.cookies[SESSION_COOKIE]
    response = client.post("/auth/logout")
    assert response.status_code == 204
    assert SESSION_COOKIE not in client.cookies  # cleared by the response
    # Nor does the old value work if someone still holds it.
    headers = {"Cookie": f"{SESSION_COOKIE}={token}"}
    assert client.get("/auth/me", headers=headers).status_code == 401
    assert client.post("/auth/logout", headers=headers).status_code == 401


def test_logout_all_revokes_every_session(client: TestClient):
    client.post("/auth/signup", json=CREDENTIALS)
    laptop = {"Cookie": f"{SESSION_COOKIE}={client.cookies[SESSION_COOKIE]}"}
    client.cookies.clear()
    client.post("/auth/login", json=CREDENTIALS)
    phone = {"Cookie": f"{SESSION_COOKIE}={client.cookies[SESSION_COOKIE]}"}
    assert client.get("/auth/me", headers=laptop).status_code == 200

    assert client.post("/auth/logout-all", headers=phone).status_code == 204
    assert client.get("/auth/me", headers=laptop).status_code == 401
    assert client.get("/auth/me", headers=phone).status_code == 401


def test_password_change_keeps_this_session_and_revokes_the_others(client: TestClient):
    client.post("/auth/signup", json=CREDENTIALS)
    other = {"Cookie": f"{SESSION_COOKIE}={client.cookies[SESSION_COOKIE]}"}
    client.cookies.clear()
    client.post("/auth/login", json=CREDENTIALS)

    wrong = client.post(
        "/auth/password",
        json={"current_password": "not it", "new_password": "a brand new passphrase"},
    )
    assert wrong.status_code == 401
    assert client.get("/auth/me", headers=other).status_code == 200

    response = client.post(
        "/auth/password",
        json={
            "current_password": CREDENTIALS["password"],
            "new_password": "a brand new passphrase",
        },
    )
    assert response.status_code == 204
    assert client.get("/auth/me").status_code == 200
    assert client.get("/auth/me", headers=other).status_code == 401
    old = client.post("/auth/login", json=CREDENTIALS)
    new = client.post("/auth/login", json={**CREDENTIALS, "password": "a brand new passphrase"})
    assert old.status_code == 401
    assert new.status_code == 200


def test_signup_emails_a_verification_link_that_unlocks_the_app(client: TestClient, outbox: Outbox):
    client.post("/auth/signup", json=CREDENTIALS)
    assert len(outbox) == 1
    email = outbox[0]
    assert email.to == "ada@example.com"
    assert email.subject == "Verify your email"
    token = verification_token(outbox)
    assert f"http://localhost:3000/verify-email?token={token}" in email.text
    assert email.html is not None
    assert token in email.html

    # Logged in, but only the auth routes work until the link is followed.
    assert client.get("/auth/me").status_code == 200
    assert client.get("/workspaces/").status_code == 403
    assert client.get("/workspaces/").json()["detail"] == "Email not verified"
    assert client.post("/workspaces/", json={"name": "Nope"}).status_code == 403

    # The link needs no login and works once.
    client.cookies.clear()
    verified = client.post("/auth/verify-email", json={"token": token})
    assert verified.status_code == 200, verified.text
    assert verified.json()["email"] == "ada@example.com"
    assert verified.json()["email_verified_at"] is not None
    assert client.post("/auth/verify-email", json={"token": token}).status_code == 404
    assert client.post("/auth/verify-email", json={"token": "nope"}).status_code == 404

    client.post("/auth/login", json=CREDENTIALS)
    assert client.get("/auth/me").json()["email_verified_at"] is not None
    assert client.get("/workspaces/").status_code == 200


def test_resend_replaces_the_pending_link(client: TestClient, outbox: Outbox):
    client.post("/auth/signup", json=CREDENTIALS)
    first = verification_token(outbox)
    client.cookies.clear()
    assert client.post("/auth/resend-verification").status_code == 401

    client.post("/auth/login", json=CREDENTIALS)
    assert client.post("/auth/resend-verification").status_code == 204
    assert len(outbox) == 2
    second = verification_token(outbox)
    assert second != first
    assert client.post("/auth/verify-email", json={"token": first}).status_code == 404
    assert client.post("/auth/verify-email", json={"token": second}).status_code == 200

    # Nothing left to verify.
    assert client.post("/auth/resend-verification").status_code == 409
    assert len(outbox) == 2


class TestExpired:
    @pytest.fixture
    def settings(self) -> Settings:
        """Verification links expire at once. Scoped to this class, not the module."""
        return Settings(app_name="Test API", verification_ttl=timedelta(seconds=-1))

    def test_expired_verification_link(self, client: TestClient, outbox: Outbox):
        client.post("/auth/signup", json=CREDENTIALS)
        token = verification_token(outbox)
        assert client.post("/auth/verify-email", json={"token": token}).status_code == 410
        assert client.get("/workspaces/").status_code == 403
        # A new link is the way out.
        assert client.post("/auth/resend-verification").status_code == 204
        assert client.post("/auth/verify-email", json={"token": token}).status_code == 404


def reset_token(outbox: Outbox) -> str:
    return outbox[-1].text.split("/reset-password?token=")[1].split()[0]


class TestPasswordReset:
    def test_the_link_sets_a_new_password_and_logs_in(self, client: TestClient, outbox: Outbox):
        client.post("/auth/signup", json=CREDENTIALS)
        # A second login elsewhere, to be revoked by the reset.
        other = client.post("/auth/login", json=CREDENTIALS).cookies[SESSION_COOKIE]
        client.cookies.clear()

        response = client.post("/auth/forgot-password", json={"email": "ADA@example.com"})
        assert response.status_code == 204
        assert len(outbox) == 2
        email = outbox[-1]
        assert email.to == "ada@example.com"
        assert email.subject == "Reset your password"
        assert "1 hour" in email.text
        token = reset_token(outbox)

        response = client.post(
            "/auth/reset-password", json={"token": token, "new_password": "new horse battery"}
        )
        assert response.status_code == 200
        assert response.json()["email"] == "ada@example.com"
        # Following the link proved the address.
        assert response.json()["email_verified_at"] is not None
        assert response.cookies[SESSION_COOKIE]
        assert client.get("/auth/me").status_code == 200
        assert client.get("/workspaces/").status_code == 200
        # The earlier login is out; the new password is in.
        client.cookies.clear()
        assert (
            client.get("/auth/me", headers={"Cookie": f"{SESSION_COOKIE}={other}"}).status_code
            == 401
        )
        assert client.post("/auth/login", json=CREDENTIALS).status_code == 401
        login = client.post("/auth/login", json={**CREDENTIALS, "password": "new horse battery"})
        assert login.status_code == 200
        # The link worked once.
        response = client.post(
            "/auth/reset-password", json={"token": token, "new_password": "third horse battery"}
        )
        assert response.status_code == 404

    def test_an_unknown_email_gets_the_same_answer_and_no_email(
        self, client: TestClient, outbox: Outbox
    ):
        response = client.post("/auth/forgot-password", json={"email": "nobody@example.com"})
        assert response.status_code == 204
        assert outbox == []

    def test_a_new_request_replaces_the_previous_link(self, client: TestClient, outbox: Outbox):
        client.post("/auth/signup", json=CREDENTIALS)
        client.cookies.clear()
        client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
        first = reset_token(outbox)
        client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
        second = reset_token(outbox)
        assert first != second
        body = {"token": first, "new_password": "new horse battery"}
        assert client.post("/auth/reset-password", json=body).status_code == 404
        body["token"] = second
        assert client.post("/auth/reset-password", json=body).status_code == 200

    def test_changing_the_password_while_logged_in_voids_the_link(
        self, client: TestClient, outbox: Outbox
    ):
        client.post("/auth/signup", json=CREDENTIALS)
        client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
        token = reset_token(outbox)
        change = {"current_password": CREDENTIALS["password"], "new_password": "new horse battery"}
        assert client.post("/auth/password", json=change).status_code == 204
        body = {"token": token, "new_password": "third horse battery"}
        assert client.post("/auth/reset-password", json=body).status_code == 404

    def test_the_link_rejects_a_short_password_without_spending_the_token(
        self, client: TestClient, outbox: Outbox
    ):
        client.post("/auth/signup", json=CREDENTIALS)
        client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
        token = reset_token(outbox)
        body = {"token": token, "new_password": "short"}
        assert client.post("/auth/reset-password", json=body).status_code == 422
        body = {"token": token, "new_password": "new horse battery"}
        assert client.post("/auth/reset-password", json=body).status_code == 200

    def test_a_reset_needs_no_login_and_ignores_a_stale_cookie(
        self, client: TestClient, outbox: Outbox
    ):
        client.post("/auth/signup", json=CREDENTIALS)
        client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
        token = reset_token(outbox)
        client.post("/auth/logout-all")  # the cookie in the jar is now dead
        body = {"token": token, "new_password": "new horse battery"}
        assert client.post("/auth/reset-password", json=body).status_code == 200


class TestExpiredReset:
    @pytest.fixture
    def settings(self) -> Settings:
        return Settings(app_name="Test API", password_reset_ttl=timedelta(seconds=-1))

    def test_expired_reset_link(self, client: TestClient, outbox: Outbox):
        client.post("/auth/signup", json=CREDENTIALS)
        client.post("/auth/forgot-password", json={"email": CREDENTIALS["email"]})
        token = reset_token(outbox)
        body = {"token": token, "new_password": "new horse battery"}
        assert client.post("/auth/reset-password", json=body).status_code == 410
        # The password is unchanged and the old login still works.
        assert client.post("/auth/login", json=CREDENTIALS).status_code == 200
