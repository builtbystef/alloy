from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.conftest import Actor


def iso(moment: datetime) -> str:
    return moment.isoformat()


def test_tasks_require_login(client: TestClient, alice: Actor):
    assert client.get(alice.ws("/tasks/")).status_code == 401


def test_create_and_read_a_task(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    created = alice.post(
        "/tasks/",
        json={
            "title": "Send proposal",
            "due_at": "2026-09-10T09:00:00Z",
            "contact_id": contact["id"],
            "company_id": company["id"],
            "notes": "Include the discount",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["title"] == "Send proposal"
    assert task["status"] == "open"
    assert task["contact"] == {"id": contact["id"], "name": "Grace"}
    assert task["company"] == {"id": company["id"], "name": "Navy"}
    assert datetime.fromisoformat(task["due_at"]) == datetime(2026, 9, 10, 9, tzinfo=UTC)

    assert alice.get(f"/tasks/{task['id']}").json() == task


def test_task_without_relations_or_due_date(alice: Actor):
    task = alice.post("/tasks/", json={"title": "Tidy inbox"}).json()
    assert task["contact"] is None
    assert task["company"] is None
    assert task["due_at"] is None


def test_task_cannot_reference_another_users_rows(alice: Actor, bob: Actor):
    contact = bob.post("/contacts/", json={"name": "Grace"}).json()
    response = alice.post("/tasks/", json={"title": "Call", "contact_id": contact["id"]})
    assert response.status_code == 404


def test_due_views(alice: Actor):
    now = datetime.now(UTC)
    for title, due_at in [
        ("Overdue", now - timedelta(days=2)),
        ("Today", now),
        ("Upcoming", now + timedelta(days=2)),
    ]:
        alice.post("/tasks/", json={"title": title, "due_at": iso(due_at)})
    alice.post("/tasks/", json={"title": "Someday"})

    def titles(**params: str) -> list[str]:
        response = alice.get("/tasks/", params=params)
        assert response.status_code == 200, response.text
        return [t["title"] for t in response.json()["items"]]

    assert titles() == ["Overdue", "Today", "Upcoming", "Someday"]  # by due date, undated last
    assert titles(due="overdue") == ["Overdue"]
    assert titles(due="today") == ["Today"]
    assert titles(due="upcoming") == ["Upcoming"]
    assert alice.get("/tasks/", params={"due": "later"}).status_code == 422


def test_today_depends_on_the_timezone(alice: Actor):
    # One minute into today in UTC is still yesterday twelve hours west of it.
    start_of_today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    alice.post(
        "/tasks/", json={"title": "Early", "due_at": iso(start_of_today + timedelta(minutes=1))}
    )

    def titles(due: str, tz: str) -> list[str]:
        response = alice.get("/tasks/", params={"due": due, "tz": tz})
        return [t["title"] for t in response.json()["items"]]

    assert titles("today", "UTC") == ["Early"]
    assert titles("today", "Etc/GMT+12") == []
    assert titles("overdue", "Etc/GMT+12") == ["Early"]
    assert alice.get("/tasks/", params={"tz": "Mars/Olympus"}).status_code == 422


def test_filter_by_status_contact_and_company(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    alice.post("/tasks/", json={"title": "A", "contact_id": contact["id"]})
    alice.post("/tasks/", json={"title": "B", "company_id": company["id"]})
    alice.post("/tasks/", json={"title": "C", "status": "done"})

    def titles(**params: str) -> list[str]:
        return [t["title"] for t in alice.get("/tasks/", params=params).json()["items"]]

    assert titles(status="open") == ["A", "B"]
    assert titles(status="done") == ["C"]
    assert titles(contact_id=contact["id"]) == ["A"]
    assert titles(company_id=company["id"]) == ["B"]


def test_sort_tasks(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    alice.post("/tasks/", json={"title": "B", "due_at": "2026-09-10T09:00:00Z"})
    alice.post("/tasks/", json={"title": "C", "contact_id": contact["id"]})
    alice.post(
        "/tasks/",
        json={"title": "A", "due_at": "2026-09-01T09:00:00Z", "company_id": company["id"]},
    )

    def titles(**params: str) -> list[str]:
        response = alice.get("/tasks/", params=params)
        assert response.status_code == 200, response.text
        return [t["title"] for t in response.json()["items"]]

    assert titles() == ["A", "B", "C"]  # soonest first, undated last
    assert titles(sort="due_at", order="desc") == ["B", "A", "C"]  # still undated last
    assert titles(sort="title") == ["A", "B", "C"]
    assert titles(sort="title", order="desc") == ["C", "B", "A"]
    assert titles(sort="contact") == ["C", "B", "A"]
    assert titles(sort="company", order="desc") == ["A", "B", "C"]
    assert alice.get("/tasks/", params={"sort": "notes"}).status_code == 422


def test_update_and_delete_a_task(alice: Actor):
    task = alice.post("/tasks/", json={"title": "Call", "due_at": "2026-09-10T09:00:00Z"}).json()
    response = alice.patch(f"/tasks/{task['id']}", json={"title": "Call back", "due_at": None})
    assert response.status_code == 200
    assert response.json()["title"] == "Call back"
    assert response.json()["due_at"] is None

    assert alice.delete(f"/tasks/{task['id']}").status_code == 204
    assert alice.get(f"/tasks/{task['id']}").status_code == 404


def test_completing_a_task_is_logged_on_the_contact(alice: Actor):
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    task = alice.post(
        "/tasks/", json={"title": "Send proposal", "contact_id": contact["id"]}
    ).json()

    done = alice.patch(f"/tasks/{task['id']}", json={"status": "done"})
    assert done.json()["status"] == "done"
    # Saving an already done task again does not log it twice.
    alice.patch(f"/tasks/{task['id']}", json={"status": "done", "notes": "Sent"})

    feed = alice.get(f"/contacts/{contact['id']}/activities").json()["items"]
    assert [(a["type"], a["notes"]) for a in feed] == [("task_completed", "Send proposal")]


def test_deleting_a_contact_keeps_its_tasks(alice: Actor):
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    task = alice.post("/tasks/", json={"title": "A", "contact_id": contact["id"]})
    alice.delete(f"/contacts/{contact['id']}")
    assert alice.get(f"/tasks/{task.json()['id']}").json()["contact"] is None


def test_users_only_see_their_own_tasks(alice: Actor, bob: Actor):
    task = alice.post("/tasks/", json={"title": "A"}).json()
    assert bob.get("/tasks/").json()["items"] == []
    assert bob.get(f"/tasks/{task['id']}").status_code == 404
    assert bob.patch(f"/tasks/{task['id']}", json={"title": "X"}).status_code == 404
    assert bob.delete(f"/tasks/{task['id']}").status_code == 404
