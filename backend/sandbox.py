"""Docker and Subprocess Sandbox for CTF challenge solving.
Implements least-privilege isolation, hardware resource limits (3GB RAM, 2 CPUs),
and safe Drive D: workspace management.
"""

from __future__ import annotations

import asyncio
import io
import logging
import os
import shlex
import shutil
import tarfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONTAINER_LABEL = "antigravity-ctf-sandbox"
DEFAULT_WORKSPACE_ROOT = r"D:\5TH vid\ctf ig\.workspaces"

# Concurrency control — hardware friendly
_start_semaphore: asyncio.Semaphore | None = None
_active_count: int = 0
_count_lock = asyncio.Lock()


def configure_semaphore(max_concurrent: int = 2) -> None:
    """Limit concurrent container starts to prevent host resource starvation."""
    global _start_semaphore
    _start_semaphore = asyncio.Semaphore(max_concurrent)


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str


class ISandbox:
    """Common interface for execution sandboxes."""

    async def start(self) -> None: ...
    async def exec(self, command: str, timeout_s: int = 60) -> ExecResult: ...
    async def read_file(self, path: str) -> str: ...
    async def write_file(self, path: str, content: str) -> None: ...
    async def list_files(self, path: str) -> list[str]: ...
    async def stop(self) -> None: ...


@dataclass
class DockerSandbox(ISandbox):
    """Isolated Docker container with least-privilege security and strict resource caps."""

    image: str = "ctf-sandbox-lite"
    challenge_dir: str = ""
    memory_limit: str = "3g"
    cpu_count: float = 2.0
    workspace_root: str = DEFAULT_WORKSPACE_ROOT
    workspace_dir: str = ""
    _container: Any = field(default=None, repr=False)
    _docker: Any = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def container_id(self) -> str:
        if not self._container:
            raise RuntimeError("Sandbox not started")
        return self._container.id

    def _parse_memory_limit(self) -> int:
        s = self.memory_limit.strip().lower()
        try:
            if s.endswith("g"):
                return int(s[:-1]) * 1024 * 1024 * 1024
            if s.endswith("m"):
                return int(s[:-1]) * 1024 * 1024
            return int(s)
        except (ValueError, IndexError):
            logger.warning("Invalid memory_limit %r, defaulting to 3GB", self.memory_limit)
            return 3 * 1024 * 1024 * 1024

    async def start(self) -> None:
        import aiodocker

        sem = _start_semaphore or asyncio.Semaphore(2)
        async with sem:
            self._docker = aiodocker.Docker()

            # Create workspace directory strictly on Drive D:
            base_ws = Path(self.workspace_root)
            base_ws.mkdir(parents=True, exist_ok=True)
            self.workspace_dir = str(base_ws / f"ws-{uuid.uuid4().hex[:8]}")
            Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)

            binds: list[str] = [f"{self.workspace_dir}:/challenge/workspace:rw"]

            if self.challenge_dir:
                challenge_root = Path(self.challenge_dir).resolve()
                distfiles = challenge_root / "distfiles"
                meta_yml = challenge_root / "metadata.yml"

                if distfiles.exists():
                    binds.append(f"{distfiles}:/challenge/distfiles:ro")
                if meta_yml.exists():
                    binds.append(f"{meta_yml}:/challenge/metadata.yml:ro")

            # Security Hardening:
            # - NO SYS_ADMIN
            # - NO seccomp=unconfined
            # - NO /dev/loop-control
            # - Memory capped at 3GB
            # - NanoCpus capped at 2.0 cores
            config = {
                "Image": self.image,
                "Cmd": ["sleep", "infinity"],
                "WorkingDir": "/challenge",
                "Tty": False,
                "Labels": {CONTAINER_LABEL: "true"},
                "HostConfig": {
                    "Binds": binds,
                    "ExtraHosts": ["host.docker.internal:host-gateway"],
                    "CapAdd": ["SYS_PTRACE"],  # Required for gdb analysis
                    "Memory": self._parse_memory_limit(),
                    "NanoCpus": int(self.cpu_count * 1e9),
                },
            }

            self._container = await self._docker.containers.create(config)
            await self._container.start()

            info = await self._container.show()
            short_id = info["Id"][:12]
            logger.info("Sandbox started: %s (Memory: %s, CPUs: %.1f)", short_id, self.memory_limit, self.cpu_count)

    async def exec(self, command: str, timeout_s: int = 60) -> ExecResult:
        if not self._container:
            raise RuntimeError("Sandbox not started")

        async with self._lock:
            wrapped = f"timeout --signal=KILL --kill-after=5 {timeout_s} bash -c {shlex.quote(command)}"
            exec_instance = await self._container.exec(
                cmd=["bash", "-c", wrapped],
                stdout=True,
                stderr=True,
                tty=False,
            )

            stream = exec_instance.start(detach=False)
            stdout_chunks: list[bytes] = []
            stderr_chunks: list[bytes] = []

            async def _collect() -> None:
                while True:
                    msg = await stream.read_out()
                    if msg is None:
                        break
                    if msg.stream == 1:
                        stdout_chunks.append(msg.data)
                    else:
                        stderr_chunks.append(msg.data)

            try:
                await asyncio.wait_for(_collect(), timeout=timeout_s + 10)
            except asyncio.TimeoutError:
                try:
                    await stream.close()
                except Exception:
                    pass
                return ExecResult(
                    exit_code=-1,
                    stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"),
                    stderr=f"Command timed out after {timeout_s}s",
                )

            inspect = await exec_instance.inspect()
            exit_code = inspect.get("ExitCode", 0)
            return ExecResult(
                exit_code=exit_code,
                stdout=b"".join(stdout_chunks).decode("utf-8", errors="replace"),
                stderr=b"".join(stderr_chunks).decode("utf-8", errors="replace"),
            )

    async def read_file(self, path: str) -> str:
        res = await self.exec(f"cat {shlex.quote(path)}", timeout_s=15)
        if res.exit_code != 0:
            raise FileNotFoundError(f"Cannot read {path}: {res.stderr}")
        return res.stdout

    async def write_file(self, path: str, content: str) -> None:
        py_cmd = (
            f"python3 -c 'import sys, pathlib; "
            f"p = pathlib.Path(sys.argv[1]); p.parent.mkdir(parents=True, exist_ok=True); "
            f"p.write_text(sys.stdin.read(), encoding=\"utf-8\")' {shlex.quote(path)}"
        )
        escaped_content = shlex.quote(content)
        cmd = f"printf '%s' {escaped_content} | {py_cmd}"
        res = await self.exec(cmd, timeout_s=20)
        if res.exit_code != 0:
            raise RuntimeError(f"Cannot write {path}: {res.stderr}")

    async def list_files(self, path: str) -> list[str]:
        res = await self.exec(f"ls -1A {shlex.quote(path)} 2>/dev/null", timeout_s=10)
        if res.exit_code != 0:
            return []
        return [f.strip() for f in res.stdout.splitlines() if f.strip()]

    async def stop(self) -> None:
        if self._container:
            try:
                await self._container.delete(force=True)
            except Exception as e:
                logger.warning("Error deleting container: %s", e)
            self._container = None

        if self._docker:
            try:
                await self._docker.close()
            except Exception:
                pass
            self._docker = None

        if self.workspace_dir and Path(self.workspace_dir).exists():
            try:
                shutil.rmtree(self.workspace_dir, ignore_errors=True)
            except Exception:
                pass


@dataclass
class MockSandbox(ISandbox):
    """Purely in-memory, safe isolated mock sandbox for offline unit tests.
    Does NOT spawn any host shell processes or execute commands on Windows host.
    Guarantees zero host execution risks.
    """

    challenge_dir: str = ""
    workspace_root: str = DEFAULT_WORKSPACE_ROOT
    workspace_dir: str = ""
    files: dict[str, str] = field(default_factory=dict)
    cmd_handlers: dict[str, ExecResult] = field(default_factory=dict)

    async def start(self) -> None:
        self.workspace_dir = f"mock-ws-{uuid.uuid4().hex[:8]}"
        if self.challenge_dir:
            dist = Path(self.challenge_dir) / "distfiles"
            if dist.exists():
                for f in dist.rglob("*"):
                    if f.is_file():
                        try:
                            rel = f.relative_to(dist)
                            self.files[f"/challenge/distfiles/{rel.as_posix()}"] = f.read_text(
                                encoding="utf-8", errors="replace"
                            )
                        except Exception:
                            pass

    async def exec(self, command: str, timeout_s: int = 30) -> ExecResult:
        for pattern, res in self.cmd_handlers.items():
            if pattern in command:
                return res
        return ExecResult(exit_code=0, stdout="[mock-sandbox]", stderr="")

    async def read_file(self, path: str) -> str:
        norm = path.replace("\\", "/").strip()
        if norm in self.files:
            return self.files[norm]
        raise FileNotFoundError(f"File not found in mock sandbox: {path}")

    async def write_file(self, path: str, content: str) -> None:
        norm = path.replace("\\", "/").strip()
        self.files[norm] = content

    async def list_files(self, path: str) -> list[str]:
        norm = path.replace("\\", "/").strip()
        return [
            Path(k).name
            for k in self.files.keys()
            if k.startswith(norm)
        ]

    async def stop(self) -> None:
        self.files.clear()


async def cleanup_orphan_containers() -> int:
    """Kill any leftover ctf containers from previous runs."""
    try:
        import aiodocker
        docker = aiodocker.Docker()
        count = 0
        try:
            containers = await docker.containers.list(all=True)
            for c in containers:
                try:
                    data = await c.show()
                    cfg = data.get("Config", {}) or {}
                    labels = cfg.get("Labels", {}) or {}
                    image = cfg.get("Image", "") or ""
                    if (
                        labels.get(CONTAINER_LABEL)
                        or labels.get("ctf-agent")
                        or "ctf-sandbox" in image
                    ):
                        await c.delete(force=True)
                        count += 1
                except Exception:
                    pass
            if count > 0:
                logger.info("Cleaned up %d orphan CTF container(s)", count)
            return count
        finally:
            await docker.close()
    except Exception as e:
        logger.warning("Orphan container cleanup skipped: %s", e)
        return 0
