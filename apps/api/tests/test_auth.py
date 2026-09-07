from typing import TYPE_CHECKING

from alloy_api.auth.cookies import SESSION_COOKIE

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

CREDENTIALS = {"email": "ada@example.com", "password": "correct horse battery"}


def test_signup_sets_a_session_cookie_and_returns_the_user(client: TestClient):
    response = client.post("/auth/signup", json=CREDENTIALS)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "ada@example.com"
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
