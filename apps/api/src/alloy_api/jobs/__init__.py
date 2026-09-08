from typing import TYPE_CHECKING, Literal

from redis.asyncio import Redis
from taskiq import (
    AsyncBroker,
    InMemoryBroker,
    SmartRetryMiddleware,
    TaskiqScheduler,
)
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import ListRedisScheduleSource, RedisAsyncResultBackend, RedisStreamBroker

from alloy_api import telemetry

if TYPE_CHECKING:
    from taskiq import ScheduleSource

    from alloy_api.config import Settings

JobsBroker = Literal["redis", "memory"]

# One stream, one consumer group: every worker process reads from it and acks
# what it finished, so a message survives a worker crash.
QUEUE_NAME = "alloy"
CONSUMER_GROUP = "alloy-workers"
RETRY_SCHEDULE_PREFIX = "alloy:retries"
# Results are kept for an hour, so a caller can still ask how a job went.
RESULT_TTL_SECONDS = 60 * 60


def create_broker(settings: Settings) -> AsyncBroker:
    broker = _create_broker(settings)
    if telemetry.enabled(settings):
        broker.add_middlewares(telemetry.TracingMiddleware())
    return broker


def _create_broker(settings: Settings) -> AsyncBroker:
    match settings.jobs_broker:
        case "redis":
            url = str(settings.redis_url)
            return (
                RedisStreamBroker(url, queue_name=QUEUE_NAME, consumer_group_name=CONSUMER_GROUP)
                .with_result_backend(
                    RedisAsyncResultBackend(url, result_ex_time=RESULT_TTL_SECONDS)
                )
                .with_middlewares(
                    # Retries only for tasks labelled `retry_on_error`. The stream
                    # broker cannot delay a message itself, so a retry is put on
                    # `retry_source`, and the scheduler process sends it when due.
                    SmartRetryMiddleware(
                        default_retry_count=5,
                        default_delay=10,
                        use_jitter=True,
                        use_delay_exponent=True,
                        max_delay_exponent=600,
                        schedule_source=create_retry_source(settings),
                    )
                )
            )
        case "memory":
            return InMemoryBroker()


def create_retry_source(settings: Settings) -> ListRedisScheduleSource:
    return ListRedisScheduleSource(str(settings.redis_url), prefix=RETRY_SCHEDULE_PREFIX)


def create_scheduler(broker: AsyncBroker, settings: Settings) -> TaskiqScheduler:
    """Fires the `schedule` labels (cron) and, on Redis, the delayed retries.

    Run exactly one scheduler process: two would send every periodic task twice.
    """
    sources: list[ScheduleSource] = [LabelScheduleSource(broker)]
    if settings.jobs_broker == "redis":
        sources.append(create_retry_source(settings))
    return TaskiqScheduler(broker, sources=sources)


async def ping_redis(url: str) -> None:
    """Raises `redis.ConnectionError` when the server does not answer."""
    client = Redis.from_url(url)
    try:
        await client.ping()
    finally:
        await client.aclose()


__all__ = ["JobsBroker", "create_broker", "create_retry_source", "create_scheduler", "ping_redis"]
