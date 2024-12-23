#utils/callback_dispatcher
import httpx
from urllib.parse import urlparse
from loguru import logger
from app.models import Job, JobStatus
from app.utils.database import async_session
from app.utils.response_aggregator import response_aggregator_instance
from app.config import settings
import asyncio

class CallbackDispatcher:
    def __init__(self):
        self.retry_limit = 3
        self.retry_delay = 5  # seconds
        self.allowed_domains = set(settings.callback.allowed_domains)
        self.auth_token = settings.callback.auth_token

    async def dispatch_callback(self, job_id: str):
        async with async_session() as session:
            job = await session.get(Job, job_id)
            if not job:
                logger.error(f"Job {job_id} not found for callback.")
                return

            if job.status != JobStatus.COMPLETED:
                logger.warning(f"Job {job_id} is not completed. Current status: {job.status}")
                return

            # Validate the callback URL's domain
            parsed_url = urlparse(job.callback_url)
            domain = parsed_url.netloc
            if domain not in self.allowed_domains:
                logger.error(f"Callback URL domain '{domain}' is not in the allowed list.")
                return

            # Get the final aggregated result
            final_result = await response_aggregator_instance.get_final_result(job_id)
            if final_result is None:
                logger.warning(f"No final result available for job {job_id}.")
                return

            payload = {
                "job_id": job_id,
                "final_result": final_result
            }

            # Include auth_token if available
            if self.auth_token:
                payload["auth_token"] = self.auth_token

            # Attempt to send the callback with retries
            for attempt in range(1, self.retry_limit + 1):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(job.callback_url, json=payload, timeout=10)
                        if response.status_code in [200, 201, 202]:
                            logger.info(f"Successfully dispatched callback for job {job_id} to {job.callback_url}")
                            return
                        else:
                            logger.error(f"Callback dispatch failed for job {job_id} with status {response.status_code}: {response.text}")
                except httpx.RequestError as e:
                    logger.error(f"Request error during callback dispatch for job {job_id}: {e}")

                if attempt < self.retry_limit:
                    logger.info(f"Retrying callback dispatch for job {job_id} in {self.retry_delay} seconds (Attempt {attempt}/{self.retry_limit})")
                    await asyncio.sleep(self.retry_delay)

            logger.error(f"Failed to dispatch callback for job {job_id} after {self.retry_limit} attempts.")

# Instantiate a global CallbackDispatcher
callback_dispatcher_instance = CallbackDispatcher()
