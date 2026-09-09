"""CSV imports through the API, with the job running inline on the in-memory broker.
`upload()` plays the browser: it writes the file under the key the upload URL names,
then starts the import."""

from typing import TYPE_CHECKING

import pytest

from alloy_api.config import Settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.conftest import Actor

    from alloy_api.storage.memory import MemoryObjectStore


@pytest.fixture
def settings() -> Settings:
    return Settings(app_name="Test API", import_max_bytes=1024)


def start(actor: Actor, store: MemoryObjectStore, kind: str, data: bytes) -> dict:
    """Create, PUT, and start an import; return the row as `start` returned it."""
    created = actor.post(
        "/imports/", json={"kind": kind, "filename": f"{kind}.csv", "size": len(data)}
    )
    assert created.status_code == 201, created.text
    ticket = created.json()
    assert ticket["import"]["status"] == "pending"
    assert ticket["import"]["requested_by"]["email"] == actor.email
    assert "?put&content_type=text/csv" in ticket["upload_url"]
    store.objects[store.key_of(ticket["upload_url"])] = (data, "text/csv")
    started = actor.post(f"/imports/{ticket['import']['id']}/start")
    assert started.status_code == 200, started.text
    return started.json()


def upload(actor: Actor, store: MemoryObjectStore, kind: str, text: str) -> dict:
    """`start`, then read the row back once the job has run."""
    started = start(actor, store, kind, text.encode())
    assert started["status"] == "queued"
    finished = actor.get(f"/imports/{started['id']}").json()
    assert finished["finished_at"] is not None
    return finished


CONTACTS = (
    "﻿Name,Email,Job Title,Company,Status,Twitter\n"
    "Grace Hopper,hopper@example.com,Rear Admiral,US Navy,active,@grace\n"
    "\n"
    "Ada Lovelace,ada@example.com,,Analytical Engines,lead,\n"
    "Charles Babbage,charles@example.com,Inventor,analytical engines,,\n"
    "Grace Again,GRACE@example.com,,,,\n"
    "Bad Email,not-an-email,,,,\n"
    ",nobody@example.com,,,,\n"
    "Alan Turing,alan@example.com,,Acme,retired,\n"
    "No Email,,Consultant,,,\n"
)


def test_import_contacts(alice: Actor, object_store: MemoryObjectStore):
    acme = alice.post("/companies/", json={"name": "Acme"}).json()
    alice.post("/contacts/", json={"name": "Grace", "email": "grace@example.com"})

    record = upload(alice, object_store, "contacts", CONTACTS)
    assert record["status"] == "done", record
    assert record["error"] is None
    assert record["total_rows"] == 8  # the blank line is not a row
    assert record["created_count"] == 4
    assert record["skipped_count"] == 1  # grace@example.com was already there
    assert record["failed_count"] == 3
    assert record["errors"] == [
        {
            "row": 7,
            "message": "email: value is not a valid email address: An email address "
            "must have an @-sign.",
        },
        {"row": 8, "message": "name: Field required"},
        {"row": 9, "message": "status: Input should be 'lead', 'active' or 'inactive'"},
    ]
    # The file is not kept.
    assert object_store.objects == {}

    contacts = {c["name"]: c for c in alice.get("/contacts/").json()["items"]}
    assert set(contacts) == {"Grace", "Ada Lovelace", "Charles Babbage", "No Email", "Grace Hopper"}
    assert contacts["Grace Hopper"]["job_title"] == "Rear Admiral"
    assert contacts["Grace Hopper"]["status"] == "active"
    assert contacts["No Email"]["email"] is None
    assert contacts["No Email"]["status"] == "lead"
    # One company per name, whatever the case, created once for the file.
    companies = {c["name"]: c["id"] for c in alice.get("/companies/").json()["items"]}
    assert set(companies) == {"Acme", "US Navy", "Analytical Engines"}
    assert companies["Acme"] == acme["id"]
    assert contacts["Ada Lovelace"]["company"]["id"] == companies["Analytical Engines"]
    assert contacts["Charles Babbage"]["company"]["id"] == companies["Analytical Engines"]
    assert contacts["Grace Hopper"]["company"]["name"] == "US Navy"


COMPANIES = (
    "name,website,industry,notes\n"
    "Acme,https://acme.test,Explosives,Beep beep\n"
    "ACME,,,\n"
    "Globex,not a url,,\n"
    "Initech,,Software,\n"
)


def test_import_companies(alice: Actor, object_store: MemoryObjectStore):
    alice.post("/companies/", json={"name": "Initech"})
    record = upload(alice, object_store, "companies", COMPANIES)
    assert record["status"] == "done", record
    assert (record["created_count"], record["skipped_count"], record["failed_count"]) == (1, 2, 1)
    assert record["errors"][0]["row"] == 4
    assert record["errors"][0]["message"].startswith("website: ")
    companies = {c["name"]: c for c in alice.get("/companies/").json()["items"]}
    assert set(companies) == {"Acme", "Initech"}
    assert companies["Acme"]["website"] == "https://acme.test"
    assert companies["Acme"]["notes"] == "Beep beep"


def test_a_file_without_a_name_column_fails_as_a_whole(
    alice: Actor, object_store: MemoryObjectStore
):
    record = upload(alice, object_store, "contacts", "email\ngrace@example.com\n")
    assert record["status"] == "failed"
    assert record["error"] == "The header row has no 'name' column"
    assert record["created_count"] == 0
    assert alice.get("/contacts/").json()["items"] == []
    assert object_store.objects == {}


def test_a_file_that_is_not_utf8_fails_as_a_whole(alice: Actor, object_store: MemoryObjectStore):
    started = start(alice, object_store, "contacts", b"name\n\xff\xfe\n")
    record = alice.get(f"/imports/{started['id']}").json()
    assert record["status"] == "failed"
    assert record["error"] == "The file is not UTF-8 encoded"


def test_start_needs_the_file_and_happens_once(alice: Actor, object_store: MemoryObjectStore):
    ticket = alice.post(
        "/imports/", json={"kind": "contacts", "filename": "c.csv", "size": 10}
    ).json()
    import_id = ticket["import"]["id"]
    assert alice.post(f"/imports/{import_id}/start").status_code == 409
    object_store.objects[object_store.key_of(ticket["upload_url"])] = (b"name\nGrace\n", "text/csv")
    assert alice.post(f"/imports/{import_id}/start").status_code == 200
    assert alice.post(f"/imports/{import_id}/start").status_code == 409
    assert alice.get(f"/imports/{import_id}").json()["status"] == "done"


def test_size_limit(alice: Actor, object_store: MemoryObjectStore):
    too_big = alice.post("/imports/", json={"kind": "contacts", "filename": "c.csv", "size": 1025})
    assert too_big.status_code == 413
    # Declared small, uploaded big: refused at start, and the file is removed.
    ticket = alice.post(
        "/imports/", json={"kind": "contacts", "filename": "c.csv", "size": 10}
    ).json()
    key = object_store.key_of(ticket["upload_url"])
    object_store.objects[key] = (b"name\n" + b"x" * 1100, "text/csv")
    assert alice.post(f"/imports/{ticket['import']['id']}/start").status_code == 413
    assert key not in object_store.objects


def test_imports_are_listed_newest_first_and_per_workspace(
    client: TestClient, alice: Actor, bob: Actor, object_store: MemoryObjectStore
):
    first = upload(alice, object_store, "companies", "name\nAcme\n")
    second = upload(alice, object_store, "contacts", "name\nGrace\n")
    assert [i["id"] for i in alice.get("/imports/").json()["items"]] == [second["id"], first["id"]]
    assert bob.get("/imports/").json()["items"] == []
    assert client.get(alice.ws(f"/imports/{first['id']}"), headers=bob.headers).status_code == 404
    assert (
        client.post(alice.ws(f"/imports/{first['id']}/start"), headers=bob.headers).status_code
        == 404
    )
