from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

GRACE = {
    "name": "Grace Hopper",
    "email": "grace@example.com",
    "phone": "+1 555 0100",
    "job_title": "Rear Admiral",
}


def test_contacts_require_login(client: TestClient):
    assert client.get("/contacts/").status_code == 401


def test_create_and_read_a_contact(client: TestClient, alice: dict[str, str]):
    created = client.post("/contacts/", json=GRACE, headers=alice)
    assert created.status_code == 201, created.text
    contact = created.json()
    assert contact["name"] == "Grace Hopper"
    assert contact["email"] == "grace@example.com"
    assert contact["status"] == "lead"
    assert contact["company"] is None
    assert contact["last_contacted_at"] is None

    assert client.get(f"/contacts/{contact['id']}", headers=alice).json() == contact


def test_contact_linked_to_a_company(client: TestClient, alice: dict[str, str]):
    company = client.post("/companies/", json={"name": "Navy"}, headers=alice).json()
    contact = client.post(
        "/contacts/", json={**GRACE, "company_id": company["id"]}, headers=alice
    ).json()
    assert contact["company"] == {"id": company["id"], "name": "Navy"}

    at_company = client.get(f"/companies/{company['id']}/contacts", headers=alice).json()
    assert [c["id"] for c in at_company] == [contact["id"]]

    # Deleting the company keeps the contact and clears the link.
    client.delete(f"/companies/{company['id']}", headers=alice)
    assert client.get(f"/contacts/{contact['id']}", headers=alice).json()["company"] is None


def test_contact_cannot_link_to_another_users_company(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    company = client.post("/companies/", json={"name": "Navy"}, headers=bob).json()
    response = client.post("/contacts/", json={**GRACE, "company_id": company["id"]}, headers=alice)
    assert response.status_code == 404


def test_search_and_filter_contacts(client: TestClient, alice: dict[str, str]):
    company = client.post("/companies/", json={"name": "Navy"}, headers=alice).json()
    client.post("/contacts/", json={**GRACE, "company_id": company["id"]}, headers=alice)
    client.post("/contacts/", json={"name": "Alan Turing", "status": "active"}, headers=alice)
    client.post("/contacts/", json={"name": "Ada Lovelace", "job_title": "Analyst"}, headers=alice)

    names = [c["name"] for c in client.get("/contacts/", headers=alice).json()]
    assert names == ["Ada Lovelace", "Alan Turing", "Grace Hopper"]

    def search(**params: str) -> list[str]:
        return [c["name"] for c in client.get("/contacts/", params=params, headers=alice).json()]

    assert search(q="hopper") == ["Grace Hopper"]
    assert search(q="grace@") == ["Grace Hopper"]
    assert search(q="analyst") == ["Ada Lovelace"]
    assert search(q="navy") == ["Grace Hopper"]  # company name
    assert search(status="active") == ["Alan Turing"]
    assert search(company_id=company["id"]) == ["Grace Hopper"]


def test_update_and_delete_a_contact(client: TestClient, alice: dict[str, str]):
    contact = client.post("/contacts/", json=GRACE, headers=alice).json()
    response = client.patch(
        f"/contacts/{contact['id']}",
        json={"status": "active", "phone": None, "last_contacted_at": "2026-09-01T10:00:00Z"},
        headers=alice,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "active"
    assert updated["phone"] is None
    assert updated["name"] == "Grace Hopper"
    assert datetime.fromisoformat(updated["last_contacted_at"]) == datetime(
        2026, 9, 1, 10, tzinfo=UTC
    )

    assert client.delete(f"/contacts/{contact['id']}", headers=alice).status_code == 204
    assert client.get(f"/contacts/{contact['id']}", headers=alice).status_code == 404


def test_users_only_see_their_own_contacts(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    contact = client.post("/contacts/", json=GRACE, headers=alice).json()
    url = f"/contacts/{contact['id']}"
    assert client.get("/contacts/", headers=bob).json() == []
    assert client.get(url, headers=bob).status_code == 404
    assert client.patch(url, json={"name": "X"}, headers=bob).status_code == 404
    assert client.delete(url, headers=bob).status_code == 404
    assert client.get(f"{url}/activities", headers=bob).status_code == 404
    assert client.post(f"{url}/activities", json={"type": "note"}, headers=bob).status_code == 404


def test_validation(client: TestClient, alice: dict[str, str]):
    assert client.post("/contacts/", json={"name": " "}, headers=alice).status_code == 422
    assert (
        client.post("/contacts/", json={**GRACE, "email": "nope"}, headers=alice).status_code == 422
    )
    assert (
        client.post("/contacts/", json={**GRACE, "status": "vip"}, headers=alice).status_code == 422
    )


# Activities


def test_activity_feed_is_newest_first(client: TestClient, alice: dict[str, str]):
    contact = client.post("/contacts/", json=GRACE, headers=alice).json()
    url = f"/contacts/{contact['id']}/activities"
    assert client.get(url, headers=alice).json() == []

    first = client.post(url, json={"type": "note", "notes": "Prefers email"}, headers=alice)
    assert first.status_code == 201, first.text
    assert first.json()["type"] == "note"
    assert first.json()["notes"] == "Prefers email"
    assert first.json()["contact_id"] == contact["id"]

    client.post(url, json={"type": "call"}, headers=alice)
    feed = client.get(url, headers=alice).json()
    assert [a["type"] for a in feed] == ["call", "note"]


def test_logging_contact_updates_last_contacted(client: TestClient, alice: dict[str, str]):
    contact = client.post("/contacts/", json=GRACE, headers=alice).json()
    url = f"/contacts/{contact['id']}"

    client.post(f"{url}/activities", json={"type": "note"}, headers=alice)
    assert client.get(url, headers=alice).json()["last_contacted_at"] is None

    before = datetime.now(UTC)
    client.post(f"{url}/activities", json={"type": "meeting"}, headers=alice)
    last_contacted = client.get(url, headers=alice).json()["last_contacted_at"]
    assert datetime.fromisoformat(last_contacted) >= before


def test_activities_go_with_their_contact(client: TestClient, alice: dict[str, str]):
    contact = client.post("/contacts/", json=GRACE, headers=alice).json()
    client.post(f"/contacts/{contact['id']}/activities", json={"type": "email"}, headers=alice)
    assert client.delete(f"/contacts/{contact['id']}", headers=alice).status_code == 204
    assert client.get(f"/contacts/{contact['id']}/activities", headers=alice).status_code == 404
