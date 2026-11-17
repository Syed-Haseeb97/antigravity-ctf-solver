"""Unit tests for classification, triage, and prioritization."""

from pathlib import Path
from backend.engine.triage import classify_category, calculate_priority, triage_challenge


def test_classify_category_direct():
    assert classify_category("crypto", "", [], "") == "crypto"
    assert classify_category("pwn", "", [], "") == "pwn"
    assert classify_category("reversing", "", [], "") == "rev"
    assert classify_category("web", "", [], "") == "web"
    assert classify_category("forensics", "", [], "") == "forensics"
    assert classify_category("stego", "", [], "") == "stego"


def test_classify_category_heuristics():
    # File heuristics
    assert classify_category("", "inspect packet capture", ["capture.pcap"], "") == "forensics"
    assert classify_category("", "find the flag", ["chall.elf"], "") == "rev"
    assert classify_category("", "inspect image", ["photo.png"], "") == "stego"
    assert classify_category("", "factor modulus", ["key.pem"], "") == "crypto"

    # Connection heuristics
    assert classify_category("", "", [], "http://chall.ctf:8080") == "web"


def test_calculate_priority():
    p1 = calculate_priority(100, 50, "forensics", True, False)
    p2 = calculate_priority(100, 0, "pwn", False, False)
    # Higher solve count & forensics weight should give higher priority
    assert p1 > p2


def test_triage_challenge(tmp_path):
    ch_dir = tmp_path / "test_challenge"
    ch_dir.mkdir()
    meta = {
        "name": "Test Chall",
        "category": "crypto",
        "value": 200,
        "solves": 15,
        "description": "RSA challenge",
    }
    triage = triage_challenge(ch_dir, meta)
    assert triage.name == "Test Chall"
    assert triage.detected_category == "crypto"
    assert triage.value == 200
    assert triage.priority_score > 0
