#!/usr/bin/env python3
"""
Project task runner for the Omnichannel Retail Analytics Assistant.

A single, dependency-free entry point (uses only the Python standard library) so
you can set up and run everything from a command prompt:

    python tools.py setup       # create .venv and install all dependencies
    python tools.py validate    # run the synthetic-data validation checks
    python tools.py html        # generate the standalone project_plan.html
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
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
IS_WINDOWS = os.name == "nt"


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
    print("\n✔ Setup complete. Next: python tools.py run")
    return 0


def cmd_validate(_args) -> int:
    py = ensure_venv()
    _banner("Validating synthetic data pipeline (Plan section 14.4)")
    return _run([str(py), "-m", "evals.validation"])


def cmd_html(_args) -> int:
    py = ensure_venv()
    _banner("Generating interactive project_plan.html")
    return _run([str(py), str(ROOT / "build_html.py")])


def cmd_run(args) -> int:
    py = venv_python()
    if not py.exists():
        print("No .venv found - running setup first.")
        if cmd_setup(args) != 0:
            return 1
        py = venv_python()
    _banner("Launching Streamlit app  (open http://localhost:8501 ; Ctrl+C to stop)")
    extra = args.extra or []
    return _run([str(py), "-m", "streamlit", "run", str(ROOT / "app" / "main.py"), *extra])


def cmd_doctor(_args) -> int:
    _banner("Environment status")
    print(f"  OS                : {platform.platform()}")
    print(f"  System Python     : {sys.version.split()[0]} ({sys.executable})")
    py = venv_python()
    print(f"  .venv present     : {py.exists()}  ({VENV_DIR})")
    if not py.exists():
        print("  -> run 'python tools.py setup' to create it.")
        return 0
    probe = (
        "import importlib.util as u\n"
        "mods=['streamlit','duckdb','networkx','chromadb','langgraph','faker','sentence_transformers','ollama']\n"
        "print('  packages          :')\n"
        "[print('     ', m, 'OK' if u.find_spec(m) else 'MISSING') for m in mods]\n"
        "ok=False\n"
        "try:\n import ollama; ollama.Client().list(); ok=True\n"
        "except Exception: ok=False\n"
        "print('  ollama daemon     :', 'reachable' if ok else 'not running (optional; deterministic fallback used)')\n"
    )
    # run quietly (no command echo) so the probe source isn't printed
    return subprocess.call([str(py), "-c", probe], cwd=ROOT)


def cmd_all(args) -> int:
    if cmd_setup(args) != 0:
        return 1
    if cmd_validate(args) != 0:
        return 1
    return cmd_run(args)


COMMANDS = {"setup": cmd_setup, "validate": cmd_validate, "html": cmd_html,
            "run": cmd_run, "doctor": cmd_doctor, "all": cmd_all}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set up and run the Omnichannel Retail Analytics Assistant.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n  python tools.py            # setup + validate + launch\n"
               "  python tools.py setup\n  python tools.py run --server.port 8502")
    parser.add_argument("command", nargs="?", default="all", choices=list(COMMANDS),
                        help="Task to run (default: all).")
    parser.add_argument("extra", nargs=argparse.REMAINDER,
                        help="Extra args passed through to Streamlit (for 'run').")
    args = parser.parse_args()
    return COMMANDS[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
