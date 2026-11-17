"""Challenge classification, metadata triage, and competition prioritization."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ChallengeTriage:
    name: str
    category: str
    detected_category: str
    value: int
    solves: int
    connection_info: str
    distfiles: list[str]
    priority_score: float
    tags: list[str] = field(default_factory=list)
    description: str = ""


# Priority weightings per category (high probability of early points in university CTFs)
CATEGORY_WEIGHTS: dict[str, float] = {
    "crypto": 1.2,
    "web": 1.1,
    "forensics": 1.3,
    "stego": 1.2,
    "rev": 1.0,
    "reversing": 1.0,
    "pwn": 0.8,  # Often high-effort/time-consuming
    "misc": 1.1,
    "osint": 1.3,
}


def classify_category(category_hint: str, description: str, distfile_names: list[str], conn_info: str) -> str:
    """Infer the most accurate CTF category based on hints, files, and connection string."""
    cat = (category_hint or "").lower().strip()
    if cat in ("crypto", "cryptography"):
        return "crypto"
    if cat in ("pwn", "binary", "exploitation"):
        return "pwn"
    if cat in ("rev", "reversing", "reverse"):
        return "rev"
    if cat in ("web", "web-security"):
        return "web"
    if cat in ("forensics", "dfir"):
        return "forensics"
    if cat in ("stego", "steganography"):
        return "stego"
    if cat in ("misc", "miscellaneous"):
        return "misc"
    if cat in ("osint",):
        return "osint"

    # Analyze connection info
    if conn_info:
        if re.match(r"^https?://", conn_info.strip()):
            return "web"
        if conn_info.strip().startswith("nc "):
            # Could be pwn or crypto service
            pass

    # Analyze distfiles extensions
    exts = {Path(f).suffix.lower() for f in distfile_names}
    if {".pcap", ".pcapng", ".raw", ".vmem"}.intersection(exts):
        return "forensics"
    if {".png", ".jpg", ".jpeg", ".bmp", ".wav", ".mp3"}.intersection(exts):
        return "stego"
    if {".elf", ".exe", ".so", ".dll", ".bin"}.intersection(exts):
        return "rev"
    if {".enc", ".cipher", ".pem", ".pub"}.intersection(exts):
        return "crypto"

    # Analyze description keywords
    desc_lower = description.lower()
    if any(k in desc_lower for k in ["rsa", "xor", "cipher", "aes", "modulus", "decrypt", "hash"]):
        return "crypto"
    if any(k in desc_lower for k in ["sql", "xss", "jwt", "cookie", "endpoint", "http"]):
        return "web"
    if any(k in desc_lower for k in ["wireshark", "pcap", "dump", "exif", "memory"]):
        return "forensics"
    if any(k in desc_lower for k in ["buffer overflow", "rop", "shellcode", "libc", "canary"]):
        return "pwn"
    if any(k in desc_lower for k in ["decompile", "disassemble", "binary", "ghidra", "radare"]):
        return "rev"

    return "misc"


def calculate_priority(value: int, solves: int, category: str, has_files: bool, has_conn: bool) -> float:
    """Calculate prioritization score for tournament play:
    Higher score means higher value, more solvable, and ready-to-test evidence.
    """
    weight = CATEGORY_WEIGHTS.get(category, 1.0)
    # Solves signal viability: 0 solves might be broken/hard; many solves means approachable
    solve_factor = 1.0 + (min(solves, 50) * 0.05)
    point_val = max(10, value)
    readiness = 1.2 if (has_files or has_conn) else 0.8
    return float(point_val * solve_factor * weight * readiness)


def triage_challenge(challenge_dir: str | Path, meta_dict: dict[str, Any]) -> ChallengeTriage:
    """Perform triage on a challenge folder."""
    ch_path = Path(challenge_dir)
    dist = ch_path / "distfiles"
    distfiles = sorted(f.name for f in dist.iterdir() if f.is_file()) if dist.exists() else []

    name = meta_dict.get("name", ch_path.name)
    raw_cat = meta_dict.get("category", "")
    desc = meta_dict.get("description", "")
    conn = meta_dict.get("connection_info", "")
    value = int(meta_dict.get("value", 100))
    solves = int(meta_dict.get("solves", 0))
    tags = meta_dict.get("tags", [])

    detected_cat = classify_category(raw_cat, desc, distfiles, conn)
    priority = calculate_priority(value, solves, detected_cat, bool(distfiles), bool(conn))

    return ChallengeTriage(
        name=name,
        category=raw_cat,
        detected_category=detected_cat,
        value=value,
        solves=solves,
        connection_info=conn,
        distfiles=distfiles,
        priority_score=priority,
        tags=tags,
        description=desc,
    )
