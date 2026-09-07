"""The upload handshake against the in-memory store. `upload()` plays the browser:
it writes the bytes under the key the upload URL names, then reports completion.
"""

from typing import TYPE_CHECKING

import pytest

from alloy_api.config import Settings

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.conftest import Actor

    from alloy_api.storage.memory import MemoryObjectStore

PDF = {"filename": "contract.pdf", "content_type": "application/pdf", "size": 11}


def upload(actor: Actor, store: MemoryObjectStore, path: str, body: dict, data: bytes) -> dict:
    """Start, PUT, and complete an upload; return the finished attachment."""
    started = actor.post(path, json=body)
    assert started.status_code == 201, started.text
    ticket = started.json()
    assert ticket["attachment"]["uploaded_at"] is None
    assert ticket["expires_at"]
    key = store.key_of(ticket["upload_url"])
    assert f"?put&content_type={body['content_type']}" in ticket["upload_url"]
    store.objects[key] = (data, body["content_type"])
    completed = actor.post(f"/attachments/{ticket['attachment']['id']}/complete")
    assert completed.status_code == 200, completed.text
    return completed.json()


@pytest.fixture
def contact(alice: Actor) -> dict:
    return alice.post("/contacts/", json={"name": "Grace Hopper"}).json()


@pytest.fixture
def company(alice: Actor) -> dict:
    return alice.post("/companies/", json={"name": "Acme"}).json()


def test_upload_to_a_contact(alice: Actor, object_store: MemoryObjectStore, contact: dict):
    path = f"/contacts/{contact['id']}/attachments"
    attachment = upload(alice, object_store, path, PDF, b"hello world")
    assert attachment["filename"] == "contract.pdf"
    assert attachment["content_type"] == "application/pdf"
    assert attachment["size"] == 11
    assert attachment["contact_id"] == contact["id"]
    assert attachment["company_id"] is None
    assert attachment["uploaded_by"]["email"] == alice.email
    assert attachment["uploaded_at"] is not None

    assert alice.get(path).json() == [attachment]
    # The object sits under the workspace's prefix, so a workspace delete can find it.
    (key,) = object_store.objects
    assert key == f"workspaces/{alice.workspace}/attachments/{attachment['id']}"


def test_upload_to_a_company(alice: Actor, object_store: MemoryObjectStore, company: dict):
    path = f"/companies/{company['id']}/attachments"
    attachment = upload(alice, object_store, path, PDF, b"hello world")
    assert attachment["company_id"] == company["id"]
    assert attachment["contact_id"] is None
    assert alice.get(path).json() == [attachment]


def test_complete_is_idempotent_and_trusts_the_store(
    alice: Actor, object_store: MemoryObjectStore, contact: dict
):
    """The client's declared size is a hint; what the store received is recorded."""
    path = f"/contacts/{contact['id']}/attachments"
    attachment = upload(alice, object_store, path, {**PDF, "size": 3}, b"hello world")
    assert attachment["size"] == 11
    again = alice.post(f"/attachments/{attachment['id']}/complete")
    assert again.status_code == 200
    assert again.json() == attachment


def test_pending_uploads_are_hidden_until_complete(
    alice: Actor, object_store: MemoryObjectStore, contact: dict
):
    path = f"/contacts/{contact['id']}/attachments"
    ticket = alice.post(path, json=PDF).json()
    attachment_id = ticket["attachment"]["id"]
    assert alice.get(path).json() == []
    download = alice.get(f"/attachments/{attachment_id}/download", follow_redirects=False)
    assert download.status_code == 404

    # Nothing was PUT yet.
    assert alice.post(f"/attachments/{attachment_id}/complete").status_code == 409

    object_store.objects[object_store.key_of(ticket["upload_url"])] = (b"x", "application/pdf")
    assert alice.post(f"/attachments/{attachment_id}/complete").status_code == 200
    assert [a["id"] for a in alice.get(path).json()] == [attachment_id]


@pytest.fixture
def settings(request: pytest.FixtureRequest) -> Settings:
    """Overrides conftest's: `indirect` parametrization sets the size limit."""
    limit = getattr(request, "param", None)
    return (
        Settings(app_name="Test API")
        if limit is None
        else Settings(app_name="Test API", attachment_max_bytes=limit)
    )


@pytest.mark.parametrize("settings", [10], indirect=True)
def test_size_limit(alice: Actor, object_store: MemoryObjectStore, contact: dict):
    path = f"/contacts/{contact['id']}/attachments"

    # Refused up front when the client says the file is too big.
    refused = alice.post(path, json={**PDF, "size": 11})
    assert refused.status_code == 413
    assert "10 bytes" in refused.json()["detail"]

    # Refused on completion, and the object removed, when the client lied.
    ticket = alice.post(path, json={**PDF, "size": 5}).json()
    key = object_store.key_of(ticket["upload_url"])
    object_store.objects[key] = (b"0123456789ab", "application/pdf")
    assert alice.post(f"/attachments/{ticket['attachment']['id']}/complete").status_code == 413
    assert key not in object_store.objects
    assert alice.get(path).json() == []

    assert upload(alice, object_store, path, {**PDF, "size": 5}, b"12345")["size"] == 5


def test_download_redirects_to_a_signed_url(
    alice: Actor, object_store: MemoryObjectStore, contact: dict
):
    path = f"/contacts/{contact['id']}/attachments"
    attachment = upload(alice, object_store, path, PDF, b"hello world")
    response = alice.get(f"/attachments/{attachment['id']}/download", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert object_store.key_of(location) in object_store.objects
    assert "?get&filename=contract.pdf" in location


def test_delete_removes_the_object(alice: Actor, object_store: MemoryObjectStore, contact: dict):
    path = f"/contacts/{contact['id']}/attachments"
    attachment = upload(alice, object_store, path, PDF, b"hello world")
    assert alice.delete(f"/attachments/{attachment['id']}").status_code == 204
    assert object_store.objects == {}
    assert alice.get(path).json() == []
    assert alice.delete(f"/attachments/{attachment['id']}").status_code == 404


def test_deleting_the_parent_removes_its_objects(
    alice: Actor, object_store: MemoryObjectStore, contact: dict, company: dict
):
    upload(alice, object_store, f"/contacts/{contact['id']}/attachments", PDF, b"a")
    upload(alice, object_store, f"/companies/{company['id']}/attachments", PDF, b"b")
    kept = upload(alice, object_store, f"/companies/{company['id']}/attachments", PDF, b"c")
    assert len(object_store.objects) == 3

    assert alice.delete(f"/contacts/{contact['id']}").status_code == 204
    assert len(object_store.objects) == 2
    assert alice.delete(f"/attachments/{kept['id']}").status_code == 204
    assert alice.delete(f"/companies/{company['id']}").status_code == 204
    assert object_store.objects == {}


def test_deleting_the_workspace_clears_its_prefix(
    client: TestClient, alice: Actor, bob: Actor, object_store: MemoryObjectStore, contact: dict
):
    upload(alice, object_store, f"/contacts/{contact['id']}/attachments", PDF, b"a")
    theirs = bob.post("/contacts/", json={"name": "Ada"}).json()
    upload(bob, object_store, f"/contacts/{theirs['id']}/attachments", PDF, b"b")

    assert client.delete(alice.ws(), headers=alice.headers).status_code == 204
    (key,) = object_store.objects
    assert key.startswith(f"workspaces/{bob.workspace}/")


def test_attachments_are_scoped_to_the_workspace(
    alice: Actor, bob: Actor, object_store: MemoryObjectStore, contact: dict
):
    path = f"/contacts/{contact['id']}/attachments"
    attachment = upload(alice, object_store, path, PDF, b"hello world")
    assert bob.get(path).status_code == 404
    assert bob.post(path, json=PDF).status_code == 404
    assert bob.post(f"/attachments/{attachment['id']}/complete").status_code == 404
    download = bob.get(f"/attachments/{attachment['id']}/download", follow_redirects=False)
    assert download.status_code == 404
    assert bob.delete(f"/attachments/{attachment['id']}").status_code == 404
    assert len(object_store.objects) == 1


def test_viewers_can_download_but_not_change(
    alice: Actor, join, object_store: MemoryObjectStore, contact: dict
):
    viewer: Actor = join(alice, "viewer@example.com", "viewer")
    path = f"/contacts/{contact['id']}/attachments"
    attachment = upload(alice, object_store, path, PDF, b"hello world")
    assert viewer.get(path).status_code == 200
    download = viewer.get(f"/attachments/{attachment['id']}/download", follow_redirects=False)
    assert download.status_code == 307
    assert viewer.post(path, json=PDF).status_code == 403
    assert viewer.post(f"/attachments/{attachment['id']}/complete").status_code == 403
    assert viewer.delete(f"/attachments/{attachment['id']}").status_code == 403


def test_validation(alice: Actor, contact: dict):
    path = f"/contacts/{contact['id']}/attachments"
    assert alice.post(path, json={**PDF, "filename": " "}).status_code == 422
    assert alice.post(path, json={**PDF, "content_type": "not a type"}).status_code == 422
    assert alice.post(path, json={**PDF, "size": 0}).status_code == 422
    assert alice.post(path, json={**PDF, "filename": "x" * 256}).status_code == 422
