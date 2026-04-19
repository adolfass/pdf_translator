import time
import logging
from functools import wraps

import requests
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

from shared.config import settings

logger = logging.getLogger(__name__)

CIRCUIT_CLOSED = "closed"
CIRCUIT_OPEN = "open"
CIRCUIT_HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CIRCUIT_CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0

    @property
    def state(self):
        if self._state == CIRCUIT_OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CIRCUIT_HALF_OPEN
                logger.info("Circuit breaker transitioning to half_open")
        return self._state

    def record_success(self):
        self._failure_count = 0
        self._state = CIRCUIT_CLOSED

    def record_failure(self):
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            if self._state != CIRCUIT_OPEN:
                logger.warning("Circuit breaker OPEN after %d failures", self._failure_count)
            self._state = CIRCUIT_OPEN

    def can_execute(self):
        return self.state in (CIRCUIT_CLOSED, CIRCUIT_HALF_OPEN)


circuit_breaker = CircuitBreaker()


def yandex_retry_policy():
    return retry(
        stop=stop_after_attempt(settings.yandex_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((requests.RequestException, TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


def circuit_guard(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not circuit_breaker.can_execute():
            raise RuntimeError("Yandex Translate circuit breaker is OPEN")
        try:
            result = func(*args, **kwargs)
            circuit_breaker.record_success()
            return result
        except Exception as exc:
            circuit_breaker.record_failure()
            raise
    return wrapper
