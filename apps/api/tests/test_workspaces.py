from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi.testclient import TestClient
    from tests.conftest import Actor

    Join = Callable[[Actor, str, str], Actor]


def test_signup_creates_a_workspace_owned_by_the_user(client: TestClient, alice: Actor):
    workspaces = client.get("/workspaces/", headers=alice.headers).json()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "My Workspace"
    assert workspaces[0]["role"] == "owner"
    assert "workspace:delete" in workspaces[0]["permissions"]

    members = alice.get("/members").json()
    assert [(m["email"], m["role"]) for m in members] == [("alice@example.com", "owner")]


def test_workspaces_require_login(client: TestClient):
    assert client.get("/workspaces/").status_code == 401
    assert client.post("/workspaces/", json={"name": "X"}).status_code == 401


def test_create_rename_and_delete_a_workspace(client: TestClient, alice: Actor):
    created = client.post("/workspaces/", json={"name": "Side project"}, headers=alice.headers)
    assert created.status_code == 201, created.text
    workspace = created.json()
    assert workspace["name"] == "Side project"
    assert workspace["role"] == "owner"
    names = [w["name"] for w in client.get("/workspaces/", headers=alice.headers).json()]
    assert names == ["My Workspace", "Side project"]

    url = f"/workspaces/{workspace['id']}"
    renamed = client.patch(url, json={"name": "Main project"}, headers=alice.headers)
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Main project"
    assert client.get(url, headers=alice.headers).json()["name"] == "Main project"

    assert client.delete(url, headers=alice.headers).status_code == 204
    assert client.get(url, headers=alice.headers).status_code == 404


def test_deleting_a_workspace_takes_its_records(client: TestClient, alice: Actor):
    company = alice.post("/companies/", json={"name": "Acme"}).json()
    alice.post("/contacts/", json={"name": "Grace", "company_id": company["id"]})
    alice.post("/tasks/", json={"title": "Call"})
    assert client.delete(alice.ws(), headers=alice.headers).status_code == 204
    assert alice.get("/contacts/").status_code == 404


def test_outsiders_get_404_for_a_workspace(client: TestClient, alice: Actor, bob: Actor):
    company = alice.post("/companies/", json={"name": "Acme"}).json()
    for path in ["", "/members", "/companies/", f"/companies/{company['id']}", "/dashboard/"]:
        assert client.get(alice.ws(path), headers=bob.headers).status_code == 404, path
    assert client.patch(alice.ws(), json={"name": "X"}, headers=bob.headers).status_code == 404
    assert client.delete(alice.ws(), headers=bob.headers).status_code == 404
    assert (
        client.post(alice.ws("/companies/"), json={"name": "X"}, headers=bob.headers).status_code
        == 404
    )
    assert client.get("/workspaces/not-a-uuid", headers=bob.headers).status_code == 422


def test_validation(client: TestClient, alice: Actor):
    assert client.post("/workspaces/", json={"name": " "}, headers=alice.headers).status_code == 422
    assert (
        client.post("/workspaces/", json={"name": "x" * 101}, headers=alice.headers).status_code
        == 422
    )


def member_id(host: Actor, email: str) -> str:
    return next(m["id"] for m in host.get("/members").json() if m["email"] == email)


def test_each_role_sees_what_it_may(client: TestClient, alice: Actor, join: Join):
    viewer = join(alice, "viewer@example.com", "viewer")
    member = join(alice, "member@example.com", "member")
    admin = join(alice, "admin@example.com", "admin")

    company = alice.post("/companies/", json={"name": "Acme"}).json()
    # Everyone reads.
    for who in (viewer, member, admin):
        assert who.get("/companies/").status_code == 200
        assert who.get(f"/companies/{company['id']}").status_code == 200
        assert who.get("/dashboard/").status_code == 200
        assert who.get("/members").status_code == 200
    # Viewers cannot write.
    assert viewer.post("/companies/", json={"name": "X"}).status_code == 403
    assert viewer.patch(f"/companies/{company['id']}", json={"name": "X"}).status_code == 403
    assert viewer.delete(f"/companies/{company['id']}").status_code == 403
    assert viewer.post("/tasks/", json={"title": "X"}).status_code == 403
    assert member.post("/companies/", json={"name": "Beta"}).status_code == 201
    # Only admins and owners manage members, the workspace, and invitations.
    for who in (viewer, member):
        assert who.get("/invites").status_code == 403
        assert who.post("/invites", json={"email": "x@example.com"}).status_code == 403
        assert who.patch("", json={"name": "X"}).status_code == 403
        assert who.delete("").status_code == 403
    assert admin.patch("", json={"name": "Renamed"}).status_code == 200
    assert admin.get("/invites").status_code == 200
    # Only owners delete.
    assert admin.delete("").status_code == 403

    roles = {m["email"]: m["role"] for m in alice.get("/members").json()}
    assert roles == {
        "alice@example.com": "owner",
        "viewer@example.com": "viewer",
        "member@example.com": "member",
        "admin@example.com": "admin",
    }
    assert client.get(alice.ws(), headers=viewer.headers).json()["permissions"] == [
        "crm:read",
        "members:read",
    ]


def test_owner_changes_roles_and_removes_members(alice: Actor, join: Join):
    viewer = join(alice, "viewer@example.com", "viewer")
    seat = member_id(alice, viewer.email)

    promoted = alice.patch(f"/members/{seat}", json={"role": "admin"})
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "admin"
    assert viewer.post("/invites", json={"email": "new@example.com"}).status_code == 201

    assert alice.delete(f"/members/{seat}").status_code == 204
    assert viewer.get("/companies/").status_code == 404
    assert alice.delete(f"/members/{seat}").status_code == 404


def test_admins_manage_only_roles_below_their_own(alice: Actor, join: Join):
    admin = join(alice, "admin@example.com", "admin")
    other_admin = join(alice, "other@example.com", "admin")
    member = join(alice, "member@example.com", "member")
    owner_seat = member_id(alice, alice.email)
    other_seat = member_id(alice, other_admin.email)
    member_seat = member_id(alice, member.email)

    assert admin.patch(f"/members/{member_seat}", json={"role": "viewer"}).status_code == 200
    assert admin.patch(f"/members/{member_seat}", json={"role": "admin"}).status_code == 403
    assert admin.patch(f"/members/{member_seat}", json={"role": "owner"}).status_code == 403
    assert admin.patch(f"/members/{other_seat}", json={"role": "member"}).status_code == 403
    assert admin.patch(f"/members/{owner_seat}", json={"role": "member"}).status_code == 403
    assert admin.delete(f"/members/{owner_seat}").status_code == 403
    assert admin.delete(f"/members/{other_seat}").status_code == 403
    assert admin.delete(f"/members/{member_seat}").status_code == 204

    def invite(role: str) -> int:
        return admin.post(
            "/invites", json={"email": f"{role}@example.com", "role": role}
        ).status_code

    assert invite("owner") == 403
    assert invite("admin") == 403
    assert invite("member") == 201


def test_a_workspace_keeps_at_least_one_owner(client: TestClient, alice: Actor, join: Join):
    admin = join(alice, "admin@example.com", "admin")
    own_seat = member_id(alice, alice.email)
    admin_seat = member_id(alice, admin.email)

    assert alice.patch(f"/members/{own_seat}", json={"role": "admin"}).status_code == 409
    assert alice.post("/leave").status_code == 409
    assert alice.delete(f"/members/{own_seat}").status_code == 409  # use leave

    assert alice.patch(f"/members/{admin_seat}", json={"role": "owner"}).status_code == 200
    assert alice.post("/leave").status_code == 204
    assert alice.get("").status_code == 404
    assert client.get(alice.ws(), headers=admin.headers).json()["role"] == "owner"


def test_anyone_can_leave_unless_last_owner(alice: Actor, join: Join):
    viewer = join(alice, "viewer@example.com", "viewer")
    assert viewer.post("/leave").status_code == 204
    assert viewer.get("").status_code == 404
    assert [m["email"] for m in alice.get("/members").json()] == ["alice@example.com"]
