from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.conftest import Actor

ACME = {"name": "Acme", "website": "https://acme.example", "industry": "Manufacturing"}


def test_companies_require_login(client: TestClient, alice: Actor):
    assert client.get(alice.ws("/companies/")).status_code == 401
    assert client.post(alice.ws("/companies/"), json=ACME).status_code == 401


def test_create_and_read_a_company(alice: Actor):
    created = alice.post("/companies/", json=ACME)
    assert created.status_code == 201, created.text
    company = created.json()
    assert company["name"] == "Acme"
    assert company["website"] == "https://acme.example"
    assert company["industry"] == "Manufacturing"
    assert company["notes"] is None

    read = alice.get(f"/companies/{company['id']}")
    assert read.status_code == 200
    assert read.json() == company


def test_list_companies_sorted_by_name_with_search(alice: Actor):
    for name in ["Zeta Corp", "Acme", "Beta Labs"]:
        alice.post("/companies/", json={"name": name})

    names = [c["name"] for c in alice.get("/companies/").json()]
    assert names == ["Acme", "Beta Labs", "Zeta Corp"]

    found = alice.get("/companies/", params={"q": "eta"}).json()
    assert [c["name"] for c in found] == ["Beta Labs", "Zeta Corp"]


def test_update_a_company_can_clear_a_field(alice: Actor):
    company = alice.post("/companies/", json=ACME).json()
    response = alice.patch(
        f"/companies/{company['id']}", json={"industry": None, "notes": "Met at the trade show"}
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Acme"
    assert updated["industry"] is None
    assert updated["notes"] == "Met at the trade show"


def test_delete_a_company(alice: Actor):
    company = alice.post("/companies/", json=ACME).json()
    assert alice.delete(f"/companies/{company['id']}").status_code == 204
    assert alice.get(f"/companies/{company['id']}").status_code == 404


def test_users_only_see_their_own_companies(alice: Actor, bob: Actor):
    company = alice.post("/companies/", json=ACME).json()
    assert bob.get("/companies/").json() == []
    assert bob.get(f"/companies/{company['id']}").status_code == 404
    assert bob.patch(f"/companies/{company['id']}", json={"name": "X"}).status_code == 404
    assert bob.delete(f"/companies/{company['id']}").status_code == 404
    # Bob's attempts changed nothing.
    assert alice.get(f"/companies/{company['id']}").json()["name"] == "Acme"


def test_validation(alice: Actor):
    assert alice.post("/companies/", json={"name": ""}).status_code == 422
    assert alice.post("/companies/", json={"website": "x"}).status_code == 422
    assert alice.get("/companies/not-a-uuid").status_code == 422
