#!/usr/bin/env python3
"""Test Phase 4 automation features."""

import sys
import time
from pathlib import Path
import tempfile
import os

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from locking import SyncLock


def test_lock_acquisition():
    """Test basic lock acquisition and release."""
    print("Testing lock acquisition...")

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"
        lock = SyncLock(lock_file)

        # Test acquisition
        assert lock.acquire(), "Should acquire lock"
        assert lock_file.exists(), "Lock file should exist"

        print("  ✓ Lock acquired successfully")
        print(f"  ✓ Lock file created: {lock_file}")

        # Check lock file content
        content = lock_file.read_text()
        assert "PID:" in content, "Lock file should contain PID"
        assert "Started:" in content, "Lock file should contain timestamp"
        print("  ✓ Lock file contains PID and timestamp")

        # Release lock
        lock.release()
        assert not lock_file.exists(), "Lock file should be removed"
        print("  ✓ Lock released successfully")

    print()


def test_concurrent_lock_prevention():
    """Test that concurrent lock acquisition is prevented."""
    print("Testing concurrent lock prevention...")

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"

        # First lock
        lock1 = SyncLock(lock_file)
        assert lock1.acquire(), "First lock should succeed"
        print("  ✓ First lock acquired")

        # Second lock should fail
        lock2 = SyncLock(lock_file)
        assert not lock2.acquire(timeout=0), "Second lock should fail"
        print("  ✓ Second lock prevented (concurrent access blocked)")

        # Release first lock
        lock1.release()
        print("  ✓ First lock released")

        # Now second lock should succeed
        assert lock2.acquire(), "Second lock should succeed after first released"
        print("  ✓ Second lock acquired after release")

        lock2.release()

    print()


def test_stale_lock_removal():
    """Test that stale locks are automatically removed."""
    print("Testing stale lock removal...")

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"

        # Create a stale lock file
        lock_file.write_text(f"PID: 99999\nStarted: old timestamp\n")

        # Set modification time to 2 hours ago
        old_time = time.time() - (2 * 3600)
        os.utime(lock_file, (old_time, old_time))

        print(f"  Created stale lock (2 hours old)")

        # Try to acquire lock with stale threshold of 1 hour
        lock = SyncLock(lock_file)
        assert lock.acquire(stale_threshold=3600), "Should remove stale lock and acquire"
        print("  ✓ Stale lock removed automatically")
        print("  ✓ New lock acquired")

        lock.release()

    print()


def test_context_manager():
    """Test lock as context manager."""
    print("Testing context manager usage...")

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"

        # Use as context manager
        with SyncLock(lock_file) as lock:
            assert lock_file.exists(), "Lock should be acquired"
            print("  ✓ Lock acquired via context manager")

        assert not lock_file.exists(), "Lock should be released after context"
        print("  ✓ Lock released automatically on exit")

    print()


def test_lock_with_exception():
    """Test that lock is released even when exception occurs."""
    print("Testing lock release on exception...")

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"

        try:
            with SyncLock(lock_file) as lock:
                assert lock_file.exists(), "Lock should be acquired"
                print("  ✓ Lock acquired")
                raise ValueError("Test exception")
        except ValueError:
            pass

        assert not lock_file.exists(), "Lock should be released even with exception"
        print("  ✓ Lock released after exception")

    print()


def test_lock_timeout():
    """Test lock acquisition with timeout."""
    print("Testing lock acquisition timeout...")

    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = Path(tmpdir) / "test.lock"

        # First lock
        lock1 = SyncLock(lock_file)
        lock1.acquire()
        print("  ✓ First lock acquired")

        # Second lock with timeout
        lock2 = SyncLock(lock_file)
        start_time = time.time()
        result = lock2.acquire(timeout=2)
        elapsed = time.time() - start_time

        assert not result, "Should fail after timeout"
        assert elapsed >= 2, "Should wait for at least timeout duration"
        assert elapsed < 3, "Should not wait much longer than timeout"

        print(f"  ✓ Timeout respected ({elapsed:.1f}s ≈ 2s)")
        print("  ✓ Lock acquisition failed as expected")

        lock1.release()

    print()


def test_cron_script_exists():
    """Test that cron setup script exists and is executable."""
    print("Testing cron setup script...")

    script_path = Path("tools/setup_cron.sh")
    assert script_path.exists(), "Cron setup script should exist"
    print(f"  ✓ Cron setup script found: {script_path}")

    # Check if executable
    assert os.access(script_path, os.X_OK), "Script should be executable"
    print("  ✓ Script is executable")

    # Check script contains key elements
    content = script_path.read_text()
    assert "crontab" in content, "Script should set up crontab"
    assert "sync.py" in content, "Script should reference sync.py"
    assert "TODO_LIST_NAME" in content, "Script should use TODO_LIST_NAME"

    print("  ✓ Script contains expected components")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 4: Automation Features Test Suite")
    print("=" * 60)
    print()

    try:
        test_lock_acquisition()
        test_concurrent_lock_prevention()
        test_stale_lock_removal()
        test_context_manager()
        test_lock_with_exception()
        test_lock_timeout()
        test_cron_script_exists()

        print("=" * 60)
        print("All Phase 4 tests completed successfully! ✓")
        print("=" * 60)
        print()
        print("Phase 4 features implemented:")
        print("  ✓ File-based locking mechanism")
        print("  ✓ Concurrent execution prevention")
        print("  ✓ Stale lock detection and removal")
        print("  ✓ Context manager support")
        print("  ✓ Lock cleanup on exception")
        print("  ✓ Lock timeout support")
        print("  ✓ Cron setup script")
        print("  ✓ Automated lock release")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
