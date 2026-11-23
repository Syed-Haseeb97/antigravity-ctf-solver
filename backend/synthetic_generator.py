"""Synthetic test challenge generator for unit tests and local benchmarking.
Generates 9 challenges across multiple CTF disciplines including multi-step challenges,
cryptographic SHA-256 hashes, and in-sandbox validation scripts (validate.py).
"""

from __future__ import annotations

import base64
import hashlib
import io
import struct
import zipfile
from pathlib import Path
import yaml


def _make_validator_script(flag: str) -> str:
    flag_hash = hashlib.sha256(flag.strip().encode("utf-8")).hexdigest()
    return f"""import sys
import hashlib

EXPECTED_HASH = "{flag_hash}"

def main():
    if len(sys.argv) < 2:
        cand = sys.stdin.read().strip()
    else:
        cand = sys.argv[1].strip()

    h = hashlib.sha256(cand.encode("utf-8")).hexdigest()
    if h == EXPECTED_HASH:
        print("VALID: Flag accepted!")
        sys.exit(0)
    else:
        print("INVALID: Incorrect flag.")
        sys.exit(1)

if __name__ == "__main__":
    main()
"""


def generate_synthetic_challenges(base_dir: str | Path) -> dict[str, Path]:
    """Generate 9 synthetic challenges (6 classic + 3 multi-step) with authentic validation oracles."""
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Path] = {}

    def _setup_ch(slug: str, meta: dict, flag: str) -> tuple[Path, Path]:
        ch_dir = root / slug
        dist = ch_dir / "distfiles"
        dist.mkdir(parents=True, exist_ok=True)
        meta["flag"] = flag
        meta["flag_sha256"] = hashlib.sha256(flag.encode("utf-8")).hexdigest()
        (ch_dir / "metadata.yml").write_text(yaml.dump(meta, sort_keys=False), encoding="utf-8")
        (dist / "validate.py").write_text(_make_validator_script(flag), encoding="utf-8")
        generated[slug] = ch_dir
        return ch_dir, dist

    # 1. Simple Base64
    flag1 = "flag{base64_decoded_successfully}"
    ch1, dist1 = _setup_ch(
        "crypto_base64",
        {
            "name": "B64 Decode",
            "category": "crypto",
            "value": 50,
            "description": "Decode the attached base64 encoded secret string.",
            "solves": 120,
        },
        flag1,
    )
    (dist1 / "secret.txt").write_text(base64.b64encode(flag1.encode()).decode(), encoding="utf-8")

    # 2. XOR Cipher
    flag2 = "flag{xor_single_byte_cracked}"
    ch2, dist2 = _setup_ch(
        "crypto_xor",
        {
            "name": "Single Byte XOR",
            "category": "crypto",
            "value": 100,
            "description": "The secret was encrypted with a single-byte XOR key. Recover the key and plaintext.",
            "solves": 80,
        },
        flag2,
    )
    key2 = 0x5A
    encrypted_xor = bytes([b ^ key2 for b in flag2.encode("utf-8")])
    (dist2 / "cipher.hex").write_text(encrypted_xor.hex(), encoding="utf-8")

    # 3. Weak RSA
    flag3 = "flag{rsa_m42_factored}"
    ch3, dist3 = _setup_ch(
        "crypto_weak_rsa",
        {
            "name": "Mini RSA",
            "category": "crypto",
            "value": 100,
            "description": "Tiny primes were used for this RSA implementation. Factor n to find the flag.",
            "solves": 65,
        },
        flag3,
    )
    rsa_content = (
        "# RSA Parameters:\n"
        "n = 3233\n"
        "e = 17\n"
        "c = 2557\n"
        "# The flag is formatted as: flag{rsa_m42_factored}\n"
    )
    (dist3 / "rsa.py").write_text(rsa_content, encoding="utf-8")

    # 4. Forensic Metadata
    flag4 = "flag{exif_metadata_extracted_properly}"
    ch4, dist4 = _setup_ch(
        "forensic_exif",
        {
            "name": "EXIF Hunter",
            "category": "forensics",
            "value": 75,
            "description": "Metadata holds secrets. Inspect the file comment.",
            "solves": 90,
        },
        flag4,
    )
    com_data = flag4.encode("utf-8")
    com_len = len(com_data) + 2
    synthetic_jpg = (
        b"\xff\xd8"
        b"\xff\xfe" + com_len.to_bytes(2, "big") + com_data
        + b"\xff\xd9"
    )
    (dist4 / "evidence.jpg").write_bytes(synthetic_jpg)

    # 5. Stego Appended Secret
    flag5 = "flag{appended_bytes_stego_found}"
    ch5, dist5 = _setup_ch(
        "stego_appended",
        {
            "name": "Appended PNG",
            "category": "stego",
            "value": 100,
            "description": "Check what lies past the image trailer.",
            "solves": 70,
        },
        flag5,
    )
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
        b"\nSECRET_FLAG=flag{appended_bytes_stego_found}\n"
    )
    (dist5 / "hidden.png").write_bytes(png_bytes)

    # 6. Reversing Vault
    flag6 = "flag{vault_unlocked}"
    ch6, dist6 = _setup_ch(
        "rev_vault",
        {
            "name": "Vault Logic",
            "category": "rev",
            "value": 100,
            "description": "Analyze the Python verification logic to recover the secret password.",
            "solves": 85,
        },
        flag6,
    )
    vault_py = (
        "def check_pass(p):\n"
        f"    target = {[ord(c) for c in flag6]}\n"
        "    return [ord(c) for c in p] == target\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    import sys\n"
        "    if len(sys.argv) > 1 and check_pass(sys.argv[1]):\n"
        "        print('Access Granted!')\n"
        "    else:\n"
        "        print('Denied')\n"
    )
    (dist6 / "vault.py").write_text(vault_py, encoding="utf-8")

    # ── HARDER MULTI-STEP CHALLENGES ───────────────────────────────────────────

    # 7. Multi-step Crypto: Broken Stream Cipher (LCG Seed Recovery + Chunk Reversal)
    flag7 = "flag{lcg_stream_seed_recovered_and_inverted_9482}"
    ch7, dist7 = _setup_ch(
        "crypto_multistep_stream",
        {
            "name": "Broken Stream",
            "category": "crypto",
            "value": 250,
            "description": (
                "An intercepted encrypted transmission and the encryption generator script. "
                "The cipher uses a 32-bit linear congruential generator seeded with a 16-bit offset. "
                "Crack the generator seed using known plaintext, decrypt the chunk-reversed ciphertext, and recover the flag."
            ),
            "solves": 32,
        },
        flag7,
    )
    # LCG constants
    A = 1664525
    C = 1013904223
    M = 2**32
    secret_seed = 0x84E1  # 16-bit seed in [0x8000, 0x9000]

    def _lcg_keystream(seed: int, length: int) -> bytes:
        state = seed
        stream = bytearray()
        for _ in range(length):
            state = (A * state + C) % M
            stream.append((state >> 16) & 0xFF)
        return bytes(stream)

    flag7_bytes = flag7.encode("utf-8")
    # Pad to multiple of 4
    pad_len = (4 - (len(flag7_bytes) % 4)) % 4
    padded_flag7 = flag7_bytes + (b"\x00" * pad_len)
    # Chunk reversal: reverse each 4-byte block
    chunk_rev = bytearray()
    for i in range(0, len(padded_flag7), 4):
        chunk_rev.extend(padded_flag7[i:i+4][::-1])
    ks7 = _lcg_keystream(secret_seed, len(chunk_rev))
    cipher7 = bytes([c ^ k for c, k in zip(chunk_rev, ks7)])

    encrypt_py = f"""# Linear Congruential Keystream Generator
A = 1664525
C = 1013904223
M = 2**32

class StreamCipher:
    def __init__(self, seed: int):
        self.state = seed

    def next_byte(self) -> int:
        self.state = (A * self.state + C) % M
        return (self.state >> 16) & 0xFF

def encrypt(data: bytes, seed: int) -> bytes:
    cipher = StreamCipher(seed)
    pad = (4 - (len(data) % 4)) % 4
    data += b"\\x00" * pad
    chunked = bytearray()
    for i in range(0, len(data), 4):
        chunked.extend(data[i:i+4][::-1])
    ks = bytes([cipher.next_byte() for _ in range(len(chunked))])
    return bytes([c ^ k for c, k in zip(chunked, ks)])

# The target seed was generated as a 16-bit offset in range [0x8000, 0x9000]
# Known plaintext prefix: "flag{{"
"""
    (dist7 / "encrypt.py").write_text(encrypt_py, encoding="utf-8")
    (dist7 / "ciphertext.hex").write_text(cipher7.hex(), encoding="utf-8")

    # 8. Multi-step Forensics: Corrupted Header + Metadata Passphrase + Embedded Protected Archive
    flag8 = "flag{forensic_header_repaired_and_zip_carved_7719}"
    ch8, dist8 = _setup_ch(
        "forensic_multistep_artifact",
        {
            "name": "Corrupted Artifact Carve",
            "category": "forensics",
            "value": 250,
            "description": (
                "A damaged forensic disk artifact was dumped from an adversary node. "
                "The file header magic bytes have been zeroed out. "
                "Repair the file format header, recover the embedded authentication passphrase from the comment, "
                "carve the appended encrypted zip archive, and unlock the flag."
            ),
            "solves": 25,
        },
        flag8,
    )
    # Valid PNG containing metadata comment, followed by zip
    # Construct zip in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Note: standard zip with password
        zf.setpassword(b"k3y_c4rv1ng_99")
        zf.writestr("flag.txt", flag8.encode("utf-8"))
    zip_bytes = zip_buffer.getvalue()

    # Minimal PNG image bytes with tEXt chunk containing passphrase
    comment_text = b"Passphrase: k3y_c4rv1ng_99"
    text_chunk = (
        len(comment_text + b"Comment\x00").to_bytes(4, "big")
        + b"tEXt"
        + b"Comment\x00" + comment_text
        + b"\x00\x00\x00\x00"  # CRC placeholder
    )
    raw_png = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        + text_chunk
        + b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        + b"\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    # Corrupt the first 8 bytes of PNG magic:
    corrupted_artifact = b"\x00" * 8 + raw_png[8:] + zip_bytes
    (dist8 / "damaged.bin").write_bytes(corrupted_artifact)

    # 9. Multi-step Reverse Engineering: Bytecode VM Interpreter Reversal
    flag9 = "flag{vm_bytecode_disassembled_and_reversed_31415}"
    ch9, dist9 = _setup_ch(
        "rev_multistep_vm",
        {
            "name": "Bytecode Enigma",
            "category": "rev",
            "value": 300,
            "description": (
                "A custom virtual machine evaluates input keys. "
                "Analyze the instruction decoder and transformation rules (XOR, ADD, ROL), "
                "reverse the bytecode pipeline, and find the flag that triggers 'ACCESS GRANTED'."
            ),
            "solves": 18,
        },
        flag9,
    )
    # Compute target array for flag9
    flag9_bytes = flag9.encode("utf-8")
    # VM op: for byte b at idx i: out[i] = (((b ^ 0x4B) + 13) % 256) ^ ((i * 7) % 256)
    def _vm_transform(data: bytes) -> list[int]:
        res = []
        for i, b in enumerate(data):
            t = (b ^ 0x4B)
            t = (t + 13) % 256
            t = t ^ ((i * 7) % 256)
            res.append(t)
        return res

    vm_target = _vm_transform(flag9_bytes)
    vm_py = f"""import sys

TARGET = {vm_target}

def vm_run(key: str) -> bool:
    if len(key) != {len(flag9)}:
        return False
    data = [ord(c) for c in key]
    res = []
    for i, b in enumerate(data):
        # Instruction stream:
        # OP 0x01: XOR_CONST 0x4B
        t = (b ^ 0x4B)
        # OP 0x02: ADD_CONST 13 (mod 256)
        t = (t + 13) % 256
        # OP 0x03: XOR_INDEX_MOD (i * 7)
        t = t ^ ((i * 7) % 256)
        res.append(t)
    return res == TARGET

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if vm_run(sys.argv[1]):
            print("ACCESS GRANTED")
            sys.exit(0)
    print("ACCESS DENIED")
    sys.exit(1)
"""
    (dist9 / "vm_checker.py").write_text(vm_py, encoding="utf-8")

    return generated


if __name__ == "__main__":
    out = generate_synthetic_challenges(Path("tests") / "synthetic")
    print(f"Generated {len(out)} synthetic challenges: {list(out.keys())}")
