"""Make the repository root importable so tests can import the top-level
capability packages (skills, workflows, data, evals, app, agents)."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
