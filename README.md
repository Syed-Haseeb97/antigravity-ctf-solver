# Antigravity CLI — Hardware-Friendly Autonomous CTF Workstation

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](https://github.com)
[![Brain](https://img.shields.io/badge/Brain-Gemini%203.8%20Flash%20(agy%20CLI)-orange)](https://deepmind.google)
[![Docker](https://img.shields.io/badge/Docker-Hardware--Optimized%20(3GB%20RAM)-green)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

An intelligent, resource-efficient autonomous CTF-solving workstation engineered specifically for competitive collegiate/university capture-the-flag jeopardy events.

Antigravity couples the reasoning capability of **Gemini 3.8 Flash** with an isolated, least-privilege Docker execution sandbox and an autonomous hypothesis-driven ReAct solver loop.

---

## 1. Laptop Hardware Profile (Target Architecture)

Upstream CTF agents often assume multi-cloud enterprise infrastructure with 16GB+ RAM per container, expensive Anthropic/OpenAI API quotas, and heavy dependencies (SageMath, PyTorch, CADO-NFS).

**Antigravity is re-architected for practical developer laptop hardware**:
- **Processor**: Modern 4+ Core x86_64 CPU (e.g. Intel Core i5/i7 or AMD Ryzen).
- **Physical Memory**: 8 GB+ RAM (Sandbox container capped at **3 GB RAM**, 2 CPU cores).
- **GPU**: Integrated or discrete GPU — all LLM reasoning runs offloaded via the native authenticated `agy` CLI with **zero local VRAM exhaustion**.
- **AI API Cost**: **$0.00**. Uses the existing authenticated Antigravity CLI (`agy.exe`) session with no paid OpenAI/Anthropic keys required.
- **Storage Isolation**: All temporary workspaces, challenge distfiles, and build artifacts reside strictly in isolated workspace directories (`.workspaces`), keeping system drives clean.
- **Zero Host Execution Policy**: Arbitrary challenge files and shell commands are strictly quarantined inside Docker containers (`DockerSandbox`). No untrusted code executes directly on the host.

---

## 2. System Architecture

```
                  ┌────────────────────────────────────────┐
                  │          ANTIGRAVITY CLI (CLI)         │
                  │ (doctor, setup, tools, solve, bench)   │
                  └──────────────────┬─────────────────────┘
                                     │
                  ┌──────────────────▼─────────────────────┐
                  │         ORCHESTRATION ENGINE           │
                  │  (Triage -> Hypothesis -> ReAct Loop)  │
                  └───────┬────────────────────────┬───────┘
                          │                        │
       [Zero-Cost Reasoner]                        [Hardened Sandbox]
                          │                        │
        ┌─────────────────▼────────┐      ┌────────▼────────────────┐
        │    Antigravity CLI       │      │   Docker Sandbox        │
        │   (Gemini 3.8 Flash)     │      │   - 3 GB RAM Cap        │
        │   via agy CLI / PATH     │      │   - 2 CPU Cores         │
        └──────────────────────────┘      │   - Privileged: False   │
                                          │   - Read-only distfiles │
                                          │   - No Host Execution   │
                                          └────────┬────────────────┘
                                                   │
                                          ┌────────▼────────────────┐
                                          │   Validation Oracle     │
                                          │  - validate.py Script   │
                                          │  - Cryptographic SHA256 │
                                          │  - CTFd API Submit      │
                                          └─────────────────────────┘
```

---

## 3. Verified Benchmark Results

The solver was evaluated across a 9-challenge benchmark suite (6 core jeopardy challenges + 3 complex multi-step challenges) comparing an offline deterministic heuristic baseline against live Gemini 3.8 Flash running inside the Docker sandbox.

### Honest Benchmark Performance Table

| Challenge Slug | Category | Difficulty | Deterministic Mock | Live Gemini 3.8 Flash (`agy`) | Turns | Wall Time | Verified Flag |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| `crypto_base64` | Crypto | Easy (50) | ✅ SOLVED | ✅ **SOLVED** | 2 | 97.0s | `flag{base64_decoded_successfully}` |
| `crypto_xor` | Crypto | Medium (100) | ✅ SOLVED | ✅ **SOLVED** | 4 | 121.4s | `flag{xor_single_byte_cracked}` |
| `crypto_weak_rsa` | Crypto | Medium (100) | ✅ SOLVED | ✅ **SOLVED** | 1 | 79.4s | `flag{rsa_m42_factored}` |
| `forensic_exif` | Forensics | Easy (75) | ✅ SOLVED | ✅ **SOLVED** | 2 | 70.9s | `flag{exif_metadata_extracted_properly}` |
| `stego_appended` | Stego | Medium (100) | ✅ SOLVED | ✅ **SOLVED** | 1 | 37.5s | `flag{appended_bytes_stego_found}` |
| `rev_vault` | Rev | Medium (100) | ✅ SOLVED | ✅ **SOLVED** | 7 | 205.2s | `flag{vault_unlocked}` |
| `crypto_multistep_stream` | Crypto | Hard (250) | ✅ SOLVED | ❌ **FAILED** | 8 (max) | 284.6s | _Exhausted turns on seed search_ |
| `forensic_multistep_artifact` | Forensics | Hard (250) | ✅ SOLVED | ✅ **SOLVED** | 5 | 204.2s | `flag{forensic_header_repaired_and_zip_carved_7719}` |
| `rev_multistep_vm` | Rev | Hard (300) | ✅ SOLVED | ✅ **SOLVED** | 7 | 262.5s | `flag{vm_bytecode_disassembled_and_reversed_31415}` |
| **Totals** | — | — | **9 / 9 (100%)** | **8 / 9 (88.9%)** | **29 turns** | **21.0 mins** | **API Cost: $0.00** |

Detailed logs and analysis are recorded in [benchmark_report.md](benchmark_report.md).

---

## 4. Authentic Flag Verification

In Antigravity, flags are never marked as "solved" based merely on LLM claims or regex extraction. Every candidate undergoes rigorous verification through:

1. **In-Sandbox Validation Script**: Executing `python3 /challenge/distfiles/validate.py <candidate>` inside the container.
2. **Cryptographic SHA-256 Hash Matching**: Comparing `hashlib.sha256(flag).hexdigest()` against the expected challenge hash without leaking plaintext flags.
3. **Remote CTFd Submission**: When `--submit` is provided, verifying with the official CTFd server endpoint.
4. **Dummy Flag Rejection**: Automatic rejection of placeholders (`flag{placeholder}`, `ctf{test}`).

---

## 5. Command Reference

### `antigravity doctor`
Runs comprehensive environment and configuration diagnostics.
```bash
antigravity doctor
```
Verifies:
- Host OS, architecture, and CPU topology.
- Python 3.11+ environment.
- Antigravity CLI (`agy.exe`) binary and Gemini authentication.
- Docker Desktop daemon status and resource caps.
- Drive D: storage isolation policy.
- CTFd competition settings.

### `antigravity setup [--profile lite|standard|advanced]`
Configures workspace directories, generates synthetic challenges, and builds the container image.
```bash
# Build the default fast Lite image (<1.5 GB, 3GB RAM cap)
antigravity setup --profile lite
```

### `antigravity tools [--profile lite|standard|advanced]`
Lists verified tools installed in the Docker sandbox image.
```bash
antigravity tools --profile lite
```

### `antigravity solve --challenge <path> [--submit]`
Launches the autonomous solver loop on a target challenge.
```bash
# Dry run solve (authenticates flag against challenge oracle without submitting to CTFd)
antigravity solve --challenge tests/synthetic/crypto_base64

# Live submission to CTFd platform
antigravity solve --challenge challenges/web_sqli --submit
```

### `antigravity benchmark [--suite <path>] [--docker / --no-docker]`
Executes an automated benchmark suite and outputs performance metrics.
```bash
# Run full benchmark inside Docker with Gemini 3.8 Flash
antigravity benchmark --suite tests/synthetic --model agy/gemini-3.8-flash-low

# Fast offline regression test with Mock sandbox
antigravity benchmark --suite tests/synthetic --model mock/smart --no-docker
```

### `antigravity cleanup`
Kills orphan CTF containers and cleans temporary workspaces on Drive D:.
```bash
antigravity cleanup
```

---

## 6. Docker Profiles & Resource Caps

| Profile | Image Name | Target Tooling | Memory Cap | CPU Cap | Typical Use |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **Lite** *(Default)* | `ctf-sandbox-lite` | Python 3, pwntools, pycryptodome, sympy, gmpy2, z3-solver, gdb, binutils, exiftool, steghide, requests | 3 GB RAM | 2.0 CPUs | 90% of jeopardy challenges |
| **Standard** | `ctf-sandbox-standard` | Adds radare2, foremost, sleuthkit, zsteg, volatility3, ropgadget | 4 GB RAM | 2.0 CPUs | Extended memory / forensics |
| **Advanced** | `ctf-sandbox-advanced` | Adds angr, RsaCtfTool | 6 GB RAM | 4.0 CPUs | Symbolic execution (on-demand) |

### Security Hardening Model
- **No `SYS_ADMIN`**: Containers run without dangerous root capabilities.
- **Restricted PTRACE**: Only `SYS_PTRACE` is granted for `gdb` debugging.
- **Seccomp active**: Host syscall filter is preserved.
- **Read-Only Mounts**: Challenge distfiles are mounted strictly as `:ro`.
- **Ephemeral Workspace**: Dynamic analysis is confined to an ephemeral workspace directory on Drive D:.
- **No Windows Host Subprocess Execution**: Execution on the host shell is completely blocked.

---

## 7. CTFd Competition Protection Policy

- **Dry Run Default**: Flag submissions are validated locally first; flags are never spammed to CTFd unless `--submit` is explicitly specified.
- **Point Protection**: The client **never** spends competition points on paid hints without the `--unlock-paid-hints` flag. Free hints (`cost == 0`) are extracted automatically.
- **Path Sanitization**: Challenge titles are sanitized to prevent Windows illegal characters (`:`, `*`, `?`, `"`, `<`, `>`, `|`) and prevent directory traversal attacks.

---

## 8. Open-Source Attribution & License

- **Upstream Agent**: Architectural patterns and message bus inspirations adapted from [`verialabs/ctf-agent`](https://github.com/verialabs/ctf-agent) (MIT License).
- **Benchmark Evaluation**: Benchmark design and dataset categorization influenced by KAIST [`CTFusion`](https://github.com/kaist-hacking/CTFusion) (MIT License).
- **CTFd Integration**: Compatible with [CTFd](https://github.com/CTFd/CTFd) REST API v1.
- **License**: MIT License. See [LICENSE](LICENSE) for full details.
