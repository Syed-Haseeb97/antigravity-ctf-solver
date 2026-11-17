"""CTFd client — async httpx, token + session auth, safe file handling, and competition point protection."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import yaml
from markdownify import markdownify as html2md

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
FLAG_FORMAT_REGEX = re.compile(r"^[A-Za-z0-9_\-]+{[^\s]{3,120}}$")


@dataclass
class SubmitResult:
    status: str  # "correct" | "already_solved" | "incorrect" | "dry_run" | "rate_limited" | "unknown"
    message: str
    display: str


@dataclass
class CTFdClient:
    base_url: str = "http://localhost:8000"
    token: str = ""
    username: str = "admin"
    password: str = "admin"
    dry_run: bool = True
    unlock_paid_hints: bool = False

    _client: httpx.AsyncClient | None = field(default=None, repr=False)
    _csrf_token: str = ""
    _logged_in: bool = False
    _challenge_ids: dict[str, int] = field(default_factory=dict)
    _submitted_cache: set[tuple[str, str]] = field(default_factory=set)

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url.rstrip("/"),
                follow_redirects=False,
                verify=False,
                timeout=30.0,
                headers={"User-Agent": USER_AGENT},
            )
        return self._client

    async def _ensure_logged_in(self) -> None:
        if self._logged_in or self.token:
            return
        client = await self._ensure_client()

        try:
            resp = await client.get("/login")
            m = re.search(r'id="nonce"[^>]*value="([^"]+)"', resp.text)
            if not m:
                m = re.search(r'name="nonce"[^>]*value="([^"]+)"', resp.text)
            if not m:
                raise RuntimeError("Could not find nonce on CTFd login page")
            nonce = m.group(1)

            resp = await client.post(
                "/login",
                data={
                    "name": self.username,
                    "password": self.password,
                    "_submit": "Submit",
                    "nonce": nonce,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if resp.status_code == 200:
                raise RuntimeError("CTFd login failed — invalid username or password")
            self._logged_in = True
        except Exception as e:
            logger.error("CTFd login failed: %s", str(e).replace(self.password, "******"))
            raise

    async def _get_csrf(self) -> str:
        if self._csrf_token:
            return self._csrf_token
        client = await self._ensure_client()
        resp = await client.get("/challenges")
        m = re.search(r"csrfNonce':\s*\"([A-Fa-f0-9]+)\"", resp.text)
        if not m:
            raise RuntimeError("Could not find csrfNonce on CTFd challenges page")
        self._csrf_token = m.group(1)
        return self._csrf_token

    def _base_headers(self) -> dict[str, str]:
        h: dict[str, str] = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Token {self.token}"
        return h

    async def _get(self, path: str) -> Any:
        await self._ensure_logged_in()
        client = await self._ensure_client()
        resp = await client.get(f"/api/v1{path}", headers=self._base_headers())
        resp.raise_for_status()
        return resp.json()

    async def _post(self, path: str, body: dict[str, Any]) -> Any:
        await self._ensure_logged_in()
        client = await self._ensure_client()
        headers = self._base_headers()
        if not self.token:
            headers["CSRF-Token"] = await self._get_csrf()
        resp = await client.post(
            f"/api/v1{path}",
            json=body,
            headers=headers,
        )
        if resp.status_code == 403 and not self.token:
            self._csrf_token = ""
            headers["CSRF-Token"] = await self._get_csrf()
            resp = await client.post(
                f"/api/v1{path}",
                json=body,
                headers=headers,
            )
        resp.raise_for_status()
        return resp.json()

    async def fetch_challenge_stubs(self) -> list[dict[str, Any]]:
        """Fetch all visible challenge stubs with pagination handling."""
        page = 1
        stubs = []
        while True:
            data = await self._get(f"/challenges?per_page=100&page={page}")
            batch = data.get("data", [])
            if not batch:
                break
            for ch in batch:
                if ch.get("type") != "hidden" and ch.get("state") != "hidden":
                    stubs.append(ch)
            pagination = data.get("meta", {}).get("pagination", {})
            total_pages = pagination.get("pages", 1)
            if page >= total_pages:
                break
            page += 1
        return stubs

    async def get_challenge_id(self, name: str) -> int:
        if name in self._challenge_ids:
            return self._challenge_ids[name]

        stubs = await self.fetch_challenge_stubs()
        for ch in stubs:
            self._challenge_ids[ch["name"]] = ch["id"]

        if name not in self._challenge_ids:
            raise RuntimeError(f'Challenge "{name}" not found in CTFd')
        return self._challenge_ids[name]

    async def submit_flag(self, challenge_name: str, flag: str, force: bool = False) -> SubmitResult:
        """Submit a flag to CTFd with dry-run protection, deduplication, and format validation."""
        flag = flag.strip()

        # Validate format
        if not FLAG_FORMAT_REGEX.match(flag):
            logger.warning("Flag '%s' does not match standard CTF flag format pattern.", flag)

        cache_key = (challenge_name, flag)
        if cache_key in self._submitted_cache:
            return SubmitResult("already_submitted", "Already attempted locally", f"ALREADY SUBMITTED: {flag}")

        # Check dry-run mode
        if self.dry_run and not force:
            logger.info("DRY-RUN enabled: Recorded flag candidate '%s' for '%s' without sending.", flag, challenge_name)
            self._submitted_cache.add(cache_key)
            return SubmitResult(
                status="dry_run",
                message="Dry-run mode active. Flag not submitted to CTFd.",
                display=f'DRY RUN — Verified format for "{flag}". (Not submitted to CTFd)',
            )

        challenge_id = await self.get_challenge_id(challenge_name)
        try:
            resp = await self._post(
                "/challenges/attempt",
                {"challenge_id": challenge_id, "submission": flag},
            )
            self._submitted_cache.add(cache_key)
            data = resp.get("data", {})
            status = data.get("status", "unknown")
            message = data.get("message", "")

            if status == "correct":
                return SubmitResult("correct", message, f'CORRECT — "{flag}" accepted! {message}'.strip())
            if status == "already_solved":
                return SubmitResult("already_solved", message, f'ALREADY SOLVED — "{flag}" accepted. {message}'.strip())
            if status == "incorrect":
                return SubmitResult("incorrect", message, f'INCORRECT — "{flag}" rejected. {message}'.strip())
            if status == "paused":
                return SubmitResult("rate_limited", message, f'RATE LIMITED — {message}'.strip())
            return SubmitResult("unknown", message, f"CTFd Response: {status} ({message})")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                return SubmitResult("rate_limited", "Rate limited by CTFd", "RATE LIMITED: HTTP 429 Too Many Requests")
            raise

    async def pull_challenge(self, challenge: dict[str, Any], output_dir: str) -> str:
        """Download challenge distfiles and metadata.yml safely without directory traversal."""
        name = challenge.get("name", f"challenge-{challenge['id']}")
        ch_id = challenge.get("id", 0)

        # Sanitize folder slug (Windows safe)
        slug = re.sub(r'[<>:"/\\|?*.\x00-\x1f]', "", name.lower().strip())
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-") or f"challenge-{ch_id}"

        ch_dir = Path(output_dir) / slug
        ch_dir.mkdir(parents=True, exist_ok=True)

        await self._ensure_logged_in()
        client = await self._ensure_client()

        # Download distfiles
        for raw_url in challenge.get("files") or []:
            dist_dir = ch_dir / "distfiles"
            dist_dir.mkdir(exist_ok=True)
            url = raw_url if raw_url.startswith("http") else f"{self.base_url.rstrip('/')}/{raw_url.lstrip('/')}"
            url_path = urlparse(url).path
            fname = Path(url_path).name or "file"
            # Sanitize filename
            fname = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", fname)
            dest = dist_dir / fname

            if not dest.exists():
                try:
                    headers = self._base_headers() if urlparse(url).hostname == urlparse(self.base_url).hostname else {}
                    resp = await client.get(url, headers=headers, follow_redirects=True, timeout=60.0)
                    resp.raise_for_status()
                    dest.write_bytes(resp.content)
                    logger.info("Downloaded distfile: %s (%d bytes)", fname, len(resp.content))
                except Exception as e:
                    logger.warning("Failed to download %s: %s", url, e)

        # Process hints — NEVER spend points on paid hints unless explicitly permitted
        hints = []
        for h in challenge.get("hints") or []:
            cost = h.get("cost", 0)
            hint_id = h.get("id")
            content = h.get("content", "")

            # If content is hidden and cost is 0, unlock free hint
            if not content and cost == 0 and hint_id:
                try:
                    hint_resp = await self._post(f"/hints/{hint_id}", {})
                    content = hint_resp.get("data", {}).get("content", "")
                except Exception:
                    pass
            elif not content and cost > 0:
                if self.unlock_paid_hints and hint_id:
                    try:
                        hint_resp = await self._post(f"/hints/{hint_id}", {})
                        content = hint_resp.get("data", {}).get("content", "")
                        logger.info("UNLOCKED PAID HINT for '%s' (Cost: %d pts)", name, cost)
                    except Exception as e:
                        logger.warning("Could not unlock paid hint %s: %s", hint_id, e)
                else:
                    content = f"[Locked Hint — Cost: {cost} points. Run with --unlock-paid-hints to unlock]"

            hints.append({"cost": cost, "content": content})

        # Process markdown description
        desc = challenge.get("description") or ""
        try:
            desc = html2md(desc, heading_style="atx", escape_asterisks=False)
        except Exception:
            pass

        tags = [t["value"] if isinstance(t, dict) else str(t) for t in (challenge.get("tags") or [])]
        meta = {
            "id": ch_id,
            "name": name,
            "category": challenge.get("category", ""),
            "description": desc.strip(),
            "value": challenge.get("value", 0),
            "connection_info": challenge.get("connection_info") or "",
            "tags": tags,
            "solves": challenge.get("solves", 0),
            "hints": hints,
        }

        (ch_dir / "metadata.yml").write_text(
            yaml.dump(meta, allow_unicode=True, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )

        return str(ch_dir)

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
