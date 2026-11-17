# Antigravity CLI — Hardware-Friendly Autonomous CTF Workstation

[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-blue)](https://github.com)
[![Model](https://img.shields.io/badge/Brain-Gemini%203.8%20Flash%20(agy%20CLI)-orange)](https://deepmind.google)
[![Docker](https://img.shields.io/badge/Docker-Hardware--Optimized%20(3GB%20RAM)-green)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-purple)](LICENSE)

An intelligent, resource-efficient autonomous CTF-solving workstation engineered specifically for competitive collegiate/university capture-the-flag jeopardy events.

Antigravity couples the reasoning capability of **Gemini 3.8 Flash** with an isolated, least-privilege Docker execution sandbox and an autonomous hypothesis-driven ReAct solver loop.

---

## 1. Laptop Hardware Profile (Target Architecture)

Upstream CTF agents often assume multi-cloud enterprise infrastructure with 16GB+ RAM per container, expensive Anthropic/OpenAI API quotas, and heavy dependencies (SageMath, PyTorch, CADO-NFS).

**Antigravity is re-architected for practical developer laptop hardware**:
- **Processor**: Intel Core i5 8th Gen (4 Cores / 8 Threads) or equivalent.
- **Physical Memory**: 16 GB RAM (Container capped at **3 GB RAM**, 2 CPU cores).
- **GPU**: NVIDIA MX130 (2 GB) — all LLM reasoning runs offloaded via the native authenticated `agy` CLI with **zero local VRAM exhaustion**.
- **AI API Cost**: **$0.00**. Uses the existing authenticated Antigravity CLI (`agy.exe`) session with no paid OpenAI/Anthropic keys required.
- **Drive D: Storage Isolation**: All temporary workspaces, challenge distfiles, and build artifacts reside strictly on **Drive D:** (`D:\5TH vid\ctf ig\.workspaces`), keeping host drive C: clean.

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
       [Zero-Cost Reasoner]                        [Isolated Execution]
                          │                        │
        ┌─────────────────▼────────┐      ┌────────▼────────────────┐
        │    Antigravity CLI       │      │   Docker Sandbox        │
        │   (Gemini 3.8 Flash)     │      │   - 3 GB RAM Cap        │
        │  via D:\ADMIN\bin\agy    │      │   - 2 CPU Cores         │
        └──────────────────────────┘      │   - Least Privilege     │
                                          │   - Read-only distfiles │
                                          └────────┬────────────────┘
                                                   │
                                          ┌────────▼────────────────┐
                                          │   Results & Evidence    │
                                          │  - state.json           │
                                          │  - report.md            │
                                          │  - Verified Flags       │
                                          └─────────────────────────┘
```

---

## 3. Command Reference

### `antigravity doctor`
Runs comprehensive environment and configuration diagnostics.
```bash
antigravity doctor
```
Verifies:
- Host OS, architecture, and CPU topology.
- Python 3.11+ environment.
- Antigravity CLI (`agy.exe`) binary and Gemini authentication.
- Docker Desktop daemon status.
- Sandbox image presence.
- Drive D: storage isolation policy.
- CTFd competition settings.

### `antigravity setup [--profile lite|standard|advanced]`
Configures workspace directories, generates synthetic challenges, and builds the container image.
```bash
# Build the default fast Lite image (<1.5 GB, 3GB RAM cap)
antigravity setup --profile lite

# Setup local testing without Docker
antigravity setup --no-docker
```

### `antigravity tools [--sandbox]`
Lists installed analysis tools on the host and inside the Docker sandbox.
```bash
antigravity tools
antigravity tools --sandbox
```

### `antigravity solve --challenge <path> [--submit]`
Launches the autonomous solver loop on a target challenge.
```bash
# Dry run solve (verifies flag locally without submitting to CTFd)
antigravity solve --challenge challenges/crypto_rsa

# Live submission to CTFd platform
antigravity solve --challenge challenges/web_sqli --submit
```

### `antigravity benchmark [--suite <path>]`
Executes an automated, reproducible benchmark suite and writes `benchmark_report.md`.
```bash
antigravity benchmark --suite tests/synthetic --model mock/smart
```

### `antigravity cleanup`
Kills orphan CTF containers and cleans temporary workspaces on Drive D:.
```bash
antigravity cleanup
```

---

## 4. Docker Profiles & Hardware Caps

| Profile | Image Name | Target Tooling | Memory Cap | Build Time |
| :--- | :--- | :--- | :--- | :--- |
| **Lite** *(Default)* | `ctf-sandbox-lite` | Python 3, pwntools, pycryptodome, sympy, gmpy2, z3-solver, gdb, radare2, exiftool, steghide, requests | 3 GB RAM, 2 CPUs | ~3-5 mins |
| **Standard** | `ctf-sandbox-standard` | Adds volatility3, zsteg, foremost, sleuthkit | 4 GB RAM, 2 CPUs | ~8-12 mins |
| **Advanced** | `ctf-sandbox-advanced` | Adds angr, RsaCtfTool (on-demand only) | 6 GB RAM, 4 CPUs | ~15-20 mins |

### Security Hardening
- **No `SYS_ADMIN`**: Containers run without dangerous root capabilities.
- **Restricted PTRACE**: Only `SYS_PTRACE` is allowed for `gdb` debugging.
- **Seccomp active**: Host syscall filter is preserved.
- **Read-Only Mounts**: Attached distfiles are mounted strictly as `:ro`.
- **Untrusted workspace**: Dynamic analysis is confined to an ephemeral workspace directory on Drive D:.

---

## 5. Quickstart Guide (Windows Laptop)

### Step 1: Open PowerShell in Project Directory
```powershell
cd "D:\5TH vid\ctf ig\antigravity-cli"
```

### Step 2: Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### Step 3: Run Diagnostics
```powershell
python -m backend.cli doctor
```

### Step 4: Run Automated Tests
```powershell
python -m pytest tests/ -v
```

### Step 5: Solve a Challenge
```powershell
python -m backend.cli solve --challenge tests/synthetic/crypto_base64
```

---

## 6. CTFd Competition Protection Policy

- **Dry Run Default**: Flag submissions are validated locally first; flags are never spammed to CTFd unless `--submit` is explicitly specified.
- **Point Protection**: The client **never** spends competition points on paid hints without the `--unlock-paid-hints` flag. Free hints (`cost == 0`) are extracted automatically.
- **Path Sanitization**: Challenge titles are sanitized to prevent Windows illegal characters (`:`, `*`, `?`, `"`, `<`, `>`, `|`) and prevent directory traversal attacks.

---

## 7. License

MIT License. See [LICENSE](LICENSE) for details. Upstream CTF-agent coordination patterns adapted from `verialabs/ctf-agent` (MIT) and benchmark evaluation paradigms from KAIST `CTFusion` (MIT).
