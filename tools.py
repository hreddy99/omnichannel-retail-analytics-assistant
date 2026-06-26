#!/usr/bin/env python3
"""
Project task runner for the Omnichannel Retail Analytics Assistant.

A single, dependency-free entry point (uses only the Python standard library) so
you can set up and run everything from a command prompt:

    python tools.py setup       # create .venv and install all dependencies
    python tools.py validate    # run the synthetic-data validation checks
    python tools.py run          # launch the Streamlit app
    python tools.py doctor      # print environment / tool status
    python tools.py all          # setup -> validate -> run  (default)

Extra args after `run` are passed to Streamlit, e.g.:

    python tools.py run --server.port 8502

Run `python tools.py` (no arguments) to do setup + validate + launch in one go.
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
IS_WINDOWS = os.name == "nt"

# Local LLM (Ollama) — installed as part of setup so the app runs with real drafting,
# not just the deterministic fallback. Model is chosen by available RAM.
OLLAMA_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_FALLBACK_MODEL = os.getenv("OLLAMA_FALLBACK_MODEL", "qwen2.5:3b")
RAM_FOR_DEFAULT_GB = 10.0     # >= this -> pull the 7B model; otherwise the 3B model
RAM_MIN_GB = 6.0              # below this we warn that the model may be slow


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _banner(text: str) -> None:
    print(f"\n\033[1;34m== {text} ==\033[0m" if not IS_WINDOWS else f"\n== {text} ==")


def venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if IS_WINDOWS else "bin/python")


def _run(cmd: list[str], **kw) -> int:
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.call(cmd, cwd=ROOT, **kw)


def ensure_venv() -> Path:
    """Create the virtual environment if it does not exist; return its python."""
    py = venv_python()
    if py.exists():
        return py
    _banner("Creating virtual environment (.venv)")
    venv.create(VENV_DIR, with_pip=True)
    if not py.exists():
        sys.exit("ERROR: virtual environment creation failed.")
    return py


# --------------------------------------------------------------------------
# hardware + local LLM (Ollama)
# --------------------------------------------------------------------------
def total_ram_gb() -> float:
    """Best-effort total physical RAM in GB (stdlib only, cross-platform)."""
    try:
        if IS_WINDOWS:
            import ctypes

            class _MS(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            ms = _MS(); ms.dwLength = ctypes.sizeof(_MS)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
            return ms.ullTotalPhys / (1024 ** 3)
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
    except Exception:
        return 0.0


def _ollama_daemon_up() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        return True
    except Exception:
        return False


def _ollama_models() -> list[str]:
    try:
        import json
        import urllib.request
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3) as r:
            return [m.get("model", "") for m in json.load(r).get("models", [])]
    except Exception:
        return []


def _install_ollama() -> bool:
    if shutil.which("ollama"):
        return True
    system = platform.system()
    if system == "Linux":
        _banner("Installing Ollama (official install script)")
        return _run(["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"]) == 0
    if system == "Darwin":
        if shutil.which("brew"):
            _banner("Installing Ollama via Homebrew")
            return _run(["brew", "install", "ollama"]) == 0
        print("  Install Ollama for macOS from https://ollama.com/download (or `brew install ollama`).")
        return False
    if IS_WINDOWS:
        if shutil.which("winget"):
            _banner("Installing Ollama via winget")
            return _run(["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent"]) == 0
        print("  Install Ollama for Windows from https://ollama.com/download")
        return False
    print(f"  Unsupported platform {system}; install Ollama from https://ollama.com/download")
    return False


def _start_ollama_daemon() -> bool:
    if _ollama_daemon_up():
        return True
    if not shutil.which("ollama"):
        return False
    _banner("Starting the Ollama daemon (ollama serve)")
    try:
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"  Could not start the daemon automatically: {e}")
        return False
    for _ in range(20):
        if _ollama_daemon_up():
            return True
        time.sleep(1)
    return _ollama_daemon_up()


def ensure_ollama(args) -> int:
    """Install Ollama, start its daemon, and pull the RAM-appropriate model. This is a
    required setup step; if it can't complete (no network / unsupported host), the app
    still runs on the deterministic template fallback, so setup is not hard-failed."""
    if os.getenv("TOOLS_SKIP_OLLAMA") or getattr(args, "skip_ollama", False):
        print("  Skipping Ollama setup (--skip-ollama / TOOLS_SKIP_OLLAMA). "
              "The app will use the deterministic fallback until a daemon is available.")
        return 0
    _banner("Local LLM (Ollama) — required for full response drafting")
    ram = total_ram_gb()
    model = OLLAMA_DEFAULT_MODEL if ram >= RAM_FOR_DEFAULT_GB else OLLAMA_FALLBACK_MODEL
    print(f"  Detected RAM      : {ram:.1f} GB" if ram else "  Detected RAM      : unknown")
    print(f"  Disk (model)      : ~5 GB for {OLLAMA_DEFAULT_MODEL} (~2 GB for {OLLAMA_FALLBACK_MODEL})")
    print(f"  Selected model    : {model}")
    if ram and ram < RAM_MIN_GB:
        print(f"  ⚠ {ram:.1f} GB is below the recommended {RAM_MIN_GB:.0f} GB; generation may be slow "
              "(the deterministic fallback always remains available).")
    if not _install_ollama():
        print("  ⚠ Could not install Ollama automatically. Install from https://ollama.com/download, "
              "then re-run `python tools.py setup`.")
        return 1
    if not _start_ollama_daemon():
        print("  ⚠ Ollama is installed but the daemon isn't reachable. Start it with `ollama serve`.")
        return 1
    if not any(model in m for m in _ollama_models()):
        _banner(f"Pulling {model} (one-time download — can take several minutes)")
        if _run(["ollama", "pull", model]) != 0:
            print(f"  ⚠ Could not pull {model}. Run `ollama pull {model}` manually.")
            return 1
    print(f"  ✔ Ollama ready — {model} reachable at http://localhost:11434")
    return 0


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_setup(_args) -> int:
    py = ensure_venv()
    _banner("Upgrading pip")
    _run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    _banner("Installing dependencies (this can take a few minutes - PyTorch is large)")
    req = str(ROOT / "requirements.txt")
    rc = _run([str(py), "-m", "pip", "install", "-r", req])
    if rc != 0:
        # Known issue: chromadb cannot uninstall a system-managed PyYAML.
        _banner("Retrying with --ignore-installed PyYAML (chromadb/PyYAML workaround)")
        rc = _run([str(py), "-m", "pip", "install", "--ignore-installed", "PyYAML", "-r", req])
    if rc != 0:
        return rc
    rc_ollama = ensure_ollama(_args)
    print("\n✔ Setup complete. Next: python tools.py run"
          + ("" if rc_ollama == 0 else "\n  (Ollama needs attention — see above; the app still runs on the "
             "deterministic fallback until it's ready.)"))
    return 0


def cmd_validate(_args) -> int:
    py = ensure_venv()
    _banner("Validating the synthetic data pipeline")
    return _run([str(py), "-m", "evals.validation"])


def cmd_run(args) -> int:
    py = venv_python()
    if not py.exists():
        print("No .venv found - running setup first.")
        if cmd_setup(args) != 0:
            return 1
        py = venv_python()
    # Best-effort: bring the local LLM daemon up so the app drafts with Ollama instead of
    # the deterministic fallback. Skipped with --skip-ollama / TOOLS_SKIP_OLLAMA; never fatal.
    if not (os.getenv("TOOLS_SKIP_OLLAMA") or getattr(args, "skip_ollama", False)):
        if shutil.which("ollama") and not _ollama_daemon_up():
            _start_ollama_daemon()
    _banner("Launching Streamlit app  (open http://localhost:8501 ; Ctrl+C to stop)")
    extra = args.extra or []
    return _run([str(py), "-m", "streamlit", "run", str(ROOT / "app" / "main.py"), *extra])


def cmd_doctor(_args) -> int:
    _banner("Environment status")
    ram = total_ram_gb()
    rec = OLLAMA_DEFAULT_MODEL if ram >= RAM_FOR_DEFAULT_GB else OLLAMA_FALLBACK_MODEL
    print(f"  OS                : {platform.platform()}")
    print(f"  System Python     : {sys.version.split()[0]} ({sys.executable})")
    print(f"  Total RAM         : {ram:.1f} GB" if ram else "  Total RAM         : unknown")
    print(f"  CPU cores         : {os.cpu_count()}")
    print(f"  Recommended model : {rec}  (>= {RAM_FOR_DEFAULT_GB:.0f} GB -> {OLLAMA_DEFAULT_MODEL}, "
          f"else {OLLAMA_FALLBACK_MODEL})")
    print(f"  Ollama binary     : {'found' if shutil.which('ollama') else 'NOT installed'}")
    print(f"  Ollama daemon     : {'reachable' if _ollama_daemon_up() else 'not running'}"
          + (f"  · models: {', '.join(_ollama_models()) or 'none pulled'}" if _ollama_daemon_up() else ""))
    py = venv_python()
    print(f"  .venv present     : {py.exists()}  ({VENV_DIR})")
    if not py.exists():
        print("  -> run 'python tools.py setup' to create it (also installs Ollama + the model).")
        return 0
    probe = (
        "import importlib.util as u\n"
        "mods=['streamlit','duckdb','networkx','chromadb','langgraph','faker','sentence_transformers','ollama']\n"
        "print('  packages          :')\n"
        "[print('     ', m, 'OK' if u.find_spec(m) else 'MISSING') for m in mods]\n"
    )
    # run quietly (no command echo) so the probe source isn't printed
    return subprocess.call([str(py), "-c", probe], cwd=ROOT)


def cmd_all(args) -> int:
    if cmd_setup(args) != 0:
        return 1
    if cmd_validate(args) != 0:
        return 1
    return cmd_run(args)


COMMANDS = {"setup": cmd_setup, "validate": cmd_validate,
            "run": cmd_run, "doctor": cmd_doctor, "all": cmd_all}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set up and run the Omnichannel Retail Analytics Assistant.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python tools.py            # setup + validate + launch\n"
               "  python tools.py setup\n  python tools.py run --server.port 8502")
    parser.add_argument("command", nargs="?", default="all", choices=list(COMMANDS),
                        help="Task to run (default: all).")
    parser.add_argument("--skip-ollama", action="store_true",
                        help="Skip installing/pulling Ollama during setup (CI/headless); the app "
                             "then uses the deterministic fallback. Same as TOOLS_SKIP_OLLAMA=1.")
    parser.add_argument("extra", nargs=argparse.REMAINDER,
                        help="Extra args passed through to Streamlit (for 'run').")
    args = parser.parse_args()
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
