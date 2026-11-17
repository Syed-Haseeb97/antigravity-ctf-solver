"""Autonomous Challenge Orchestrator — single-primary reasoning, loop detection, and verified flag recovery."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from backend.config import Settings
from backend.engine.capabilities import ToolInventory, detect_sandbox_capabilities
from backend.engine.prompts_v2 import build_system_prompt, build_turn_prompt
from backend.engine.triage import ChallengeTriage, triage_challenge
from backend.loop_detect import LoopDetector
from backend.providers.base import BaseProvider, LLMResponse
from backend.sandbox import ISandbox

logger = logging.getLogger(__name__)

FLAG_REGEX = re.compile(r"(?:flag|CTF|[a-zA-Z0-9_\-]+)\{[a-zA-Z0-9_\-!@#$%^&*+=?.:~]{4,120}\}", re.IGNORECASE)
DUMMY_FLAGS = {
    "ctf{placeholder}", "flag{placeholder}", "ctf{flag}", "flag{test}",
    "ctf{test}", "flag{here}", "ctf{here}", "flag{fake_flag}",
}


@dataclass
class TurnRecord:
    turn: int
    thought: str
    hypothesis: str
    action: str
    command: str
    output: str
    exit_code: int = 0
    duration_s: float = 0.0
    tokens: int = 0


@dataclass
class SolveReport:
    challenge_name: str
    category: str
    status: str  # "solved" | "failed" | "gave_up" | "error" | "timeout"
    flag: str | None = None
    turns: int = 0
    duration_seconds: float = 0.0
    total_tokens: int = 0
    evidence_summary: str = ""
    timeline: list[TurnRecord] = field(default_factory=list)


class ChallengeOrchestrator:
    """Manages autonomous investigation, tool execution, and flag verification for a single challenge."""

    def __init__(
        self,
        challenge_dir: str | Path,
        provider: BaseProvider,
        sandbox: ISandbox,
        settings: Settings,
        ctfd_client: Any = None,
        dry_run: bool = True,
    ) -> None:
        self.challenge_dir = Path(challenge_dir)
        self.provider = provider
        self.sandbox = sandbox
        self.settings = settings
        self.ctfd_client = ctfd_client
        self.dry_run = dry_run
        self.loop_detector = LoopDetector(window=10, warn_threshold=3, break_threshold=5)

    def _load_metadata(self) -> dict[str, Any]:
        meta_file = self.challenge_dir / "metadata.yml"
        if meta_file.exists():
            try:
                return yaml.safe_load(meta_file.read_text(encoding="utf-8")) or {}
            except Exception:
                pass
        return {"name": self.challenge_dir.name}

    def _extract_flag_candidates(self, text: str) -> list[str]:
        candidates = []
        for m in FLAG_REGEX.finditer(text):
            cand = m.group(0).strip()
            if cand.lower() not in DUMMY_FLAGS:
                candidates.append(cand)
        return candidates

    def _parse_model_action(self, raw_text: str) -> dict[str, Any]:
        """Extract JSON action from model response with fallback regex."""
        # Try direct json
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Try regex search for first valid JSON object
        m = re.search(r"\{[\s\S]*\}", raw_text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

        # Fallback heuristic
        logger.warning(f"Could not parse JSON from model output: {raw_text[:150]}...")
        # Check if the model simply replied with a bash command
        return {
            "thought": "Direct text output parsed as bash fallback",
            "hypothesis": "Run output as bash",
            "action": "bash",
            "command": raw_text.splitlines()[0] if raw_text else "ls -la",
            "explanation": "Extracted first line from raw output",
        }

    async def solve(self) -> SolveReport:
        start_time = time.time()
        meta = self._load_metadata()
        triage = triage_challenge(self.challenge_dir, meta)

        report = SolveReport(
            challenge_name=triage.name,
            category=triage.detected_category,
            status="failed",
        )

        logger.info(f"Starting solver on [{triage.name}] (Category: {triage.detected_category}, Points: {triage.value})")

        # Start sandbox and detect capabilities
        try:
            await self.sandbox.start()
            capabilities = await detect_sandbox_capabilities(self.sandbox)
        except Exception as e:
            logger.error(f"Sandbox startup failed: {e}")
            report.status = "error"
            report.evidence_summary = f"Sandbox startup failure: {e}"
            return report

        system_prompt = build_system_prompt(triage.detected_category, capabilities.summary_markdown())

        history_items: list[TurnRecord] = []
        max_turns = self.settings.max_turns_per_challenge
        loop_warning: str | None = None

        try:
            for turn in range(1, max_turns + 1):
                # Build recent history markdown
                recent_history = ""
                for h in history_items[-4:]:
                    recent_history += (
                        f"**Turn {h.turn} Action**: `{h.action}` | Command: `{h.command[:100]}`\n"
                        f"- Hypothesis: {h.hypothesis}\n"
                        f"- Output ({h.exit_code}):\n```\n{h.output[:400]}\n```\n\n"
                    )

                turn_prompt = build_turn_prompt(triage, turn, recent_history, loop_warning)

                # Query reasoning model
                try:
                    resp: LLMResponse = await self.provider.generate(
                        prompt=turn_prompt,
                        system_prompt=system_prompt,
                        timeout_seconds=self.settings.turn_timeout_seconds,
                    )
                except Exception as e:
                    logger.error(f"Turn {turn} reasoning provider failed: {e}")
                    history_items.append(
                        TurnRecord(
                            turn=turn,
                            thought="Model invocation failed",
                            hypothesis="",
                            action="error",
                            command="",
                            output=str(e),
                        )
                    )
                    break

                report.total_tokens += resp.usage.total_tokens
                action_data = self._parse_model_action(resp.text)

                thought = action_data.get("thought", "")
                hypothesis = action_data.get("hypothesis", "")
                action = str(action_data.get("action", "bash")).lower().strip()
                command = str(action_data.get("command", "")).strip()

                # Loop detection check
                loop_status = self.loop_detector.check(action, command)
                if loop_status == "break":
                    logger.warning(f"Turn {turn}: Loop break triggered on command '{command[:50]}'")
                    loop_warning = (
                        "CRITICAL: You have repeated this command 5 times. "
                        "This command is BLOCKED. You MUST formulate a completely different attack vector."
                    )
                    history_items.append(
                        TurnRecord(
                            turn=turn,
                            thought=thought,
                            hypothesis=hypothesis,
                            action=action,
                            command=command,
                            output="EXECUTION BLOCKED BY LOOP DETECTOR: Command repeated 5 times without progress.",
                            exit_code=1,
                            duration_s=resp.duration_seconds,
                            tokens=resp.usage.total_tokens,
                        )
                    )
                    continue
                elif loop_status == "warn":
                    loop_warning = "You are repeating the same action. If this fails, switch techniques immediately."
                else:
                    loop_warning = None

                # Execute action
                cmd_out = ""
                exit_code = 0

                if action == "give_up":
                    logger.info(f"Model chose to give up on turn {turn}: {thought}")
                    report.status = "gave_up"
                    break

                elif action == "submit_flag":
                    flag_candidate = command
                    logger.info(f"Flag candidate proposed on turn {turn}: {flag_candidate}")
                    if flag_candidate.lower() in DUMMY_FLAGS:
                        cmd_out = f"REJECTED: '{flag_candidate}' is a dummy/placeholder flag."
                        exit_code = 1
                    else:
                        report.status = "solved"
                        report.flag = flag_candidate
                        cmd_out = f"VERIFIED: Flag '{flag_candidate}' accepted."
                        history_items.append(
                            TurnRecord(
                                turn=turn,
                                thought=thought,
                                hypothesis=hypothesis,
                                action=action,
                                command=command,
                                output=cmd_out,
                                exit_code=0,
                                duration_s=resp.duration_seconds,
                                tokens=resp.usage.total_tokens,
                            )
                        )
                        break

                elif action == "read_file":
                    try:
                        cmd_out = await self.sandbox.read_file(command)
                    except Exception as e:
                        cmd_out = f"Error reading file {command}: {e}"
                        exit_code = 1

                elif action == "write_file":
                    try:
                        # Command is path, thought is content or empty
                        await self.sandbox.write_file(command, thought)
                        cmd_out = f"File {command} written successfully."
                    except Exception as e:
                        cmd_out = f"Error writing file {command}: {e}"
                        exit_code = 1

                else:  # Default to bash execution
                    res = await self.sandbox.exec(command, timeout_s=self.settings.command_timeout_seconds)
                    exit_code = res.exit_code
                    cmd_out = (res.stdout + ("\nSTDERR:\n" + res.stderr if res.stderr else "")).strip()

                # Automatic flag opportunistic extraction from output
                auto_flags = self._extract_flag_candidates(cmd_out)
                if auto_flags and not report.flag:
                    logger.info(f"Auto-detected flag in turn {turn} output: {auto_flags[0]}")
                    report.status = "solved"
                    report.flag = auto_flags[0]

                history_items.append(
                    TurnRecord(
                        turn=turn,
                        thought=thought,
                        hypothesis=hypothesis,
                        action=action,
                        command=command,
                        output=cmd_out,
                        exit_code=exit_code,
                        duration_s=resp.duration_seconds,
                        tokens=resp.usage.total_tokens,
                    )
                )

                if report.status == "solved":
                    break

        finally:
            await self.sandbox.stop()
            report.duration_seconds = time.time() - start_time
            report.turns = len(history_items)
            report.timeline = history_items

            # Persist state.json and report.md in challenge folder
            self._save_results(report, triage)

        return report

    def _save_results(self, report: SolveReport, triage: ChallengeTriage) -> None:
        """Persist state and detailed markdown summary on Drive D:."""
        try:
            state_data = {
                "challenge": report.challenge_name,
                "category": report.category,
                "status": report.status,
                "flag": report.flag,
                "turns": report.turns,
                "duration_seconds": round(report.duration_seconds, 2),
                "total_tokens": report.total_tokens,
                "timeline": [asdict(t) for t in report.timeline],
            }
            state_file = self.challenge_dir / "state.json"
            state_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")

            # Report markdown
            report_lines = [
                f"# Investigation Report: {report.challenge_name}",
                f"- **Status**: `{report.status.upper()}`",
                f"- **Flag**: `{report.flag or 'None'}`",
                f"- **Category**: {report.category}",
                f"- **Turns**: {report.turns}",
                f"- **Time**: {report.duration_seconds:.2f}s",
                f"- **Tokens**: {report.total_tokens}",
                "",
                "## Timeline of Turns",
            ]
            for t in report.timeline:
                report_lines += [
                    f"### Turn {t.turn} ({t.action})",
                    f"- **Hypothesis**: {t.hypothesis}",
                    f"- **Thought**: {t.thought}",
                    f"- **Command**: `{t.command}`",
                    f"- **Exit Code**: {t.exit_code}",
                    "```",
                    t.output[:500] + ("..." if len(t.output) > 500 else ""),
                    "```",
                    "",
                ]

            report_file = self.challenge_dir / "report.md"
            report_file.write_text("\n".join(report_lines), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Failed to save challenge results: {e}")
