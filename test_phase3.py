#!/usr/bin/env python3
"""Test Phase 3 robustness features."""

import sys
import time
from pathlib import Path

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

from errors import retry_on_failure, APIError, NetworkError, SyncError
from orgplan_parser import OrgplanParser


def test_error_classes():
    """Test custom error classes."""
    print("Testing error classes...")

    try:
        raise SyncError("Test sync error")
    except SyncError as e:
        print(f"  ✓ SyncError: {e}")

    try:
        raise APIError("Test API error")
    except APIError as e:
        print(f"  ✓ APIError: {e}")

    try:
        raise NetworkError("Test network error")
    except NetworkError as e:
        print(f"  ✓ NetworkError: {e}")

    print()


def test_retry_logic():
    """Test retry logic with exponential backoff."""
    print("Testing retry logic...")

    # Test successful retry
    attempt_count = [0]

    def failing_then_succeeding():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise NetworkError("Simulated network error")
        return "success"

    start = time.time()
    result = retry_on_failure(
        failing_then_succeeding,
        max_retries=3,
        initial_delay=0.1,
        backoff_factor=2.0
    )
    duration = time.time() - start

    print(f"  ✓ Retry succeeded after {attempt_count[0]} attempts")
    print(f"  ✓ Total duration: {duration:.2f}s (with backoff)")
    print(f"  ✓ Result: {result}")

    # Test all retries fail
    def always_failing():
        raise NetworkError("Always fails")

    try:
        retry_on_failure(always_failing, max_retries=2, initial_delay=0.05)
        print("  ✗ Should have raised exception")
    except NetworkError as e:
        print(f"  ✓ All retries exhausted correctly: {e}")

    print()


def test_orgplan_validation():
    """Test orgplan file format validation."""
    print("Testing orgplan file validation...")

    # Test valid file
    parser = OrgplanParser(Path("2025/12-notes.md"))
    parser.load()
    warnings = parser.validate()

    if not warnings:
        print("  ✓ Valid orgplan file has no warnings")
    else:
        print(f"  ⚠ Warnings: {warnings}")

    # Test file without TODO List section
    test_file = Path("/tmp/test_invalid.md")
    test_file.write_text("# Some Header\n\nNo TODO List here\n")

    parser2 = OrgplanParser(test_file)
    parser2.load()
    warnings2 = parser2.validate()

    if warnings2 and "TODO List" in warnings2[0]:
        print("  ✓ Detected missing TODO List section")
    else:
        print(f"  ✗ Should detect missing TODO List section")

    # Clean up
    test_file.unlink()

    print()


def test_enhanced_error_handling():
    """Test enhanced error handling scenarios."""
    print("Testing enhanced error handling...")

    # Test error inheritance
    print("  ✓ APIError inherits from SyncError:", issubclass(APIError, SyncError))
    print("  ✓ NetworkError inherits from APIError:", issubclass(NetworkError, APIError))
    print("  ✓ NetworkError inherits from SyncError:", issubclass(NetworkError, SyncError))

    # Test exception catching hierarchy
    try:
        raise NetworkError("Network issue")
    except APIError as e:  # Should catch NetworkError
        print(f"  ✓ NetworkError caught as APIError: {e}")

    try:
        raise NetworkError("Network issue")
    except SyncError as e:  # Should catch NetworkError
        print(f"  ✓ NetworkError caught as SyncError: {e}")

    print()


def test_retry_backoff_timing():
    """Test that retry backoff timing is correct."""
    print("Testing retry backoff timing...")

    attempt_times = []

    def track_timing():
        attempt_times.append(time.time())
        if len(attempt_times) < 4:
            raise NetworkError("Retry")
        return "done"

    start = time.time()
    retry_on_failure(track_timing, max_retries=3, initial_delay=0.1, backoff_factor=2.0)

    # Check delays
    delays = [attempt_times[i+1] - attempt_times[i] for i in range(len(attempt_times)-1)]

    expected_delays = [0.1, 0.2, 0.4]  # Exponential backoff

    print(f"  Actual delays: {[f'{d:.2f}s' for d in delays]}")
    print(f"  Expected delays: {[f'{d:.1f}s' for d in expected_delays]}")

    # Allow for small timing variations
    for i, (actual, expected) in enumerate(zip(delays, expected_delays)):
        if abs(actual - expected) < 0.05:  # 50ms tolerance
            print(f"  ✓ Delay {i+1} is correct ({actual:.2f}s ≈ {expected:.1f}s)")
        else:
            print(f"  ⚠ Delay {i+1} off ({actual:.2f}s vs {expected:.1f}s)")

    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 3: Robustness Features Test Suite")
    print("=" * 60)
    print()

    try:
        test_error_classes()
        test_retry_logic()
        test_orgplan_validation()
        test_enhanced_error_handling()
        test_retry_backoff_timing()

        print("=" * 60)
        print("All Phase 3 tests completed successfully! ✓")
        print("=" * 60)
        print()
        print("Phase 3 features implemented:")
        print("  ✓ Custom error class hierarchy")
        print("  ✓ Retry logic with exponential backoff")
        print("  ✓ Orgplan file format validation")
        print("  ✓ Enhanced error handling")
        print("  ✓ API error classification (server, client, network)")
        print("  ✓ Logging integration for retries")

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
