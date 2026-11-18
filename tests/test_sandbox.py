"""Unit tests for sandboxes, resource limits, and mock sandbox isolation."""

import pytest
from pathlib import Path
from backend.sandbox import DockerSandbox, MockSandbox, ExecResult


def test_docker_sandbox_resource_parsing():
    box = DockerSandbox(memory_limit="3g", cpu_count=2.0)
    bytes_limit = box._parse_memory_limit()
    assert bytes_limit == 3 * 1024 * 1024 * 1024

    box_mb = DockerSandbox(memory_limit="512m")
    assert box_mb._parse_memory_limit() == 512 * 1024 * 1024

    box_invalid = DockerSandbox(memory_limit="invalid")
    assert box_invalid._parse_memory_limit() == 3 * 1024 * 1024 * 1024


@pytest.mark.asyncio
async def test_mock_sandbox_isolation(tmp_path):
    sandbox = MockSandbox()
    await sandbox.start()

    # Test file writing and reading in memory
    await sandbox.write_file("/challenge/workspace/test.txt", "hello ctf")
    content = await sandbox.read_file("/challenge/workspace/test.txt")
    assert content == "hello ctf"

    # Test listing
    files = await sandbox.list_files("/challenge/workspace")
    assert "test.txt" in files

    # Test exec
    res = await sandbox.exec("echo 'PONG'")
    assert isinstance(res, ExecResult)
    assert res.exit_code == 0
    assert "[mock-sandbox]" in res.stdout

    # Test stop/cleanup
    await sandbox.stop()
    assert len(sandbox.files) == 0
