"""Unit tests for sandboxes and resource limits."""

import pytest
from pathlib import Path
from backend.sandbox import DockerSandbox, LocalSubprocessSandbox, ExecResult


def test_docker_sandbox_resource_parsing():
    box = DockerSandbox(memory_limit="3g", cpu_count=2.0)
    bytes_limit = box._parse_memory_limit()
    assert bytes_limit == 3 * 1024 * 1024 * 1024

    box_mb = DockerSandbox(memory_limit="512m")
    assert box_mb._parse_memory_limit() == 512 * 1024 * 1024

    box_invalid = DockerSandbox(memory_limit="invalid")
    assert box_invalid._parse_memory_limit() == 3 * 1024 * 1024 * 1024


@pytest.mark.asyncio
async def test_local_subprocess_sandbox_lifecycle(tmp_path):
    ws_root = tmp_path / "workspaces"
    sandbox = LocalSubprocessSandbox(workspace_root=str(ws_root))
    await sandbox.start()

    assert Path(sandbox.workspace_dir).exists()

    # Test file writing and reading
    await sandbox.write_file("test.txt", "hello ctf")
    content = await sandbox.read_file("test.txt")
    assert content == "hello ctf"

    # Test directory listing
    files = await sandbox.list_files(".")
    assert "test.txt" in files

    # Test exec
    res = await sandbox.exec("python -c \"print('PONG')\"")
    assert isinstance(res, ExecResult)
    assert res.exit_code == 0
    assert "PONG" in res.stdout

    # Test stop/cleanup
    await sandbox.stop()
    assert not Path(sandbox.workspace_dir).exists()
