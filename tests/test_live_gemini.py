"""Live model verification test using the verified local agy.exe CLI adapter and Gemini 3.8 Flash."""

import pytest
from pathlib import Path
from backend.config import Settings
from backend.engine.orchestrator import ChallengeOrchestrator
from backend.providers.agy_cli import AgyCliProvider
from backend.sandbox import LocalSubprocessSandbox
from backend.synthetic_generator import generate_synthetic_challenges


@pytest.mark.asyncio
async def test_live_agy_gemini_solve(tmp_path):
    provider = AgyCliProvider(
        model="gemini-3.8-flash-medium",
        executable_path=r"D:\ADMIN\bin\agy.exe",
    )
    if not provider.is_available():
        pytest.skip("Antigravity CLI not available on system.")

    synth_dir = tmp_path / "synthetic"
    chals = generate_synthetic_challenges(synth_dir)
    target_chall = chals["crypto_base64"]

    settings = Settings(
        workspace_root=str(tmp_path / "workspaces"),
        max_turns_per_challenge=5,
        turn_timeout_seconds=90,
    )

    sandbox = LocalSubprocessSandbox(
        challenge_dir=str(target_chall),
        workspace_root=settings.workspace_root,
    )

    orchestrator = ChallengeOrchestrator(
        challenge_dir=target_chall,
        provider=provider,
        sandbox=sandbox,
        settings=settings,
        dry_run=True,
    )

    print("\n--- Starting Live Gemini 3.8 Flash Solver on crypto_base64 ---")
    report = await orchestrator.solve()

    print(f"\nFinal Result:")
    print(f"- Status: {report.status}")
    print(f"- Flag: {report.flag}")
    print(f"- Turns: {report.turns}")
    print(f"- Duration: {report.duration_seconds:.2f}s")
    print(f"- Tokens: {report.total_tokens}")

    assert report.status == "solved"
    assert "flag{base64_decoded_successfully}" in (report.flag or "").lower()
