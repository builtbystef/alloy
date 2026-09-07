from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient


def iso(moment: datetime) -> str:
    return moment.isoformat()


def test_tasks_require_login(client: TestClient):
    assert client.get("/tasks/").status_code == 401


def test_create_and_read_a_task(client: TestClient, alice: dict[str, str]):
    company = client.post("/companies/", json={"name": "Navy"}, headers=alice).json()
    contact = client.post("/contacts/", json={"name": "Grace"}, headers=alice).json()
    created = client.post(
        "/tasks/",
        json={
            "title": "Send proposal",
            "due_at": "2026-09-10T09:00:00Z",
            "contact_id": contact["id"],
            "company_id": company["id"],
            "notes": "Include the discount",
        },
        headers=alice,
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["title"] == "Send proposal"
    assert task["status"] == "open"
    assert task["contact"] == {"id": contact["id"], "name": "Grace"}
    assert task["company"] == {"id": company["id"], "name": "Navy"}
    assert datetime.fromisoformat(task["due_at"]) == datetime(2026, 9, 10, 9, tzinfo=UTC)

    assert client.get(f"/tasks/{task['id']}", headers=alice).json() == task


def test_task_without_relations_or_due_date(client: TestClient, alice: dict[str, str]):
    task = client.post("/tasks/", json={"title": "Tidy inbox"}, headers=alice).json()
    assert task["contact"] is None
    assert task["company"] is None
    assert task["due_at"] is None


def test_task_cannot_reference_another_users_rows(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    contact = client.post("/contacts/", json={"name": "Grace"}, headers=bob).json()
    response = client.post(
        "/tasks/", json={"title": "Call", "contact_id": contact["id"]}, headers=alice
    )
    assert response.status_code == 404


def test_due_views(client: TestClient, alice: dict[str, str]):
    now = datetime.now(UTC)
    for title, due_at in [
        ("Overdue", now - timedelta(days=2)),
        ("Today", now),
        ("Upcoming", now + timedelta(days=2)),
    ]:
        client.post("/tasks/", json={"title": title, "due_at": iso(due_at)}, headers=alice)
    client.post("/tasks/", json={"title": "Someday"}, headers=alice)

    def titles(**params: str) -> list[str]:
        response = client.get("/tasks/", params=params, headers=alice)
        assert response.status_code == 200, response.text
        return [t["title"] for t in response.json()]

    assert titles() == ["Overdue", "Today", "Upcoming", "Someday"]  # by due date, undated last
    assert titles(due="overdue") == ["Overdue"]
    assert titles(due="today") == ["Today"]
    assert titles(due="upcoming") == ["Upcoming"]
    assert client.get("/tasks/", params={"due": "later"}, headers=alice).status_code == 422


def test_today_depends_on_the_timezone(client: TestClient, alice: dict[str, str]):
    # One minute into today in UTC is still yesterday twelve hours west of it.
    start_of_today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    client.post(
        "/tasks/",
        json={"title": "Early", "due_at": iso(start_of_today + timedelta(minutes=1))},
        headers=alice,
    )

    def titles(due: str, tz: str) -> list[str]:
        response = client.get("/tasks/", params={"due": due, "tz": tz}, headers=alice)
        return [t["title"] for t in response.json()]

    assert titles("today", "UTC") == ["Early"]
    assert titles("today", "Etc/GMT+12") == []
    assert titles("overdue", "Etc/GMT+12") == ["Early"]
    assert client.get("/tasks/", params={"tz": "Mars/Olympus"}, headers=alice).status_code == 422


def test_filter_by_status_contact_and_company(client: TestClient, alice: dict[str, str]):
    company = client.post("/companies/", json={"name": "Navy"}, headers=alice).json()
    contact = client.post("/contacts/", json={"name": "Grace"}, headers=alice).json()
    client.post("/tasks/", json={"title": "A", "contact_id": contact["id"]}, headers=alice)
    client.post("/tasks/", json={"title": "B", "company_id": company["id"]}, headers=alice)
    client.post("/tasks/", json={"title": "C", "status": "done"}, headers=alice)

    def titles(**params: str) -> list[str]:
        return [t["title"] for t in client.get("/tasks/", params=params, headers=alice).json()]

    assert titles(status="open") == ["A", "B"]
    assert titles(status="done") == ["C"]
    assert titles(contact_id=contact["id"]) == ["A"]
    assert titles(company_id=company["id"]) == ["B"]


def test_update_and_delete_a_task(client: TestClient, alice: dict[str, str]):
    task = client.post(
        "/tasks/", json={"title": "Call", "due_at": "2026-09-10T09:00:00Z"}, headers=alice
    ).json()
    response = client.patch(
        f"/tasks/{task['id']}", json={"title": "Call back", "due_at": None}, headers=alice
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Call back"
    assert response.json()["due_at"] is None

    assert client.delete(f"/tasks/{task['id']}", headers=alice).status_code == 204
    assert client.get(f"/tasks/{task['id']}", headers=alice).status_code == 404


def test_completing_a_task_is_logged_on_the_contact(client: TestClient, alice: dict[str, str]):
    contact = client.post("/contacts/", json={"name": "Grace"}, headers=alice).json()
    task = client.post(
        "/tasks/", json={"title": "Send proposal", "contact_id": contact["id"]}, headers=alice
    ).json()

    done = client.patch(f"/tasks/{task['id']}", json={"status": "done"}, headers=alice)
    assert done.json()["status"] == "done"
    # Saving an already done task again does not log it twice.
    client.patch(f"/tasks/{task['id']}", json={"status": "done", "notes": "Sent"}, headers=alice)

    feed = client.get(f"/contacts/{contact['id']}/activities", headers=alice).json()
    assert [(a["type"], a["notes"]) for a in feed] == [("task_completed", "Send proposal")]


def test_deleting_a_contact_keeps_its_tasks(client: TestClient, alice: dict[str, str]):
    contact = client.post("/contacts/", json={"name": "Grace"}, headers=alice).json()
    task = client.post("/tasks/", json={"title": "A", "contact_id": contact["id"]}, headers=alice)
    client.delete(f"/contacts/{contact['id']}", headers=alice)
    assert client.get(f"/tasks/{task.json()['id']}", headers=alice).json()["contact"] is None


def test_users_only_see_their_own_tasks(
    client: TestClient, alice: dict[str, str], bob: dict[str, str]
):
    task = client.post("/tasks/", json={"title": "A"}, headers=alice).json()
    assert client.get("/tasks/", headers=bob).json() == []
    assert client.get(f"/tasks/{task['id']}", headers=bob).status_code == 404
    assert client.patch(f"/tasks/{task['id']}", json={"title": "X"}, headers=bob).status_code == 404
    assert client.delete(f"/tasks/{task['id']}", headers=bob).status_code == 404
