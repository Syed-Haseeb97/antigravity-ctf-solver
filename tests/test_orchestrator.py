"""Integration tests for autonomous challenge orchestrator on synthetic challenges."""

import json
import pytest
from pathlib import Path

from backend.config import Settings
from backend.engine.orchestrator import ChallengeOrchestrator
from backend.providers.mock_provider import MockProvider
from backend.sandbox import LocalSubprocessSandbox
from backend.synthetic_generator import generate_synthetic_challenges


@pytest.fixture(scope="module")
def synthetic_suite(tmp_path_factory):
    base_dir = tmp_path_factory.mktemp("synthetic_challenges")
    return generate_synthetic_challenges(base_dir)


@pytest.mark.asyncio
async def test_solve_crypto_base64_synthetic(synthetic_suite, tmp_path):
    ch_path = synthetic_suite["crypto_base64"]
    settings = Settings(workspace_root=str(tmp_path / "workspaces"), max_turns_per_challenge=5)

    # Mock provider simulates agent discovering base64 file and decoding it
    responses = [
        # Turn 1: inspect distfiles
        json.dumps({
            "thought": "Inspect the attached secret.txt",
            "hypothesis": "The secret file contains a base64 encoded flag",
            "action": "bash",
            "command": "python -c \"import base64; print(base64.b64decode(open('distfiles/secret.txt').read().strip()).decode())\"",
            "explanation": "Decode base64 string",
        }),
        # Turn 2: submit extracted flag
        json.dumps({
            "thought": "The base64 decode yielded flag{base64_decoded_successfully}",
            "hypothesis": "Submit the decoded flag",
            "action": "submit_flag",
            "command": "flag{base64_decoded_successfully}",
            "explanation": "Confirmed flag format",
        }),
    ]

    provider = MockProvider(responses=responses)
    sandbox = LocalSubprocessSandbox(challenge_dir=str(ch_path), workspace_root=settings.workspace_root)

    orchestrator = ChallengeOrchestrator(
        challenge_dir=ch_path,
        provider=provider,
        sandbox=sandbox,
        settings=settings,
        dry_run=True,
    )

    report = await orchestrator.solve()

    assert report.status == "solved"
    assert report.flag == "flag{base64_decoded_successfully}"
    assert report.turns <= 2
    assert (ch_path / "state.json").exists()
    assert (ch_path / "report.md").exists()


@pytest.mark.asyncio
async def test_solve_reversing_synthetic(synthetic_suite, tmp_path):
    ch_path = synthetic_suite["rev_vault"]
    settings = Settings(workspace_root=str(tmp_path / "workspaces"), max_turns_per_challenge=5)

    responses = [
        # Turn 1: inspect python check
        json.dumps({
            "thought": "Run python to extract characters from target array",
            "hypothesis": "Reconstruct password from ord array",
            "action": "bash",
            "command": "python -c \"target = [102, 108, 97, 103, 123, 118, 97, 117, 108, 116, 95, 117, 110, 108, 111, 99, 107, 101, 100, 125]; print(''.join(chr(c) for c in target))\"",
            "explanation": "Convert ASCII codes back to characters",
        }),
        # Turn 2: submit flag
        json.dumps({
            "thought": "ASCII array reconstructs to flag{vault_unlocked}",
            "hypothesis": "Submit reconstructed flag",
            "action": "submit_flag",
            "command": "flag{vault_unlocked}",
            "explanation": "Verified solution",
        }),
    ]

    provider = MockProvider(responses=responses)
    sandbox = LocalSubprocessSandbox(challenge_dir=str(ch_path), workspace_root=settings.workspace_root)

    orchestrator = ChallengeOrchestrator(
        challenge_dir=ch_path,
        provider=provider,
        sandbox=sandbox,
        settings=settings,
        dry_run=True,
    )

    report = await orchestrator.solve()

    assert report.status == "solved"
    assert report.flag == "flag{vault_unlocked}"


@pytest.mark.asyncio
async def test_solve_give_up_behavior(synthetic_suite, tmp_path):
    ch_path = synthetic_suite["crypto_xor"]
    settings = Settings(workspace_root=str(tmp_path / "workspaces"), max_turns_per_challenge=5)

    responses = [
        json.dumps({
            "thought": "I cannot crack this cipher after multiple attempts",
            "hypothesis": "Exhausted viable approaches",
            "action": "give_up",
            "command": "",
            "explanation": "Giving up to save competition time",
        }),
    ]

    provider = MockProvider(responses=responses)
    sandbox = LocalSubprocessSandbox(challenge_dir=str(ch_path), workspace_root=settings.workspace_root)

    orchestrator = ChallengeOrchestrator(
        challenge_dir=ch_path,
        provider=provider,
        sandbox=sandbox,
        settings=settings,
        dry_run=True,
    )

    report = await orchestrator.solve()
    assert report.status == "gave_up"
    assert report.flag is None
