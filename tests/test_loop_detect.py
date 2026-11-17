"""Unit tests for loop detection."""

from backend.loop_detect import LoopDetector, LOOP_WARNING_MESSAGE


def test_loop_detector_thresholds():
    detector = LoopDetector(window=10, warn_threshold=3, break_threshold=5)

    # First and second calls: no loop
    assert detector.check("bash", "ls -la") is None
    assert detector.check("bash", "ls -la") is None

    # Third call: warn
    assert detector.check("bash", "ls -la") == "warn"

    # Fourth call: still warn
    assert detector.check("bash", "ls -la") == "warn"

    # Fifth call: break
    assert detector.check("bash", "ls -la") == "break"


def test_loop_detector_reset():
    detector = LoopDetector(window=10, warn_threshold=3, break_threshold=5)
    detector.check("bash", "cat flag.txt")
    detector.check("bash", "cat flag.txt")
    detector.check("bash", "cat flag.txt")
    assert detector.check("bash", "cat flag.txt") == "warn"

    detector.reset()
    assert detector.check("bash", "cat flag.txt") is None
