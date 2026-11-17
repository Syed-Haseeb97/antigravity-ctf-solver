"""Pydantic Settings — configuration and hardware resource profiles."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # CTFd configuration
    ctfd_url: str = "http://localhost:8000"
    ctfd_user: str = "admin"
    ctfd_pass: str = "admin"
    ctfd_token: str = ""

    # Primary reasoning model (zero-cost Gemini 3.8 Flash via agy CLI)
    default_model: str = "agy/gemini-3.8-flash-medium"
    reasoning_effort: str = "medium"  # low, medium, high
    agy_cli_path: str = ""

    # Optional direct API keys (fallback / alternate providers)
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Hardware-optimized Docker Sandbox Profile (Laptop Target: i5, 16GB RAM)
    sandbox_image: str = "ctf-sandbox-lite"
    sandbox_profile: str = "lite"  # lite, standard, advanced
    container_memory_limit: str = "3g"  # 3GB limit per container (replaces 16g default)
    container_cpu_count: float = 2.0  # 2 cores max per container
    max_concurrent_challenges: int = 1  # 1 active challenge by default
    max_attempts_per_challenge: int = 3
    max_turns_per_challenge: int = 25  # Limit turns per challenge to prevent runaway costs/loops

    # Timeouts (seconds)
    command_timeout_seconds: int = 60
    turn_timeout_seconds: int = 180

    # Storage paths (Strictly Drive D: per policy)
    workspace_root: str = r"D:\5TH vid\ctf ig\.workspaces"
    challenges_dir: str = "challenges"

    # Competition Safety Controls
    dry_run: bool = True  # Dry run flag verification by default
    unlock_paid_hints: bool = False  # NEVER spend points without explicit operator permission

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def ensure_directories(self) -> None:
        """Ensure necessary runtime directories exist on Drive D:."""
        Path(self.workspace_root).mkdir(parents=True, exist_ok=True)
        Path(self.challenges_dir).mkdir(parents=True, exist_ok=True)
