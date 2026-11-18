"""Antigravity CLI — Hardware-friendly autonomous CTF solver workstation."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from backend.config import Settings

console = Console()

BANNER = r"""
 [bold cyan]   _    _ _ _ _  _    _           _       _ [/bold cyan]
 [bold cyan]  | |  | | | | || |  | |         | |     | |[/bold cyan]
 [bold cyan]  | |__| | | | || |__| | ___   __| | __ _| |_ ___[/bold cyan]
 [bold cyan]  |  __  | | | ||  __  |/ _ \ / _` |/ _` | __/ _ \[/bold cyan]
 [bold cyan]  | |  | | | | || |  | | (_) | (_| | (_| | ||  __/[/bold cyan]
 [bold cyan]  |_|  |_|_||_||_|  |_|\___/ \__,_|\__,_|\__\___|[/bold cyan]
 [dim]Autonomous Hardware-Friendly CTF Solving Workstation[/dim]
"""


@click.group()
@click.version_option(version="2.0.0", prog_name="antigravity")
def cli() -> None:
    """Antigravity CLI — Hardware-Friendly Autonomous CTF Workstation."""
    pass


# ── DOCTOR ────────────────────────────────────────────────────────────────────

@cli.command()
def doctor() -> None:
    """Diagnose environment, Docker, Antigravity CLI, and CTF capabilities."""
    console.print(BANNER)
    settings = Settings()

    table = Table(title="System Diagnostics & Readiness", box=box.ROUNDED)
    table.add_column("Component", style="bold white", width=22)
    table.add_column("Status", width=12)
    table.add_column("Details & Remediation")

    # 1. OS & Architecture
    import platform
    table.add_row(
        "Host OS",
        "[green]PASS[/green]",
        f"{platform.system()} {platform.release()} ({platform.machine()}) — {os.cpu_count()} CPU cores",
    )

    # 2. Python Environment
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    table.add_row(
        "Python Runtime",
        "[green]PASS[/green]" if sys.version_info >= (3, 11) else "[yellow]WARN[/yellow]",
        f"Python {py_ver} ({sys.executable})",
    )

    # 3. Drive D: Storage Policy
    ws_path = Path(settings.workspace_root)
    drive_ok = str(ws_path).upper().startswith("D:")
    table.add_row(
        "Workspace Storage",
        "[green]PASS[/green]" if drive_ok else "[yellow]WARN[/yellow]",
        f"Configured: {settings.workspace_root} (Drive D: isolated policy)",
    )

    # 4. Antigravity CLI (agy)
    from backend.providers.agy_cli import AgyCliProvider
    agy_prov = AgyCliProvider(executable_path=settings.agy_cli_path)
    if agy_prov.is_available():
        table.add_row(
            "Antigravity CLI",
            "[green]PASS[/green]",
            f"Found: {agy_prov.executable_path} (Zero-cost Gemini 3.8 Flash access)",
        )
    else:
        table.add_row(
            "Antigravity CLI",
            "[yellow]WARN[/yellow]",
            "agy executable not found on PATH or D:\\ADMIN\\bin\\agy.exe. Set AGY_CLI_PATH in .env",
        )

    # 5. Docker Desktop
    docker_which = shutil.which("docker")
    if docker_which:
        try:
            import subprocess
            res = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                table.add_row("Docker Engine", "[green]PASS[/green]", f"Docker Desktop running (Engine {res.stdout.strip()})")
            else:
                table.add_row("Docker Engine", "[yellow]WARN[/yellow]", "Docker CLI found but daemon not responding. Start Docker Desktop.")
        except Exception as e:
            table.add_row("Docker Engine", "[yellow]WARN[/yellow]", f"Docker check timed out or failed: {e}")
    else:
        table.add_row("Docker Engine", "[red]FAIL[/red]", "Docker not found on PATH. Install Docker Desktop.")

    # 6. Sandbox Docker Image
    try:
        import subprocess
        img_check = subprocess.run(["docker", "image", "inspect", settings.sandbox_image], capture_output=True, text=True, timeout=5)
        if img_check.returncode == 0:
            table.add_row("Sandbox Image", "[green]PASS[/green]", f"Image '{settings.sandbox_image}' built and ready.")
        else:
            table.add_row(
                "Sandbox Image",
                "[yellow]NOT BUILT[/yellow]",
                f"Image '{settings.sandbox_image}' missing. Run: antigravity setup --profile lite",
            )
    except Exception:
        table.add_row("Sandbox Image", "[dim]SKIPPED[/dim]", "Docker daemon inactive; using local fallback sandbox.")

    # 7. Hardware Profile Settings
    table.add_row(
        "Hardware Caps",
        "[green]PASS[/green]",
        f"Memory Limit: {settings.container_memory_limit} | NanoCPUs: {settings.container_cpu_count} | Max Active: {settings.max_concurrent_challenges}",
    )

    # 8. CTFd Configuration
    if settings.ctfd_token or (settings.ctfd_user and settings.ctfd_url != "http://localhost:8000"):
        table.add_row("CTFd Target", "[green]CONFIGURED[/green]", f"URL: {settings.ctfd_url} (Dry-run: {settings.dry_run})")
    else:
        table.add_row("CTFd Target", "[dim]DEFAULT[/dim]", f"URL: {settings.ctfd_url} (Local/Testing default)")

    console.print(table)
    console.print("\n[dim]To solve challenges locally: [bold]antigravity solve --challenge <path>[/bold][/dim]\n")


# ── SETUP ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--profile", type=click.Choice(["lite", "standard", "advanced"]), default="lite", help="Docker image profile to build")
@click.option("--no-docker", is_flag=True, help="Skip Docker build and only configure local directories")
def setup(profile: str, no_docker: bool) -> None:
    """Setup directories, synthetic challenges, and build the hardware-optimized sandbox image."""
    console.print(BANNER)
    settings = Settings()
    settings.ensure_directories()
    console.print(f"[green]✔[/green] Created runtime directories at: [cyan]{settings.workspace_root}[/cyan]")

    # Generate synthetic challenges for self-test
    from backend.synthetic_generator import generate_synthetic_challenges
    synth_dir = Path("tests") / "synthetic"
    synth_chals = generate_synthetic_challenges(synth_dir)
    console.print(f"[green]✔[/green] Generated {len(synth_chals)} synthetic test challenges in [cyan]{synth_dir}[/cyan]")

    if no_docker:
        console.print("[yellow]Skipping Docker image build (--no-docker selected).[/yellow]")
        return

    # Check Docker
    if not shutil.which("docker"):
        console.print("[red]Docker not found on PATH. Docker Desktop is required to build sandbox image.[/red]")
        return

    image_tag = f"ctf-sandbox-{profile}"
    dockerfile = f"sandbox/Dockerfile.{profile}"
    if not Path(dockerfile).exists():
        console.print(f"[red]Dockerfile not found at {dockerfile}[/red]")
        return

    console.print(f"\n[bold]Building Docker Sandbox ({profile.upper()} profile)...[/bold]")
    console.print(f"Command: docker build -f {dockerfile} -t {image_tag} .\n")

    import subprocess
    ret = subprocess.run(["docker", "build", "-f", dockerfile, "-t", image_tag, "."])
    if ret.returncode == 0:
        console.print(f"\n[green]✔ Sandbox image '{image_tag}' built successfully![/green]")
    else:
        console.print(f"\n[red]Docker build failed with code {ret.returncode}[/red]")


# ── TOOLS ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--sandbox", is_flag=True, help="Inspect tools inside the Docker sandbox")
def tools(sandbox: bool) -> None:
    """List available CTF analysis tools on host and in sandbox."""
    console.print(BANNER)
    settings = Settings()

    if not sandbox:
        console.print("[bold]Host Environment Tools:[/bold]")
        tool_checks = [
            ("python", sys.executable),
            ("git", shutil.which("git")),
            ("docker", shutil.which("docker")),
            ("uv", shutil.which("uv")),
            ("agy CLI", shutil.which("agy") or shutil.which("agy.exe") or settings.agy_cli_path),
        ]
        table = Table(box=box.SIMPLE)
        table.add_column("Tool", style="bold white")
        table.add_column("Path / Status")
        for name, path in tool_checks:
            table.add_row(name, f"[green]{path}[/green]" if path else "[dim]Not installed[/dim]")
        console.print(table)
        console.print("[dim]Use --sandbox to inspect tools inside the Docker container.[/dim]")
    else:
        async def _run_sandbox_check():
            from backend.engine.capabilities import detect_sandbox_capabilities
            from backend.sandbox import DockerSandbox
            box_inst = DockerSandbox(image=settings.sandbox_image, workspace_root=settings.workspace_root)
            console.print(f"Spinning up test sandbox '{settings.sandbox_image}'...")
            try:
                await box_inst.start()
                inv = await detect_sandbox_capabilities(box_inst)
                console.print(Panel(inv.summary_markdown(), title="Sandbox Capabilities", border_style="cyan"))
            finally:
                await box_inst.stop()
        asyncio.run(_run_sandbox_check())


# ── PULL ──────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--url", default=None, help="CTFd URL")
@click.option("--token", default=None, help="CTFd API token")
@click.option("--user", default=None, help="CTFd Username")
@click.option("--password", default=None, help="CTFd Password")
@click.option("--output", default="challenges", help="Output directory")
@click.option("--unlock-paid-hints", is_flag=True, help="Authorize spending points on paid hints (DANGEROUS)")
def pull(url: str | None, token: str | None, user: str | None, password: str | None, output: str, unlock_paid_hints: bool) -> None:
    """Safely pull challenges and distfiles from a CTFd competition."""
    console.print(BANNER)
    settings = Settings()
    ctfd_url = url or settings.ctfd_url
    ctfd_token = token or settings.ctfd_token
    ctfd_user = user or settings.ctfd_user
    ctfd_pass = password or settings.ctfd_pass

    from backend.ctfd import CTFdClient

    async def _do_pull():
        client = CTFdClient(
            base_url=ctfd_url,
            token=ctfd_token,
            username=ctfd_user,
            password=ctfd_pass,
            unlock_paid_hints=unlock_paid_hints,
        )
        try:
            console.print(f"Connecting to CTFd at [cyan]{ctfd_url}[/cyan]...")
            stubs = await client.fetch_challenge_stubs()
            console.print(f"Discovered [bold green]{len(stubs)}[/bold green] active challenges.")

            with console.status("[bold cyan]Downloading challenges...[/bold cyan]"):
                for stub in stubs:
                    ch_dir = await client.pull_challenge(stub, output)
                    console.print(f"  [green]✔[/green] {stub.get('name')} -> [dim]{ch_dir}[/dim]")
        finally:
            await client.close()

    asyncio.run(_do_pull())


# ── SOLVE ─────────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--challenge", required=True, help="Path to challenge directory")
@click.option("--model", default=None, help="Reasoning model spec (default: agy/gemini-3.8-flash-medium)")
@click.option("--no-docker", is_flag=True, help="Deprecated/Disabled: Host execution is blocked for security")
@click.option("--submit", is_flag=True, help="Submit flag to CTFd if found (default is dry-run)")
@click.option("--max-turns", default=25, type=int, help="Maximum reasoning turns")
def solve(challenge: str, model: str | None, no_docker: bool, submit: bool, max_turns: int) -> None:
    """Solve an individual CTF challenge using the autonomous reasoning loop."""
    console.print(BANNER)
    if no_docker:
        console.print("[bold red]SECURITY REJECTION[/bold red]: Host execution of untrusted CTF challenges is strictly forbidden. Isolated Docker container is mandatory.")
        sys.exit(1)

    settings = Settings()
    if max_turns:
        settings.max_turns_per_challenge = max_turns

    ch_path = Path(challenge)
    if not ch_path.exists():
        console.print(f"[red]Challenge path not found: {challenge}[/red]")
        sys.exit(1)

    from backend.ctfd import CTFdClient
    from backend.engine.orchestrator import ChallengeOrchestrator
    from backend.providers.factory import get_provider
    from backend.sandbox import DockerSandbox

    provider = get_provider(spec=model, settings=settings)
    console.print(f"Reasoning Provider: [bold cyan]{provider.name}[/bold cyan]")
    console.print(f"Execution Target: [bold white]{ch_path.resolve()}[/bold white]")
    console.print(f"Mode: {'[green]Live Submission[/green]' if submit else '[yellow]Dry Run (Safe Verification)[/yellow]'}")

    ctfd_client = None
    if submit and settings.ctfd_token:
        ctfd_client = CTFdClient(
            base_url=settings.ctfd_url,
            token=settings.ctfd_token,
            dry_run=False,
        )

    sandbox = DockerSandbox(
        image=settings.sandbox_image,
        challenge_dir=str(ch_path),
        memory_limit=settings.container_memory_limit,
        cpu_count=settings.container_cpu_count,
        workspace_root=settings.workspace_root,
    )
    console.print(f"Sandbox: [cyan]Docker Container ({settings.sandbox_image}) [Caps: {settings.container_memory_limit} RAM, {settings.container_cpu_count} CPUs][/cyan]")

    orchestrator = ChallengeOrchestrator(
        challenge_dir=ch_path,
        provider=provider,
        sandbox=sandbox,
        settings=settings,
        ctfd_client=ctfd_client,
        dry_run=not submit,
    )

    with console.status("[bold green]Agent investigating challenge...[/bold green]"):
        report = asyncio.run(orchestrator.solve())

    console.print()
    if report.status == "solved":
        console.print(Panel(
            f"[bold green]CHALLENGE SOLVED![/bold green]\n\n"
            f"Flag: [bold yellow]{report.flag}[/bold yellow]\n"
            f"Turns: {report.turns} | Time: {report.duration_seconds:.2f}s | Tokens: {report.total_tokens:,}\n"
            f"Report saved to: {ch_path / 'report.md'}",
            title="Result",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[bold red]Status: {report.status.upper()}[/bold red]\n\n"
            f"Turns: {report.turns} | Time: {report.duration_seconds:.2f}s\n"
            f"Investigation log: {ch_path / 'report.md'}",
            title="Result",
            border_style="red",
        ))


# ── BENCHMARK ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--suite", default="tests/synthetic", help="Path to benchmark challenge directory")
@click.option("--model", default="mock/default", help="Reasoning model spec (default: mock/default)")
@click.option("--docker/--no-docker", "use_docker", default=True, help="Run inside Docker container (default: True)")
@click.option("--report-file", default="benchmark_report.md", help="Output markdown report file")
def benchmark(suite: str, model: str, use_docker: bool, report_file: str) -> None:
    """Run benchmark evaluation across a challenge suite and generate metrics report."""
    console.print(BANNER)
    settings = Settings()
    suite_path = Path(suite)
    if not suite_path.exists():
        console.print(f"[yellow]Suite directory '{suite}' does not exist. Generating synthetic suite...[/yellow]")
        from backend.synthetic_generator import generate_synthetic_challenges
        generate_synthetic_challenges(suite_path)

    from backend.benchmark import BenchmarkRunner
    from backend.providers.factory import get_provider

    provider = get_provider(spec=model, settings=settings)
    sandbox_desc = f"Docker ({settings.sandbox_image})" if use_docker else "In-Memory MockSandbox (offline)"
    console.print(f"Running benchmark suite: [cyan]{suite_path}[/cyan]")
    console.print(f"Reasoning Model: [bold cyan]{provider.name}[/bold cyan]")
    console.print(f"Sandbox Environment: [bold white]{sandbox_desc}[/bold white]\n")

    runner = BenchmarkRunner(
        challenges_dir=suite_path,
        provider=provider,
        settings=settings,
        use_docker=use_docker,
    )

    with console.status("[bold green]Executing benchmark suite...[/bold green]"):
        summary = asyncio.run(runner.run())

    md_report = summary.to_markdown()
    Path(report_file).write_text(md_report, encoding="utf-8")

    console.print(Panel(
        f"[bold]Benchmark Completed[/bold]\n"
        f"Solved: [bold green]{summary.solved_count}[/bold green] / {summary.total_challenges} "
        f"([cyan]{summary.solve_rate_percent:.1f}%[/cyan])\n"
        f"Runtime: {summary.total_time_seconds:.2f}s | Total Tokens: {summary.total_tokens:,}\n"
        f"Report saved: [bold cyan]{report_file}[/bold cyan]",
        title="Summary",
        border_style="cyan",
    ))


# ── CLEANUP ───────────────────────────────────────────────────────────────────

@cli.command()
def cleanup() -> None:
    """Safely remove leftover CTF Docker containers and clean temporary workspaces."""
    console.print(BANNER)
    settings = Settings()

    # 1. Clean orphan Docker containers
    from backend.sandbox import cleanup_orphan_containers
    count = asyncio.run(cleanup_orphan_containers())
    console.print(f"[green]✔[/green] Removed {count} dangling CTF container(s).")

    # 2. Clean temporary workspaces on Drive D:
    ws_dir = Path(settings.workspace_root)
    cleaned_dirs = 0
    if ws_dir.exists():
        for item in ws_dir.iterdir():
            if item.is_dir() and (item.name.startswith("ws-") or item.name.startswith("local-ws-")):
                try:
                    shutil.rmtree(item, ignore_errors=True)
                    cleaned_dirs += 1
                except Exception:
                    pass
    console.print(f"[green]✔[/green] Cleaned {cleaned_dirs} temporary workspace folder(s) in {ws_dir}.")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
