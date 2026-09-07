from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

ACME = {"name": "Acme", "website": "https://acme.example", "industry": "Manufacturing"}


def test_companies_require_login(client: TestClient):
    assert client.get("/companies/").status_code == 401
    assert client.post("/companies/", json=ACME).status_code == 401


def test_create_and_read_a_company(client: TestClient, alice: dict[str, str]):
    created = client.post("/companies/", json=ACME, headers=alice)
    assert created.status_code == 201, created.text
    company = created.json()
    assert company["name"] == "Acme"
    assert company["website"] == "https://acme.example"
    assert company["industry"] == "Manufacturing"
    assert company["notes"] is None

    read = client.get(f"/companies/{company['id']}", headers=alice)
    assert read.status_code == 200
    assert read.json() == company


def test_list_companies_sorted_by_name_with_search(client: TestClient, alice: dict[str, str]):
    for name in ["Zeta Corp", "Acme", "Beta Labs"]:
        client.post("/companies/", json={"name": name}, headers=alice)

    names = [c["name"] for c in client.get("/companies/", headers=alice).json()]
    assert names == ["Acme", "Beta Labs", "Zeta Corp"]

    found = client.get("/companies/", params={"q": "eta"}, headers=alice).json()
    assert [c["name"] for c in found] == ["Beta Labs", "Zeta Corp"]


def test_update_a_company_can_clear_a_field(client: TestClient, alice: dict[str, str]):
    company = client.post("/companies/", json=ACME, headers=alice).json()
    response = client.patch(
        f"/companies/{company['id']}",
        json={"industry": None, "notes": "Met at the trade show"},
        headers=alice,
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Acme"
    assert updated["industry"] is None
    assert updated["notes"] == "Met at the trade show"


def test_delete_a_company(client: TestClient, alice: dict[str, str]):
    company = client.post("/companies/", json=ACME, headers=alice).json()
    assert client.delete(f"/companies/{company['id']}", headers=alice).status_code == 204
    assert client.get(f"/companies/{company['id']}", headers=alice).status_code == 404


def test_users_only_see_their_own_companies(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    company = client.post("/companies/", json=ACME, headers=alice).json()
    assert client.get("/companies/", headers=bob).json() == []
    assert client.get(f"/companies/{company['id']}", headers=bob).status_code == 404
    assert (
        client.patch(f"/companies/{company['id']}", json={"name": "X"}, headers=bob).status_code
        == 404
    )
    assert client.delete(f"/companies/{company['id']}", headers=bob).status_code == 404
    # Bob's attempts changed nothing.
    assert client.get(f"/companies/{company['id']}", headers=alice).json()["name"] == "Acme"


def test_validation(client: TestClient, alice: dict[str, str]):
    assert client.post("/companies/", json={"name": ""}, headers=alice).status_code == 422
    assert client.post("/companies/", json={"website": "x"}, headers=alice).status_code == 422
    assert client.get("/companies/not-a-uuid", headers=alice).status_code == 422
