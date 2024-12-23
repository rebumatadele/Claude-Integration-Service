# app/utils/rate_limiter.py
import asyncio
from app.config import settings
from typing import Any, Dict
import time

class RateLimiter:
    def __init__(self):
        self.max_rpm = settings.rate_limit.max_rpm
        self.max_rph = settings.rate_limit.max_rph
        self.cooldown_period = settings.rate_limit.cooldown_period
        self.token_limit = settings.rate_limit.token_limit

        self.lock = asyncio.Lock()
        self.reset_time_rpm = time.time() + 60
        self.reset_time_rph = time.time() + 3600
        self.request_count_rpm = 0
        self.request_count_rph = 0

    async def acquire(self):
        async with self.lock:
            current_time = time.time()

            # Reset RPM
            if current_time >= self.reset_time_rpm:
                self.reset_time_rpm = current_time + 60
                self.request_count_rpm = 0

            # Reset RPH
            if current_time >= self.reset_time_rph:
                self.reset_time_rph = current_time + 3600
                self.request_count_rph = 0

            if self.request_count_rpm >= self.max_rpm or self.request_count_rph >= self.max_rph:
                wait_time = self.cooldown_period
                await asyncio.sleep(wait_time)
                # Reset after cooldown
                self.reset_time_rpm = time.time() + 60
                self.reset_time_rph = time.time() + 3600
                self.request_count_rpm = 0
                self.request_count_rph = 0

            self.request_count_rpm += 1
            self.request_count_rph += 1

    def update_from_headers(self, headers: Dict[str, Any]):
        """
        Update rate limiter parameters based on response headers.
        Assumes headers contain 'X-RateLimit-Remaining-RPM', 'X-RateLimit-Remaining-RPH',
        'X-RateLimit-Reset-RPM', 'X-RateLimit-Reset-RPH'.
        """
        async def _update():
            async with self.lock:
                remaining_rpm = int(headers.get('X-RateLimit-Remaining-RPM', self.max_rpm))
                remaining_rph = int(headers.get('X-RateLimit-Remaining-RPH', self.max_rph))
                reset_rpm = int(headers.get('X-RateLimit-Reset-RPM', self.cooldown_period))
                reset_rph = int(headers.get('X-RateLimit-Reset-RPH', self.cooldown_period))

                self.request_count_rpm = self.max_rpm - remaining_rpm
                self.request_count_rph = self.max_rph - remaining_rph
                self.reset_time_rpm = time.time() + reset_rpm
                self.reset_time_rph = time.time() + reset_rph

        asyncio.create_task(_update())

    def get_current_limits(self) -> Dict[str, Any]:
        return {
            "max_rpm": self.max_rpm,
            "max_rph": self.max_rph,
            "current_rpm": self.request_count_rpm,
            "current_rph": self.request_count_rph,
            "reset_time_rpm": self.reset_time_rpm,
            "reset_time_rph": self.reset_time_rph
        }

# Instantiate a global RateLimiter
rate_limiter_instance = RateLimiter()
