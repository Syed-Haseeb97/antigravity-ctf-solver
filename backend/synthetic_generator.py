"""Synthetic test challenge generator for unit tests and local benchmarking."""

from __future__ import annotations

import base64
from pathlib import Path
import yaml


def generate_synthetic_challenges(base_dir: str | Path) -> dict[str, Path]:
    """Generate local synthetic challenges for testing without any external network dependency."""
    root = Path(base_dir)
    root.mkdir(parents=True, exist_ok=True)
    generated: dict[str, Path] = {}

    # 1. Simple Base64
    b64_dir = root / "crypto_base64"
    (b64_dir / "distfiles").mkdir(parents=True, exist_ok=True)
    (b64_dir / "metadata.yml").write_text(
        yaml.dump(
            {
                "name": "B64 Decode",
                "category": "crypto",
                "value": 50,
                "description": "Decode the attached base64 encoded secret string.",
                "solves": 120,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    flag_b64 = "flag{base64_decoded_successfully}"
    (b64_dir / "distfiles" / "secret.txt").write_text(
        base64.b64encode(flag_b64.encode()).decode(),
        encoding="utf-8",
    )
    generated["crypto_base64"] = b64_dir

    # 2. XOR Cipher
    xor_dir = root / "crypto_xor"
    (xor_dir / "distfiles").mkdir(parents=True, exist_ok=True)
    (xor_dir / "metadata.yml").write_text(
        yaml.dump(
            {
                "name": "Single Byte XOR",
                "category": "crypto",
                "value": 100,
                "description": "The secret was encrypted with a single-byte XOR key. Recover the key and plaintext.",
                "solves": 80,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    flag_xor = b"flag{xor_single_byte_cipher_cracked}"
    key = 0x5A
    encrypted_xor = bytes([b ^ key for b in flag_xor])
    (xor_dir / "distfiles" / "cipher.hex").write_text(encrypted_xor.hex(), encoding="utf-8")
    generated["crypto_xor"] = xor_dir

    # 3. Weak RSA
    rsa_dir = root / "crypto_weak_rsa"
    (rsa_dir / "distfiles").mkdir(parents=True, exist_ok=True)
    (rsa_dir / "metadata.yml").write_text(
        yaml.dump(
            {
                "name": "Mini RSA",
                "category": "crypto",
                "value": 100,
                "description": "Tiny primes were used for this RSA implementation. Factor n to find the flag.",
                "solves": 65,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    rsa_content = (
        "# RSA Parameters:\n"
        "n = 3233\n"
        "e = 17\n"
        "c = 2557\n"
        "# The flag is formatted as: flag{rsa_m42_factored}\n"
    )
    (rsa_dir / "distfiles" / "rsa.py").write_text(rsa_content, encoding="utf-8")
    generated["crypto_weak_rsa"] = rsa_dir

    # 4. Forensic Metadata
    forensics_dir = root / "forensic_exif"
    (forensics_dir / "distfiles").mkdir(parents=True, exist_ok=True)
    (forensics_dir / "metadata.yml").write_text(
        yaml.dump(
            {
                "name": "EXIF Hunter",
                "category": "forensics",
                "value": 75,
                "description": "Metadata holds secrets. Inspect the file comment.",
                "solves": 90,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    # Synthetic minimal JPEG with COM marker (0xFFFE) containing flag
    flag_exif = "flag{exif_metadata_extracted_properly}"
    com_data = flag_exif.encode("utf-8")
    com_len = len(com_data) + 2
    synthetic_jpg = (
        b"\xff\xd8"
        b"\xff\xfe" + com_len.to_bytes(2, "big") + com_data
        + b"\xff\xd9"
    )
    (forensics_dir / "distfiles" / "evidence.jpg").write_bytes(synthetic_jpg)
    generated["forensic_exif"] = forensics_dir

    # 5. Stego Appended Secret
    stego_dir = root / "stego_appended"
    (stego_dir / "distfiles").mkdir(parents=True, exist_ok=True)
    (stego_dir / "metadata.yml").write_text(
        yaml.dump(
            {
                "name": "Appended PNG",
                "category": "stego",
                "value": 100,
                "description": "Check what lies past the image trailer.",
                "solves": 70,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    # 1x1 valid PNG + appended flag
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
        b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4"
        b"\x00\x00\x00\x00IEND\xaeB`\x82"
        b"\nSECRET_FLAG=flag{appended_bytes_stego_found}\n"
    )
    (stego_dir / "distfiles" / "hidden.png").write_bytes(png_bytes)
    generated["stego_appended"] = stego_dir

    # 6. Reversing Vault
    rev_dir = root / "rev_vault"
    (rev_dir / "distfiles").mkdir(parents=True, exist_ok=True)
    (rev_dir / "metadata.yml").write_text(
        yaml.dump(
            {
                "name": "Vault Logic",
                "category": "rev",
                "value": 100,
                "description": "Analyze the Python verification logic to recover the secret password.",
                "solves": 85,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    vault_py = (
        "def check_pass(p):\n"
        "    target = [102, 108, 97, 103, 123, 118, 97, 117, 108, 116, 95, 117, 110, 108, 111, 99, 107, 101, 100, 125]\n"
        "    return [ord(c) for c in p] == target\n"
        "\n"
        "if __name__ == '__main__':\n"
        "    import sys\n"
        "    if len(sys.argv) > 1 and check_pass(sys.argv[1]):\n"
        "        print('Access Granted!')\n"
        "    else:\n"
        "        print('Denied')\n"
    )
    (rev_dir / "distfiles" / "vault.py").write_text(vault_py, encoding="utf-8")
    generated["rev_vault"] = rev_dir

    return generated


if __name__ == "__main__":
    out = generate_synthetic_challenges(r"D:\5TH vid\ctf ig\antigravity-cli\tests\synthetic")
    print(f"Generated {len(out)} synthetic challenges: {list(out.keys())}")
