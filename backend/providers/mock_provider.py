"""Mock provider for unit testing, CI pipelines, and deterministic offline benchmarking."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable

from backend.providers.base import BaseProvider, LLMResponse, LLMUsage


class MockProvider(BaseProvider):
    """Deterministic mock provider that returns configured responses or uses a smart solver heuristic."""

    def __init__(
        self,
        responses: list[str] | None = None,
        handler: Callable[[str, str], str] | None = None,
        model_name: str = "mock-gemini-3.8-flash",
    ) -> None:
        self.responses = list(responses) if responses else []
        self.handler = handler
        self.model = model_name
        self.call_history: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return f"mock/{self.model}"

    def is_available(self) -> bool:
        return True

    def _smart_heuristic(self, prompt: str) -> str:
        """Smart deterministic heuristic for solving synthetic benchmark challenges."""
        # 1. Base64
        if "b64 decode" in prompt.lower() or "secret.txt" in prompt.lower():
            if "Turn 1" in prompt:
                return json.dumps({
                    "thought": "Read and decode base64 secret file",
                    "hypothesis": "File contains base64 string",
                    "action": "bash",
                    "command": "python3 -c \"import base64; print(base64.b64decode(open('distfiles/secret.txt').read().strip()).decode())\"",
                    "explanation": "Decode base64",
                })
            return json.dumps({
                "thought": "Extracted flag from base64 decode",
                "hypothesis": "Submit flag",
                "action": "submit_flag",
                "command": "flag{base64_decoded_successfully}",
                "explanation": "Verified flag",
            })

        # 2. XOR
        if "single byte xor" in prompt.lower() or "cipher.hex" in prompt.lower():
            if "Turn 1" in prompt:
                return json.dumps({
                    "thought": "Brute force single-byte XOR key",
                    "hypothesis": "Single byte XOR key",
                    "action": "bash",
                    "command": "python3 -c \"data = bytes.fromhex(open('distfiles/cipher.hex').read().strip()); print([bytes([b ^ k for b in data]) for k in range(256) if b'flag{' in bytes([b ^ k for b in data])][0].decode())\"",
                    "explanation": "XOR brute force",
                })
            return json.dumps({
                "thought": "XOR key recovered successfully",
                "hypothesis": "Submit recovered XOR flag",
                "action": "submit_flag",
                "command": "flag{xor_single_byte_cipher_cracked}",
                "explanation": "Verified plaintext",
            })

        # 3. Mini RSA
        if "mini rsa" in prompt.lower() or "rsa.py" in prompt.lower():
            return json.dumps({
                "thought": "Factor n=3233 (p=61, q=53) and submit flag",
                "hypothesis": "Small prime factorization",
                "action": "submit_flag",
                "command": "flag{rsa_m42_factored}",
                "explanation": "Factored RSA modulus",
            })

        # 4. Forensic EXIF
        if "exif hunter" in prompt.lower() or "evidence.jpg" in prompt.lower():
            return json.dumps({
                "thought": "Extract comment metadata from JPEG",
                "hypothesis": "Comment contains flag",
                "action": "submit_flag",
                "command": "flag{exif_metadata_extracted_properly}",
                "explanation": "Extracted from JPEG header",
            })

        # 5. Stego Appended
        if "appended png" in prompt.lower() or "hidden.png" in prompt.lower():
            return json.dumps({
                "thought": "Found appended flag after IEND chunk",
                "hypothesis": "Appended plaintext bytes",
                "action": "submit_flag",
                "command": "flag{appended_bytes_stego_found}",
                "explanation": "Extracted from trailer",
            })

        # 6. Reversing Vault
        if "vault logic" in prompt.lower() or "vault.py" in prompt.lower():
            return json.dumps({
                "thought": "Reconstruct ASCII ord array to flag string",
                "hypothesis": "Target array contains char codes",
                "action": "submit_flag",
                "command": "flag{vault_unlocked}",
                "explanation": "Decoded ord array",
            })

        return json.dumps({
            "thought": "Generic fallback",
            "hypothesis": "None",
            "action": "give_up",
            "command": "",
            "explanation": "No known pattern",
        })

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        schema: dict[str, Any] | None = None,
        timeout_seconds: int = 10,
    ) -> LLMResponse:
        await asyncio.sleep(0.01)
        self.call_history.append({"prompt": prompt, "system_prompt": system_prompt})

        if self.handler:
            text = self.handler(prompt, system_prompt)
        elif self.responses:
            text = self.responses.pop(0)
        elif "smart" in self.model:
            text = self._smart_heuristic(prompt)
        else:
            text = '{"thought": "Mock thought", "action": "give_up", "explanation": "No more mock responses"}'

        usage = LLMUsage(
            input_tokens=len(prompt) // 4,
            output_tokens=len(text) // 4,
            thinking_tokens=10,
            total_tokens=(len(prompt) + len(text)) // 4 + 10,
        )

        return LLMResponse(
            text=text,
            usage=usage,
            duration_seconds=0.01,
            model_name=self.model,
            raw={"mock": True},
        )
