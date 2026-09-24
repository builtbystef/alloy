from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.integration.conftest import Actor


def iso(moment: datetime) -> str:
    return moment.isoformat()


def test_tasks_require_login(client: TestClient, alice: Actor):
    assert client.get(alice.ws("/tasks/")).status_code == 401


def test_create_and_read_a_task(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    contact = alice.post("/contacts/", json={"name": "Grace", "company_id": company["id"]}).json()
    created = alice.post(
        "/tasks/",
        json={
            "title": "Send proposal",
            "due_at": "2026-09-10T09:00:00Z",
            "contact_id": contact["id"],
            "notes": "Include the discount",
        },
    )
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["title"] == "Send proposal"
    assert task["status"] == "open"
    assert task["contact"] == {"id": contact["id"], "name": "Grace"}
    # A contact task's company is the contact's.
    assert task["company"] == {"id": company["id"], "name": "Navy"}
    assert task["created_by"]["email"] == alice.email
    assert datetime.fromisoformat(task["due_at"]) == datetime(2026, 9, 10, 9, tzinfo=UTC)

    assert alice.get(f"/tasks/{task['id']}").json() == task


def test_task_without_relations_or_due_date(alice: Actor):
    task = alice.post("/tasks/", json={"title": "Tidy inbox"}).json()
    assert task["contact"] is None
    assert task["company"] is None
    assert task["due_at"] is None


def test_task_links_to_a_contact_or_a_company_not_both(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    other = alice.post("/companies/", json={"name": "Army"}).json()
    contact = alice.post("/contacts/", json={"name": "Grace", "company_id": company["id"]}).json()
    both = {"title": "Call", "contact_id": contact["id"], "company_id": other["id"]}
    response = alice.post("/tasks/", json=both)
    assert response.status_code == 409, response.text
    assert response.json()["detail"] == "A task is linked to a contact or a company, not both"

    task = alice.post("/tasks/", json={"title": "Call", "company_id": other["id"]}).json()
    url = f"/tasks/{task['id']}"
    assert alice.patch(url, json=both).status_code == 409
    # Linking a contact moves the link off the company, and the other way round.
    moved = alice.patch(url, json={"contact_id": contact["id"]}).json()
    assert moved["contact"]["id"] == contact["id"]
    assert moved["company"] == {"id": company["id"], "name": "Navy"}
    moved = alice.patch(url, json={"company_id": other["id"]}).json()
    assert moved["contact"] is None
    assert moved["company"] == {"id": other["id"], "name": "Army"}
    # A contact with no company gives a task with no company.
    loner = alice.post("/contacts/", json={"name": "Ada"}).json()
    moved = alice.patch(url, json={"contact_id": loner["id"]}).json()
    assert moved["contact"]["id"] == loner["id"]
    assert moved["company"] is None


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


def test_today_depends_on_the_timezone(alice: Actor, monkeypatch: pytest.MonkeyPatch):
    # Pin the clock to a UTC afternoon: one minute into today in UTC is then still
    # yesterday twelve hours west of it. Before noon UTC that would not hold, and the
    # task would count as today in both zones.
    now = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    monkeypatch.setattr("alloy_server.modules.crm.dates.utcnow", lambda: now)
    start_of_today = now.replace(hour=0, minute=0)
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
    other = alice.post("/companies/", json={"name": "Army"}).json()
    contact = alice.post("/contacts/", json={"name": "Grace", "company_id": company["id"]}).json()
    alice.post("/tasks/", json={"title": "A", "contact_id": contact["id"]})
    alice.post("/tasks/", json={"title": "B", "company_id": company["id"]})
    alice.post("/tasks/", json={"title": "C", "status": "done"})
    alice.post("/tasks/", json={"title": "D", "company_id": other["id"]})

    def titles(**params: str) -> list[str]:
        return [t["title"] for t in alice.get("/tasks/", params=params).json()["items"]]

    assert titles(status="open") == ["A", "B", "D"]
    assert titles(status="done") == ["C"]
    assert titles(contact_id=contact["id"]) == ["A"]
    # A company's tasks include its contacts' tasks.
    assert titles(company_id=company["id"]) == ["A", "B"]
    assert titles(company_id=other["id"]) == ["D"]


def test_sort_tasks(alice: Actor):
    company = alice.post("/companies/", json={"name": "Navy"}).json()
    army = alice.post("/companies/", json={"name": "Army"}).json()
    contact = alice.post("/contacts/", json={"name": "Grace", "company_id": army["id"]}).json()
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
    # By company name, a contact task under its contact's company: Army, Navy, none.
    assert titles(sort="company") == ["C", "A", "B"]
    assert titles(sort="company", order="desc") == ["A", "C", "B"]
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
    assert feed[0]["created_by"]["email"] == alice.email


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


def test_due_at_needs_a_time_zone(alice: Actor):
    naive = "2026-09-10T09:00:00"
    response = alice.post("/tasks/", json={"title": "Call", "due_at": naive})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "due_at"]
    task = alice.post("/tasks/", json={"title": "Call"}).json()
    assert alice.patch(f"/tasks/{task['id']}", json={"due_at": naive}).status_code == 422
    assert alice.get(f"/tasks/{task['id']}").json()["due_at"] is None


def test_required_fields_cannot_be_nulled(alice: Actor):
    task = alice.post("/tasks/", json={"title": "Call"}).json()
    for field in ("title", "status"):
        response = alice.patch(f"/tasks/{task['id']}", json={field: None})
        assert response.status_code == 422, response.text
        assert response.json()["detail"][0]["loc"] == ["body", field]
    assert alice.get(f"/tasks/{task['id']}").json() == task


def test_update_cannot_reference_another_users_rows(alice: Actor, bob: Actor):
    theirs = bob.post("/contacts/", json={"name": "Grace"}).json()
    their_company = bob.post("/companies/", json={"name": "Navy"}).json()
    task = alice.post("/tasks/", json={"title": "Call"}).json()
    url = f"/tasks/{task['id']}"
    assert alice.patch(url, json={"contact_id": theirs["id"]}).status_code == 404
    assert alice.patch(url, json={"company_id": their_company["id"]}).status_code == 404
    assert alice.get(url).json() == task


def test_filters_combine(alice: Actor):
    now = datetime.now(UTC)
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    alice.post("/tasks/", json={"title": "Open late", "due_at": iso(now - timedelta(days=1))})
    alice.post(
        "/tasks/",
        json={"title": "Done late", "due_at": iso(now - timedelta(days=1)), "status": "done"},
    )
    alice.post(
        "/tasks/",
        json={"title": "Hers", "due_at": iso(now - timedelta(days=1)), "contact_id": contact["id"]},
    )

    def titles(**params: str) -> list[str]:
        return [t["title"] for t in alice.get("/tasks/", params=params).json()["items"]]

    assert titles(due="overdue") == ["Open late", "Done late", "Hers"]
    assert titles(due="overdue", status="open") == ["Open late", "Hers"]
    assert titles(due="overdue", status="done") == ["Done late"]
    assert titles(due="overdue", status="open", contact_id=contact["id"]) == ["Hers"]


def test_reopening_a_task_and_completing_it_again_logs_it_again(alice: Actor):
    contact = alice.post("/contacts/", json={"name": "Grace"}).json()
    task = alice.post("/tasks/", json={"title": "Call", "contact_id": contact["id"]}).json()
    url = f"/tasks/{task['id']}"
    alice.patch(url, json={"status": "done"})
    assert alice.patch(url, json={"status": "open"}).json()["status"] == "open"
    alice.patch(url, json={"status": "done"})
    feed = alice.get(f"/contacts/{contact['id']}/activities").json()["items"]
    assert [a["type"] for a in feed] == ["task_completed", "task_completed"]
