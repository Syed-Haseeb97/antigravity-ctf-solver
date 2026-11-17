"""Challenge solving engine package."""

from backend.engine.capabilities import ToolInventory, detect_sandbox_capabilities
from backend.engine.orchestrator import ChallengeOrchestrator, SolveReport, TurnRecord
from backend.engine.prompts_v2 import build_system_prompt, build_turn_prompt
from backend.engine.triage import ChallengeTriage, classify_category, triage_challenge

__all__ = [
    "ChallengeOrchestrator",
    "SolveReport",
    "TurnRecord",
    "ChallengeTriage",
    "classify_category",
    "triage_challenge",
    "ToolInventory",
    "detect_sandbox_capabilities",
    "build_system_prompt",
    "build_turn_prompt",
]
