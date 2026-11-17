"""System and turn prompts for autonomous CTF challenge solving."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.engine.triage import ChallengeTriage

CATEGORY_STRATEGIES: dict[str, str] = {
    "crypto": (
        "- Identify algorithm: RSA, AES, XOR, substitution, or custom.\n"
        "- RSA: Check small n (factoring via sympy/factordb), small e (e=3 cube root), Wiener attack (d small), common modulus.\n"
        "- XOR/Sub: Single-byte brute force, known plaintext attack, frequency analysis.\n"
        "- Constraints: Formulate systems of equations using z3-solver in Python."
    ),
    "pwn": (
        "- Triage binary: run `file`, `checksec`, identify arch and protections (NX, Canary, PIE).\n"
        "- Decompile/disassemble main logic via radare2 (`r2 -qc 'aaa; pdf @main' <bin>`) or objdump.\n"
        "- Detect vulnerabilities: buffer overflow (gets, strcpy), format string (printf(buf)), use-after-free.\n"
        "- Develop pwntools exploit script in /challenge/workspace/exploit.py and execute it."
    ),
    "rev": (
        "- Triage: strings, file, objdump, nm.\n"
        "- Static analysis: Disassemble main and verification functions via radare2 or gdb.\n"
        "- Dynamic analysis: Trace system calls via ltrace or strace, set breakpoints in gdb.\n"
        "- Extract hardcoded arrays, XOR masks, or write a Z3 keygen script."
    ),
    "web": (
        "- Inspect headers, cookies, HTML source, and JavaScript files using curl or python requests.\n"
        "- Fuzz parameters for SQL injection (' or 1=1--), SSTI ({{7*7}}), directory traversal (../../etc/passwd).\n"
        "- Check robots.txt, .git, and common hidden endpoints."
    ),
    "forensics": (
        "- Metadata & File Carving: Run `file`, `exiftool`, `binwalk -e`, `foremost` on distfiles.\n"
        "- Inspect text & hex: Run `strings -a -n 8 <file> | grep -iE 'flag|ctf'` and `xxd`.\n"
        "- Network: For pcap files, extract HTTP requests or DNS queries using tshark or python scapy.\n"
        "- Memory dumps: Analyze with volatility3 (pslist, filescan, cmdline)."
    ),
    "stego": (
        "- Image integrity: Run `pngcheck -v`, inspect magic bytes.\n"
        "- Steghide: Run `steghide extract -sf <img.jpg> -p ''`.\n"
        "- Bit planes & LSB: Run `zsteg -a <img.png>` if installed, or write a Python PIL script to extract LSBs.\n"
        "- Hidden text: Check EXIF comments or run OCR with tesseract."
    ),
    "misc": (
        "- Inspect file contents, check for esoteric encodings (Base64, Hex, Morse, Brainfuck, Caesar).\n"
        "- Automate custom socket interaction or regex pattern matching using Python."
    ),
}


def build_system_prompt(category: str, capabilities_md: str) -> str:
    strategy = CATEGORY_STRATEGIES.get(category, CATEGORY_STRATEGIES["misc"])

    return f"""You are an elite, highly disciplined autonomous CTF competition solver.
Your sole mission is to find and extract the authentic competition flag for the assigned challenge.

{capabilities_md}

### Tactical Methodology:
1. **Formulate Hypotheses**: Before running commands, analyze evidence and identify 1-2 concrete hypotheses.
2. **Execute Targeted Tools**: Choose the most specific tool available in the sandbox. Run Python scripts for custom logic.
3. **Parse Output**: Scrutinize command output for flag strings, keys, or clues.
4. **Never Guess Dummy Flags**: Ignore generic placeholders like `CTF{{placeholder}}` or `flag{{test}}`.
5. **Acknowledge Errors**: If a command fails or produces empty output, pivot immediately to an alternative hypothesis.

### Category Playbook ({category.upper()}):
{strategy}

### Response Protocol:
You MUST respond with a single, valid JSON object matching this exact schema:
```json
{{
  "thought": "Deep reasoning analyzing current state and previous output",
  "hypothesis": "Specific hypothesis being tested this turn",
  "action": "bash | read_file | write_file | submit_flag | give_up",
  "command": "The exact shell command to run, file path, or flag string",
  "explanation": "Why this action directly validates the hypothesis"
}}
```

Available actions:
- `bash`: Run a bash command in the isolated container.
- `read_file`: Read a file path (e.g. `/challenge/distfiles/readme.txt`).
- `write_file`: Write script/exploit into `/challenge/workspace/script.py`. (Use `command` for filename, put file content in `thought` or use `bash` with python/heredoc).
- `submit_flag`: Submit an extracted candidate flag string (e.g. `flag{{...}}`).
- `give_up`: Only when all realistic attack avenues have been exhausted.
"""


def build_turn_prompt(
    triage: ChallengeTriage,
    turn: int,
    history_md: str,
    loop_warning: str | None = None,
) -> str:
    lines = [
        f"## Challenge: {triage.name} [{triage.detected_category.upper()}] ({triage.value} pts)",
        f"**Description**: {triage.description or 'No description'}",
    ]
    if triage.connection_info:
        lines.append(f"**Connection**: `{triage.connection_info}`")
    if triage.distfiles:
        lines.append(f"**Distfiles**: {', '.join(f'/challenge/distfiles/{f}' for f in triage.distfiles)}")

    lines.append(f"\n### Turn {turn} Execution History:")
    lines.append(history_md if history_md else "_Starting initial triage turn._")

    if loop_warning:
        lines.append(f"\n> ⚠️ **LOOP WARNING**: {loop_warning}")

    lines.append(
        "\nDetermine your next hypothesis and action. "
        "Return ONLY the structured JSON object with keys 'thought', 'hypothesis', 'action', 'command', 'explanation'."
    )
    return "\n".join(lines)
