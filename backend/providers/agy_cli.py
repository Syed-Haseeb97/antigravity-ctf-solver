"""Antigravity CLI (agy) provider adapter — zero-cost local Gemini 3.8 Flash."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from backend.providers.base import BaseProvider, LLMResponse, LLMUsage

logger = logging.getLogger(__name__)

DEFAULT_AGY_PATHS = [
    os.path.expanduser(r"~\.antigravity\bin\agy.exe"),
    r"C:\Program Files\Antigravity\bin\agy.exe",
]


class AgyCliProvider(BaseProvider):
    """Adapter for non-interactive execution via the native agy CLI binary."""

    def __init__(
        self,
        model: str = "gemini-3.8-flash-low",
        executable_path: str | None = None,
        effort: str = "low",
    ) -> None:
        self.model = model
        self.effort = effort
        self.executable_path = self._resolve_executable(executable_path)

    @classmethod
    def _resolve_executable(cls, path_override: str | None = None) -> str | None:
        if path_override and Path(path_override).exists():
            return path_override
        # Check environment variable
        env_path = os.getenv("AGY_CLI_PATH")
        if env_path and Path(env_path).exists():
            return env_path
        # Check PATH
        which_agy = shutil.which("agy") or shutil.which("agy.exe")
        if which_agy:
            return which_agy
        # Check standard known locations
        for candidate in DEFAULT_AGY_PATHS:
            if Path(candidate).exists():
                return candidate
        return None

    @property
    def name(self) -> str:
        return f"agy/{self.model}"

    def is_available(self) -> bool:
        return self.executable_path is not None and Path(self.executable_path).exists()

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        schema: dict[str, Any] | None = None,
        timeout_seconds: int = 180,
    ) -> LLMResponse:
        if not self.is_available():
            raise RuntimeError(
                f"Antigravity CLI executable not found. Checked PATH and {DEFAULT_AGY_PATHS}. "
                "Ensure agy is installed and accessible."
            )

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"### System Instructions\n{system_prompt.strip()}\n\n### Task\n{prompt.strip()}"

        cmd = [
            str(self.executable_path),
            "-p",
            full_prompt,
            "--output-format",
            "json",
            "--model",
            self.model,
            "--disable-slash-commands",
            "--dangerously-skip-permissions",
        ]
        # Only append --effort if model name does not already embed the level
        if not any(f"-{lvl}" in self.model for lvl in ["low", "medium", "high", "xhigh", "max"]):
            if self.effort:
                cmd.extend(["--effort", self.effort])

        logger.debug(f"Executing agy CLI: {' '.join(cmd[:4])} ...")

        max_attempts = 3
        last_err = ""

        for attempt in range(1, max_attempts + 1):
            start_time = asyncio.get_event_loop().time()
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except Exception:
                    pass
                if attempt < max_attempts:
                    logger.warning(f"agy CLI timed out (attempt {attempt}/{max_attempts}), retrying...")
                    await asyncio.sleep(2 * attempt)
                    continue
                raise TimeoutError(f"Antigravity CLI timed out after {timeout_seconds}s")
            except Exception as e:
                if attempt < max_attempts:
                    logger.warning(f"agy CLI launch failed ({e}) (attempt {attempt}/{max_attempts}), retrying...")
                    await asyncio.sleep(2 * attempt)
                    continue
                raise RuntimeError(f"Failed to launch Antigravity CLI process: {e}") from e

            duration = asyncio.get_event_loop().time() - start_time
            stdout_str = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr_str = stderr_bytes.decode("utf-8", errors="replace").strip()

            if proc.returncode != 0:
                last_err = stderr_str or stdout_str
                if attempt < max_attempts:
                    logger.warning(
                        f"agy CLI failed (exit {proc.returncode}: {last_err[:80]}) "
                        f"(attempt {attempt}/{max_attempts}), retrying..."
                    )
                    await asyncio.sleep(2 * attempt)
                    continue
                logger.error(f"agy CLI failed permanently (exit {proc.returncode}): {last_err}")
                raise RuntimeError(f"Antigravity CLI exited with code {proc.returncode}: {last_err}")
            
            # Successfully executed
            break

        # Parse JSON output from agy
        try:
            data = json.loads(stdout_str)
        except json.JSONDecodeError:
            # Fallback if text wasn't pure JSON
            logger.warning("agy output was not valid JSON, returning raw text")
            return LLMResponse(
                text=stdout_str,
                duration_seconds=duration,
                model_name=self.model,
                raw={"raw_stdout": stdout_str, "raw_stderr": stderr_str},
            )

        response_text = data.get("response", "")
        # Clean markdown code blocks if returning JSON block
        cleaned_text = response_text
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()

        usage_data = data.get("usage", {})
        usage = LLMUsage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
            thinking_tokens=usage_data.get("thinking_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        return LLMResponse(
            text=cleaned_text,
            usage=usage,
            duration_seconds=data.get("duration_seconds", duration),
            model_name=self.model,
            raw=data,
        )
