"""Benchmark system for evaluating CTF solver performance on synthetic and live challenge sets."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from backend.config import Settings
from backend.engine.orchestrator import ChallengeOrchestrator, SolveReport
from backend.providers.base import BaseProvider
from backend.providers.factory import get_provider
from backend.sandbox import DockerSandbox, ISandbox, MockSandbox

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkSummary:
    total_challenges: int = 0
    solved_count: int = 0
    failed_count: int = 0
    gave_up_count: int = 0
    error_count: int = 0
    solve_rate_percent: float = 0.0
    total_time_seconds: float = 0.0
    avg_time_per_challenge: float = 0.0
    total_tokens: int = 0
    total_turns: int = 0
    results: list[dict[str, Any]] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            "# CTF Autonomous Solver — Benchmark Evaluation Report",
            f"- **Challenges Attempted**: {self.total_challenges}",
            f"- **Challenges Solved**: {self.solved_count} / {self.total_challenges} ({self.solve_rate_percent:.1f}%)",
            f"- **Total Runtime**: {self.total_time_seconds:.2f}s (Avg {self.avg_time_per_challenge:.2f}s per challenge)",
            f"- **Total Model Tokens**: {self.total_tokens:,}",
            f"- **Total Action Turns**: {self.total_turns}",
            "",
            "## Challenge Results Table",
            "| Challenge | Category | Status | Turns | Time (s) | Tokens | Flag Recovered |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        ]
        for r in self.results:
            flag_disp = f"`{r.get('flag')}`" if r.get("flag") else "None"
            lines.append(
                f"| {r.get('challenge')} | {r.get('category')} | **{r.get('status').upper()}** | "
                f"{r.get('turns')} | {r.get('duration_s'):.2f} | {r.get('tokens'):,} | {flag_disp} |"
            )
        lines.append("")
        return "\n".join(lines)


class BenchmarkRunner:
    """Orchestrates challenge runs against a suite and computes metrics."""

    def __init__(
        self,
        challenges_dir: str | Path,
        provider: BaseProvider,
        settings: Settings,
        use_docker: bool = True,
    ) -> None:
        self.challenges_dir = Path(challenges_dir)
        self.provider = provider
        self.settings = settings
        self.use_docker = use_docker

    def _get_sandbox(self, ch_dir: Path) -> ISandbox:
        if self.use_docker:
            return DockerSandbox(
                image=self.settings.sandbox_image,
                challenge_dir=str(ch_dir),
                memory_limit=self.settings.container_memory_limit,
                cpu_count=self.settings.container_cpu_count,
                workspace_root=self.settings.workspace_root,
            )
        else:
            return MockSandbox(
                challenge_dir=str(ch_dir),
                workspace_root=self.settings.workspace_root,
            )

    async def run(self, max_challenges: int | None = None) -> BenchmarkSummary:
        start_time = time.time()
        subdirs = [p for p in self.challenges_dir.iterdir() if p.is_dir() and (p / "metadata.yml").exists()]
        if max_challenges:
            subdirs = subdirs[:max_challenges]

        summary = BenchmarkSummary(total_challenges=len(subdirs))
        reports: list[SolveReport] = []

        for ch_path in subdirs:
            sandbox = self._get_sandbox(ch_path)
            orchestrator = ChallengeOrchestrator(
                challenge_dir=ch_path,
                provider=self.provider,
                sandbox=sandbox,
                settings=self.settings,
                dry_run=True,
            )
            report = await orchestrator.solve()
            reports.append(report)

            if report.status == "solved":
                summary.solved_count += 1
            elif report.status == "gave_up":
                summary.gave_up_count += 1
            elif report.status == "error":
                summary.error_count += 1
            else:
                summary.failed_count += 1

            summary.total_tokens += report.total_tokens
            summary.total_turns += report.turns
            summary.results.append({
                "challenge": report.challenge_name,
                "category": report.category,
                "status": report.status,
                "flag": report.flag,
                "turns": report.turns,
                "duration_s": report.duration_seconds,
                "tokens": report.total_tokens,
            })

        summary.total_time_seconds = time.time() - start_time
        if summary.total_challenges > 0:
            summary.solve_rate_percent = (summary.solved_count / summary.total_challenges) * 100.0
            summary.avg_time_per_challenge = summary.total_time_seconds / summary.total_challenges

        return summary
