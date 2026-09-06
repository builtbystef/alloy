"""Root pytest configuration."""

import pytest


def pytest_sessionfinish(session: pytest.Session) -> None:
    """Exit successfully when no tests exist yet, instead of pytest's code 5."""
    if session.exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED:
        session.exitstatus = pytest.ExitCode.OK
