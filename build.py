#!/usr/bin/env python3
"""Build helper for Antigravity CLI.

Usage:
    python build.py install       # uv sync + pip install -e .
    python build.py wheel        # build a wheel
    python build.py sdist        # build a source dist
    python build.py test         # run tests
    python build.py sandbox      # build the Docker sandbox image
    python build.py clean        # remove build artifacts
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run(cmd: list[str], **kw) -> int:
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT, **kw).returncode


def install() -> int:
    """Install in editable mode with uv."""
    rc = _run(["uv", "sync"])
    if rc != 0:
        return rc
    return _run(["uv", "pip", "install", "-e", "."])


def wheel() -> int:
    return _run(["uv", "build", "--wheel"])


def sdist() -> int:
    return _run(["uv", "build", "--sdist"])


def test() -> int:
    return _run(["uv", "run", "pytest", "-v"])


def sandbox() -> int:
    return _run([
        "docker", "build",
        "-f", "sandbox/Dockerfile.sandbox",
        "-t", "ctf-sandbox",
        ".",
    ])


def clean() -> int:
    for d in ["build", "dist", "*.egg-info", ".pytest_cache", ".ruff_cache"]:
        for p in ROOT.glob(d):
            if p.is_dir():
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink(missing_ok=True)
    print("Cleaned build artifacts.")
    return 0


COMMANDS = {
    "install": install,
    "wheel": wheel,
    "sdist": sdist,
    "test": test,
    "sandbox": sandbox,
    "clean": clean,
}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "install"
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS)}")
        sys.exit(1)
    sys.exit(COMMANDS()())