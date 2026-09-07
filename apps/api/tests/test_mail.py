import logging

import pytest

from alloy_api.config import Settings
from alloy_api.mail import ConsoleMailer, Email, create_mailer


def test_console_is_the_default_provider():
    mailer = create_mailer(Settings(app_name="Test API"))
    assert isinstance(mailer, ConsoleMailer)
    assert mailer.sender == "Alloy <no-reply@alloy.local>"


@pytest.mark.anyio
async def test_console_mailer_logs_the_message(caplog: pytest.LogCaptureFixture):
    mailer = ConsoleMailer(sender="Alloy <hello@alloy.test>")
    with caplog.at_level(logging.INFO, logger="alloy_api.mail.console"):
        await mailer.send(Email(to="grace@example.com", subject="Hi", text="Body\nmore"))
    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    for line in ("From: Alloy <hello@alloy.test>", "To: grace@example.com", "Subject: Hi", "Body"):
        assert line in message
