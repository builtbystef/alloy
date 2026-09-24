from typing import TYPE_CHECKING

from alloy_server.integrations.mail import Email
from alloy_server.integrations.mail.jobs import queue_email, send_email
from alloy_server.jobs.app import RETRY_ON_ERROR, app

if TYPE_CHECKING:
    from tests.integration.conftest import Database, InlineConnector, Outbox


def test_the_send_task_is_registered_with_retries():
    assert app.tasks["mail.send"] is send_email
    assert send_email.retry_strategy is RETRY_ON_ERROR


def test_a_queued_email_goes_through_the_queue_to_the_mailer(
    db: Database, outbox: Outbox, queue: InlineConnector
):
    """The message is stored as JSON on the way, so what the mailer gets is a copy."""
    email = Email(to="grace@example.com", subject="Hi", text="Body", html="<p>Body</p>")

    async def queue_it() -> int:
        async with db.session() as session:
            return await queue_email(session, email)

    job_id = db.run(queue_it)
    assert outbox == [email]
    assert outbox[0] is not email
    stored = queue.jobs[job_id]
    assert stored["task_name"] == "mail.send"
    assert stored["args"]["email"] == {
        "to": "grace@example.com",
        "subject": "Hi",
        "text": "Body",
        "html": "<p>Body</p>",
    }
