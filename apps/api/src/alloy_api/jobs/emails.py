from taskiq import TaskiqDepends

from alloy_api.integrations.mail import Email, Mailer
from alloy_api.jobs.broker import broker
from alloy_api.jobs.deps import get_mailer


@broker.task(task_name="mail.send", retry_on_error=True, max_retries=5)
async def send_email(email: Email, mailer: Mailer = TaskiqDepends(get_mailer)) -> None:
    await mailer.send(email)
