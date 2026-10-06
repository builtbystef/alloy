from datetime import timedelta

from alloy_server.integrations.rate_limit.base import (
    Hit,
    Limit,
    RateLimiter,
    RateLimitStore,
    too_many_requests,
)
from alloy_server.integrations.rate_limit.database import DatabaseRateLimitStore
from alloy_server.integrations.rate_limit.memory import MemoryRateLimitStore

# Routes that take an emailed token. Not against guessing (tokens are 32 random
# bytes): keeps scanners off the database.
TOKEN_PER_IP = Limit("token:ip", 10, timedelta(minutes=1))

__all__ = [
    "TOKEN_PER_IP",
    "DatabaseRateLimitStore",
    "Hit",
    "Limit",
    "MemoryRateLimitStore",
    "RateLimitStore",
    "RateLimiter",
    "too_many_requests",
]
