"""File-based locking to prevent concurrent sync runs."""

import os
import time
from pathlib import Path
from typing import Optional
import logging


class SyncLock:
    """File-based lock to prevent concurrent sync execution."""

    def __init__(self, lock_file: Path, logger: Optional[logging.Logger] = None):
        """Initialize sync lock.

        Args:
            lock_file: Path to lock file
            logger: Optional logger
        """
        self.lock_file = lock_file
        self.logger = logger or logging.getLogger(__name__)
        self.acquired = False

    def acquire(self, timeout: float = 0, stale_threshold: float = 3600) -> bool:
        """Acquire the lock.

        Args:
            timeout: Maximum seconds to wait for lock (0 = don't wait)
            stale_threshold: Seconds after which lock is considered stale

        Returns:
            True if lock was acquired, False otherwise
        """
        start_time = time.time()

        while True:
            # Check if lock file exists
            if self.lock_file.exists():
                # Check if lock is stale
                lock_age = time.time() - self.lock_file.stat().st_mtime

                if lock_age > stale_threshold:
                    self.logger.warning(f"Lock file is stale ({lock_age:.0f}s old), removing")
                    try:
                        self.lock_file.unlink()
                    except OSError as e:
                        self.logger.error(f"Failed to remove stale lock: {e}")
                        return False
                else:
                    # Lock is held by another process
                    if timeout == 0:
                        self.logger.error(
                            "Another sync is already running. " f"Lock file: {self.lock_file}"
                        )
                        return False

                    # Wait and retry
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        self.logger.error(f"Timeout waiting for lock after {elapsed:.1f}s")
                        return False

                    time.sleep(1)
                    continue

            # Try to create lock file
            try:
                # Write PID and timestamp to lock file
                self.lock_file.parent.mkdir(parents=True, exist_ok=True)
                self.lock_file.write_text(
                    f"PID: {os.getpid()}\n" f"Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                )
                self.acquired = True
                self.logger.debug(f"Acquired lock: {self.lock_file}")
                return True
            except OSError as e:
                self.logger.error(f"Failed to create lock file: {e}")
                return False

    def release(self):
        """Release the lock."""
        if not self.acquired:
            return

        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
                self.logger.debug(f"Released lock: {self.lock_file}")
        except OSError as e:
            self.logger.error(f"Failed to remove lock file: {e}")
        finally:
            self.acquired = False

    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise RuntimeError("Failed to acquire lock")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()
        return False  # Don't suppress exceptions
