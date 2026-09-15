import logging

from alloy_server.jobs.app import app, task
from alloy_server.jobs.resources import Resources

logger = logging.getLogger(__name__)


@task("jobs.retry_stalled", cron="*/10 * * * *")
async def retry_stalled(_res: Resources) -> int:
    """A job whose worker died mid-run would stay running for good. Its worker's
    heartbeat has stopped, so the job is put back in the queue; every job is
    written to bear a second run."""
    stalled = list(await app.job_manager.get_stalled_jobs())
    for job in stalled:
        await app.job_manager.retry_job(job)
    if stalled:
        logger.warning("Requeued %d stalled jobs", len(stalled))
    return len(stalled)
