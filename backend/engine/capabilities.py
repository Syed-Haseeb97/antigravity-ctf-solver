"""Tool inventory and capability detection inside the execution sandbox."""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.sandbox import ISandbox

logger = logging.getLogger(__name__)

COMMON_BINARIES = [
    "python3", "bash", "curl", "wget", "nc", "strings", "xxd", "file",
    "gdb", "r2", "readelf", "objdump", "exiftool", "steghide",
    "pngcheck", "tesseract", "zsteg", "volatility", "foremost"
]

COMMON_PYTHON_MODULES = [
    "pwntools", "Crypto", "sympy", "gmpy2", "z3", "PIL", "requests", "angr"
]


@dataclass
class ToolInventory:
    binaries: dict[str, bool] = field(default_factory=dict)
    python_modules: dict[str, bool] = field(default_factory=dict)
    custom_notes: list[str] = field(default_factory=list)

    def summary_markdown(self) -> str:
        avail_bins = [b for b, ok in self.binaries.items() if ok]
        avail_py = [m for m, ok in self.python_modules.items() if ok]

        lines = [
            "### Verified Sandbox Capabilities",
            f"- **System Binaries**: {', '.join(avail_bins) if avail_bins else 'standard shell'}",
            f"- **Python CTF Packages**: {', '.join(avail_py) if avail_py else 'python standard library'}",
        ]
        return "\n".join(lines)


async def detect_sandbox_capabilities(sandbox: ISandbox) -> ToolInventory:
    """Inspect the live sandbox to verify which tools are genuinely present."""
    from backend.sandbox import LocalSubprocessSandbox

    inv = ToolInventory()

    # Fast path for LocalSubprocessSandbox
    if isinstance(sandbox, LocalSubprocessSandbox):
        for b in COMMON_BINARIES:
            inv.binaries[b] = bool(shutil.which(b) or shutil.which(f"{b}.exe"))
        for p in COMMON_PYTHON_MODULES:
            try:
                __import__(p)
                inv.python_modules[p] = True
            except Exception:
                inv.python_modules[p] = False
        return inv

    # For DockerSandbox, run python inside container to test availability safely
    py_check_script = (
        "import shutil, json, sys\n"
        f"bins = {repr(COMMON_BINARIES)}\n"
        f"pkgs = {repr(COMMON_PYTHON_MODULES)}\n"
        "bin_res = {b: bool(shutil.which(b)) for b in bins}\n"
        "pkg_res = {}\n"
        "for p in pkgs:\n"
        "    try:\n"
        "        __import__(p)\n"
        "        pkg_res[p] = True\n"
        "    except Exception:\n"
        "        pkg_res[p] = False\n"
        "print(json.dumps({'binaries': bin_res, 'modules': pkg_res}))\n"
    )
    import json
    res = await sandbox.exec(f"python3 -c {repr(py_check_script)}", timeout_s=15)
    if res.exit_code == 0:
        try:
            data = json.loads(res.stdout.strip())
            inv.binaries = data.get("binaries", {})
            inv.python_modules = data.get("modules", {})
        except Exception:
            pass

    return inv
