from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from tests.conftest import Actor


def test_dashboard_requires_login(client: TestClient, alice: Actor):
    assert client.get(alice.ws("/dashboard/")).status_code == 401


def test_empty_dashboard(alice: Actor):
    response = alice.get("/dashboard/")
    assert response.status_code == 200
    assert response.json() == {
        "total_contacts": 0,
        "tasks_due_today": 0,
        "overdue_tasks": 0,
        "recently_contacted": [],
        "not_recently_contacted": [],
    }


def test_dashboard_counts_and_lists(alice: Actor, bob: Actor):
    now = datetime.now(UTC)

    def contact(name: str, last_contacted: datetime | None, who: Actor = alice):
        body = {"name": name, "last_contacted_at": last_contacted and last_contacted.isoformat()}
        return who.post("/contacts/", json=body).json()

    contact("Fresh", now - timedelta(days=1))
    contact("Recent", now - timedelta(days=10))
    contact("Stale", now - timedelta(days=45))
    contact("Never", None)
    contact("Bobs", now, who=bob)

    def task(title: str, due_at: datetime | None, status: str = "open"):
        body = {"title": title, "due_at": due_at and due_at.isoformat(), "status": status}
        alice.post("/tasks/", json=body)

    task("Overdue", now - timedelta(days=3))
    task("Overdue but done", now - timedelta(days=3), status="done")
    task("Today", now)
    task("Today too", now)
    task("Upcoming", now + timedelta(days=3))
    task("Undated", None)

    dashboard = alice.get("/dashboard/").json()
    assert dashboard["total_contacts"] == 4
    assert dashboard["tasks_due_today"] == 2
    assert dashboard["overdue_tasks"] == 1
    assert [c["name"] for c in dashboard["recently_contacted"]] == ["Fresh", "Recent", "Stale"]
    # Not contacted in 30 days, never contacted last.
    assert [c["name"] for c in dashboard["not_recently_contacted"]] == ["Stale", "Never"]


def test_dashboard_stale_days_and_limit(alice: Actor):
    now = datetime.now(UTC)
    for days in [1, 5, 10]:
        body = {
            "name": f"{days} days",
            "last_contacted_at": (now - timedelta(days=days)).isoformat(),
        }
        alice.post("/contacts/", json=body)

    dashboard = alice.get("/dashboard/", params={"stale_days": 7, "limit": 2}).json()
    assert [c["name"] for c in dashboard["recently_contacted"]] == ["1 days", "5 days"]
    assert [c["name"] for c in dashboard["not_recently_contacted"]] == ["10 days"]
