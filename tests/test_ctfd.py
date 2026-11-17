"""Unit tests for CTFd client with mocked HTTP interactions."""

import pytest
import respx
import httpx
from backend.ctfd import CTFdClient


@pytest.mark.asyncio
async def test_ctfd_dry_run_submission():
    client = CTFdClient(base_url="http://mock-ctfd", dry_run=True)
    res = await client.submit_flag("Test Challenge", "flag{sample_flag}")
    assert res.status == "dry_run"
    assert "Dry-run mode active" in res.message


@pytest.mark.asyncio
@respx.mock
async def test_ctfd_fetch_stubs():
    respx.get("http://mock-ctfd/api/v1/challenges?per_page=100&page=1").respond(
        200,
        json={
            "success": True,
            "data": [
                {"id": 1, "name": "Crypto 1", "category": "crypto", "type": "standard", "value": 100},
                {"id": 2, "name": "Hidden 1", "category": "misc", "type": "hidden", "value": 500},
            ],
            "meta": {"pagination": {"pages": 1}},
        },
    )

    client = CTFdClient(base_url="http://mock-ctfd", token="ctfd_test_token")
    stubs = await client.fetch_challenge_stubs()
    await client.close()

    assert len(stubs) == 1
    assert stubs[0]["name"] == "Crypto 1"


@pytest.mark.asyncio
@respx.mock
async def test_ctfd_submit_flag_live():
    respx.get("http://mock-ctfd/api/v1/challenges?per_page=100&page=1").respond(
        200,
        json={
            "success": True,
            "data": [{"id": 42, "name": "Web 1", "type": "standard"}],
            "meta": {"pagination": {"pages": 1}},
        },
    )
    respx.post("http://mock-ctfd/api/v1/challenges/attempt").respond(
        200,
        json={"success": True, "data": {"status": "correct", "message": "Flag verified!"}},
    )

    client = CTFdClient(base_url="http://mock-ctfd", token="ctfd_test_token", dry_run=False)
    res = await client.submit_flag("Web 1", "flag{winner}")
    await client.close()

    assert res.status == "correct"
    assert "accepted" in res.display
