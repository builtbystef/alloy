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

    at_company = alice.get(f"/companies/{company['id']}/contacts").json()["items"]
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

    names = [c["name"] for c in alice.get("/contacts/").json()["items"]]
    assert names == ["Ada Lovelace", "Alan Turing", "Grace Hopper"]

    def search(**params: str) -> list[str]:
        return [c["name"] for c in alice.get("/contacts/", params=params).json()["items"]]

    assert search(q="hopper") == ["Grace Hopper"]
    assert search(q="grace@") == ["Grace Hopper"]
    assert search(q="analyst") == ["Ada Lovelace"]
    assert search(q="navy") == ["Grace Hopper"]  # company name
    assert search(status="active") == ["Alan Turing"]
    assert search(company_id=company["id"]) == ["Grace Hopper"]


def test_lists_are_paged_with_a_total(alice: Actor):
    for name in ["Ada", "Alan", "Grace", "Linus"]:
        alice.post("/contacts/", json={"name": name})

    page = alice.get("/contacts/", params={"limit": 3}).json()
    assert page["total"] == 4
    assert page["limit"] == 3
    assert page["offset"] == 0
    assert [c["name"] for c in page["items"]] == ["Ada", "Alan", "Grace"]

    rest = alice.get("/contacts/", params={"limit": 3, "offset": 3}).json()
    assert [c["name"] for c in rest["items"]] == ["Linus"]
    assert rest["total"] == 4

    beyond = alice.get("/contacts/", params={"offset": 10}).json()
    assert beyond == {"items": [], "total": 4, "limit": 100, "offset": 10}

    # The total counts what the filters match, not the workspace.
    filtered = alice.get("/contacts/", params={"q": "a", "limit": 1}).json()
    assert filtered["total"] == 3  # Ada, Alan, Grace; not Linus
    assert len(filtered["items"]) == 1
    assert alice.get("/contacts/", params={"limit": 0}).status_code == 422
    assert alice.get("/contacts/", params={"limit": 501}).status_code == 422


def test_sort_contacts(alice: Actor):
    navy = alice.post("/companies/", json={"name": "Navy"}).json()
    acme = alice.post("/companies/", json={"name": "Acme"}).json()
    alice.post("/contacts/", json={"name": "Grace", "company_id": navy["id"], "status": "active"})
    alice.post("/contacts/", json={"name": "Ada", "company_id": acme["id"], "status": "lead"})
    alice.post("/contacts/", json={"name": "Alan", "last_contacted_at": "2026-09-01T10:00:00Z"})

    def names(**params: str) -> list[str]:
        response = alice.get("/contacts/", params=params)
        assert response.status_code == 200, response.text
        return [c["name"] for c in response.json()["items"]]

    assert names(sort="name", order="desc") == ["Grace", "Alan", "Ada"]
    # A missing value sorts last whichever way the list goes.
    assert names(sort="company") == ["Ada", "Grace", "Alan"]
    assert names(sort="company", order="desc") == ["Grace", "Ada", "Alan"]
    # Ties (here: never contacted) keep creation order, so pages never overlap.
    assert names(sort="last_contacted_at") == ["Alan", "Grace", "Ada"]
    assert names(sort="last_contacted_at", order="desc") == ["Alan", "Grace", "Ada"]
    assert names(sort="status") == ["Grace", "Ada", "Alan"]  # active < lead
    assert names(sort="company", q="a") == ["Ada", "Grace", "Alan"]
    assert alice.get("/contacts/", params={"sort": "email"}).status_code == 422
    assert alice.get("/contacts/", params={"order": "up"}).status_code == 422


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
    assert bob.get("/contacts/").json()["items"] == []
    assert bob.get(url).status_code == 404
    assert bob.patch(url, json={"name": "X"}).status_code == 404
    assert bob.delete(url).status_code == 404
    assert bob.get(f"{url}/activities").status_code == 404
    assert bob.post(f"{url}/activities", json={"type": "note"}).status_code == 404


def test_validation(alice: Actor):
    assert alice.post("/contacts/", json={"name": " "}).status_code == 422
    assert alice.post("/contacts/", json={**GRACE, "email": "nope"}).status_code == 422
    assert alice.post("/contacts/", json={**GRACE, "status": "vip"}).status_code == 422


def test_activity_feed_is_newest_first(alice: Actor):
    contact = alice.post("/contacts/", json=GRACE).json()
    url = f"/contacts/{contact['id']}/activities"
    assert alice.get(url).json()["items"] == []

    first = alice.post(url, json={"type": "note", "notes": "Prefers email"})
    assert first.status_code == 201, first.text
    assert first.json()["type"] == "note"
    assert first.json()["notes"] == "Prefers email"
    assert first.json()["contact_id"] == contact["id"]

    alice.post(url, json={"type": "call"})
    feed = alice.get(url).json()["items"]
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
