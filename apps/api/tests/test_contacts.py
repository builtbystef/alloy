from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.conftest import Actor

GRACE = {
    "name": "Grace Hopper",
    "email": "grace@example.com",
    "phone": "+1 555 0100",
    "job_title": "Rear Admiral",
}


def test_contacts_require_login(client: TestClient, alice: Actor):
    assert client.get(alice.ws("/contacts/")).status_code == 401


def test_create_and_read_a_contact(alice: Actor):
    created = alice.post("/contacts/", json=GRACE)
    assert created.status_code == 201, created.text
    contact = created.json()
    assert contact["name"] == "Grace Hopper"
    assert contact["email"] == "grace@example.com"
    assert contact["status"] == "lead"
    assert contact["company"] is None
    assert contact["last_contacted_at"] is None

    assert alice.get(f"/contacts/{contact['id']}").json() == contact


def test_contact_linked_to_a_company(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    contact = alice.post("/contacts/", json={**GRACE, "company_id": company["id"]}).json()
    assert contact["company"] == {"id": company["id"], "name": "Navy"}

    at_company = alice.get(f"/companies/{company['id']}/contacts").json()
    assert [c["id"] for c in at_company] == [contact["id"]]

    # Deleting the company keeps the contact and clears the link.
    alice.delete(f"/companies/{company['id']}")
    assert alice.get(f"/contacts/{contact['id']}").json()["company"] is None


def test_contact_cannot_link_to_another_users_company(alice: Actor, bob: Actor):
    company = bob.post("/companies/", json={"name": "Navy"}).json()
    response = alice.post("/contacts/", json={**GRACE, "company_id": company["id"]})
    assert response.status_code == 404


def test_search_and_filter_contacts(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    alice.post("/contacts/", json={**GRACE, "company_id": company["id"]})
    alice.post("/contacts/", json={"name": "Alan Turing", "status": "active"})
    alice.post("/contacts/", json={"name": "Ada Lovelace", "job_title": "Analyst"})

    names = [c["name"] for c in alice.get("/contacts/").json()]
    assert names == ["Ada Lovelace", "Alan Turing", "Grace Hopper"]

    def search(**params: str) -> list[str]:
        return [c["name"] for c in alice.get("/contacts/", params=params).json()]

    assert search(q="hopper") == ["Grace Hopper"]
    assert search(q="grace@") == ["Grace Hopper"]
    assert search(q="analyst") == ["Ada Lovelace"]
    assert search(q="navy") == ["Grace Hopper"]  # company name
    assert search(status="active") == ["Alan Turing"]
    assert search(company_id=company["id"]) == ["Grace Hopper"]


def test_update_and_delete_a_contact(alice: Actor):
    contact = alice.post("/contacts/", json=GRACE).json()
    response = alice.patch(
        f"/contacts/{contact['id']}",
        json={"status": "active", "phone": None, "last_contacted_at": "2026-09-01T10:00:00Z"},
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["status"] == "active"
    assert updated["phone"] is None
    assert updated["name"] == "Grace Hopper"
    assert datetime.fromisoformat(updated["last_contacted_at"]) == datetime(
        2026, 9, 1, 10, tzinfo=UTC
    )

    assert alice.delete(f"/contacts/{contact['id']}").status_code == 204
    assert alice.get(f"/contacts/{contact['id']}").status_code == 404


def test_users_only_see_their_own_contacts(alice: Actor, bob: Actor):
    contact = alice.post("/contacts/", json=GRACE).json()
    url = f"/contacts/{contact['id']}"
    assert bob.get("/contacts/").json() == []
    assert bob.get(url).status_code == 404
    assert bob.patch(url, json={"name": "X"}).status_code == 404
    assert bob.delete(url).status_code == 404
    assert bob.get(f"{url}/activities").status_code == 404
    assert bob.post(f"{url}/activities", json={"type": "note"}).status_code == 404


def test_validation(alice: Actor):
    assert alice.post("/contacts/", json={"name": " "}).status_code == 422
    assert alice.post("/contacts/", json={**GRACE, "email": "nope"}).status_code == 422
    assert alice.post("/contacts/", json={**GRACE, "status": "vip"}).status_code == 422


# Activities


def test_activity_feed_is_newest_first(alice: Actor):
    contact = alice.post("/contacts/", json=GRACE).json()
    url = f"/contacts/{contact['id']}/activities"
    assert alice.get(url).json() == []

    first = alice.post(url, json={"type": "note", "notes": "Prefers email"})
    assert first.status_code == 201, first.text
    assert first.json()["type"] == "note"
    assert first.json()["notes"] == "Prefers email"
    assert first.json()["contact_id"] == contact["id"]

    alice.post(url, json={"type": "call"})
    feed = alice.get(url).json()
    assert [a["type"] for a in feed] == ["call", "note"]


def test_logging_contact_updates_last_contacted(alice: Actor):
    contact = alice.post("/contacts/", json=GRACE).json()
    url = f"/contacts/{contact['id']}"

    alice.post(f"{url}/activities", json={"type": "note"})
    assert alice.get(url).json()["last_contacted_at"] is None

    before = datetime.now(UTC)
    alice.post(f"{url}/activities", json={"type": "meeting"})
    last_contacted = alice.get(url).json()["last_contacted_at"]
    assert datetime.fromisoformat(last_contacted) >= before


def test_activities_go_with_their_contact(alice: Actor):
    contact = alice.post("/contacts/", json=GRACE).json()
    alice.post(f"/contacts/{contact['id']}/activities", json={"type": "email"})
    assert alice.delete(f"/contacts/{contact['id']}").status_code == 204
    assert alice.get(f"/contacts/{contact['id']}/activities").status_code == 404
