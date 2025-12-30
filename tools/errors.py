"""Error handling and retry logic for orgplan-todo sync."""

import time
from typing import Callable, TypeVar, Optional
import logging


T = TypeVar("T")


class SyncError(Exception):
    """Base exception for sync errors."""

    pass


class ConfigurationError(SyncError):
    """Raised when configuration is invalid."""

    pass


class OrgplanFormatError(SyncError):
    """Raised when orgplan file format is invalid."""

    pass


class APIError(SyncError):
    """Raised when API call fails."""

    pass


class NetworkError(APIError):
    """Raised when network operation fails."""

    pass


def retry_on_failure(
    func: Callable[..., T],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    logger: Optional[logging.Logger] = None,
) -> T:
    """Retry a function on failure with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        logger: Optional logger for retry messages

    Returns:
        Function return value

    Raises:
        Last exception if all retries fail
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            last_exception = e

            if attempt < max_retries:
                if logger:
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                time.sleep(delay)
                delay *= backoff_factor
            else:
                if logger:
                    logger.error(f"All {max_retries + 1} attempts failed")

    raise last_exception
