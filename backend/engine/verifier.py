"""Authentic flag verification engine.
Validates flag candidates against live CTFd, cryptographic hashes in metadata.yml,
or in-sandbox validator scripts before marking challenges solved.
"""

from __future__ import annotations

import hashlib
import logging
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from backend.sandbox import ISandbox

logger = logging.getLogger(__name__)

DUMMY_FLAGS = {
    "ctf{placeholder}", "flag{placeholder}", "ctf{flag}", "flag{test}",
    "ctf{test}", "flag{here}", "ctf{here}", "flag{fake_flag}",
    "flag{example}", "ctf{example}", "flag{your_flag_here}",
}


@dataclass
class VerificationResult:
    verified: bool
    method: str  # "ctfd" | "local_sha256" | "local_exact" | "validator_script" | "unverifiable"
    message: str
    details: dict[str, Any] | None = None


async def verify_candidate_flag(
    candidate: str,
    challenge_dir: Path,
    sandbox: ISandbox | None = None,
    ctfd_client: Any = None,
    challenge_id: int | None = None,
    dry_run: bool = True,
) -> VerificationResult:
    """Rigorously verify a candidate flag against available oracles.
    
    Order of verification:
    1. Check for dummy/placeholder patterns.
    2. CTFd remote submission (if enabled and not dry_run).
    3. In-sandbox validation script (if validate.py exists).
    4. Cryptographic SHA-256 hash in metadata.yml / challenge.json.
    5. Plaintext flag in metadata.yml / challenge.json.
    6. Unverifiable fallback.
    """
    cleaned = candidate.strip()
    if not cleaned:
        return VerificationResult(
            verified=False,
            method="empty",
            message="Candidate flag is empty.",
        )

    # 1. Reject dummy / placeholder flags
    if cleaned.lower() in DUMMY_FLAGS:
        return VerificationResult(
            verified=False,
            method="dummy_check",
            message=f"'{cleaned}' is a known dummy or placeholder flag.",
        )

    # Load metadata
    meta: dict[str, Any] = {}
    meta_path = challenge_dir / "metadata.yml"
    if meta_path.exists():
        try:
            meta = yaml.safe_load(meta_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning("Could not read metadata.yml for verification: %s", e)

    # 2. Live CTFd verification
    if ctfd_client is not None and not dry_run and challenge_id is not None:
        try:
            res = await ctfd_client.submit_flag(challenge_id=challenge_id, flag=cleaned)
            if res.get("correct", False):
                return VerificationResult(
                    verified=True,
                    method="ctfd",
                    message="Accepted by live CTFd platform.",
                    details=res,
                )
            else:
                return VerificationResult(
                    verified=False,
                    method="ctfd",
                    message=f"Rejected by live CTFd platform: {res.get('message', 'Incorrect')}",
                    details=res,
                )
        except Exception as e:
            logger.error("CTFd live verification failed: %s", e)

    # 3. In-sandbox validation script
    if sandbox is not None:
        val_script = challenge_dir / "distfiles" / "validate.py"
        if val_script.exists():
            try:
                cmd = f"python3 /challenge/distfiles/validate.py {shlex.quote(cleaned)}"
                exec_res = await sandbox.exec(cmd, timeout_s=15)
                if exec_res.exit_code == 0:
                    return VerificationResult(
                        verified=True,
                        method="validator_script",
                        message="Passed in-sandbox validation script (validate.py).",
                        details={"stdout": exec_res.stdout},
                    )
                else:
                    return VerificationResult(
                        verified=False,
                        method="validator_script",
                        message=f"Failed in-sandbox validation script: {exec_res.stdout or exec_res.stderr}",
                        details={"exit_code": exec_res.exit_code, "stderr": exec_res.stderr},
                    )
            except Exception as e:
                logger.warning("Sandbox validation script execution error: %s", e)

    # 4. Cryptographic SHA-256 hash match
    expected_sha256 = meta.get("flag_sha256")
    if expected_sha256:
        cand_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest().lower()
        if cand_hash == expected_sha256.lower():
            return VerificationResult(
                verified=True,
                method="local_sha256",
                message="Cryptographic SHA-256 hash matches challenge metadata.",
                details={"hash": cand_hash},
            )
        else:
            return VerificationResult(
                verified=False,
                method="local_sha256",
                message="Cryptographic SHA-256 hash does not match challenge metadata.",
                details={"candidate_hash": cand_hash, "expected_hash": expected_sha256},
            )

    # 5. Plaintext flag match in metadata
    expected_flag = meta.get("flag")
    if expected_flag:
        if isinstance(expected_flag, list):
            valid = any(cleaned == f.strip() for f in expected_flag)
        else:
            valid = (cleaned == str(expected_flag).strip())

        if valid:
            return VerificationResult(
                verified=True,
                method="local_exact",
                message="Matches expected flag in challenge metadata.",
            )
        else:
            return VerificationResult(
                verified=False,
                method="local_exact",
                message="Does not match expected flag in challenge metadata.",
            )

    # 6. Unverifiable fallback
    return VerificationResult(
        verified=False,
        method="unverifiable",
        message="No verification oracle found (CTFd offline/dry-run, no validator script, no flag hash in metadata).",
    )
