from datetime import UTC, datetime
from uuid import UUID

from alloy_server.modules.assistant.tools.common import describe_changes
from alloy_server.modules.crm.contacts.models import ContactStatus
from alloy_server.modules.crm.contacts.schemas import ContactUpdate
from alloy_server.modules.crm.tasks.models import TaskStatus
from alloy_server.modules.crm.tasks.schemas import TaskUpdate


def test_describe_changes_lists_only_the_fields_being_set():
    changes = ContactUpdate(status=ContactStatus.INACTIVE, job_title="VP Sales")
    assert describe_changes(changes) == "job_title: VP Sales, status: inactive"


def test_describe_changes_shows_plain_values_for_enums_ids_and_dates():
    company_id = UUID("01a0d2dc-f2da-76b1-acfb-cbf2a2a0ae5e")
    when = datetime(2026, 9, 20, 10, 30, tzinfo=UTC)
    changes = ContactUpdate(company_id=company_id, last_contacted_at=when)
    text = describe_changes(changes, width=200)
    assert "<" not in text
    assert f"company_id: {company_id}" in text
    assert "last_contacted_at: 2026-09-20T10:30:00Z" in text


def test_describe_changes_marks_cleared_fields():
    assert describe_changes(TaskUpdate(due_at=None, status=TaskStatus.DONE)) == (
        "due_at: —, status: done"
    )


def test_describe_changes_is_cut_to_the_column_width():
    changes = ContactUpdate(job_title="x" * 100)
    assert describe_changes(changes, width=20) == "job_title: xxxxxxxx…"
