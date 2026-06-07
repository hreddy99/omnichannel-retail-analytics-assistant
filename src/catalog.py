"""
Governed catalog loader (Plan section 6).

Loads the YAML semantic catalog - the authoritative source of truth - and
exposes a content_hash + version so downstream layers (ChromaDB chunks,
NetworkX graph) can detect drift and refuse stale context.
"""
from __future__ import annotations

import functools
import hashlib
import pathlib

import yaml

CATALOG_PATH = pathlib.Path(__file__).resolve().parent.parent / "catalog" / "catalog.yaml"


@functools.lru_cache(maxsize=1)
def load_catalog() -> dict:
    text = CATALOG_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    data["_content_hash"] = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return data


def version() -> str:
    return load_catalog().get("catalog_version", "unknown")


def content_hash() -> str:
    return load_catalog()["_content_hash"]


def get_metric(name: str) -> dict | None:
    return load_catalog().get("metrics", {}).get(name)


def get_driver(name: str) -> dict | None:
    return load_catalog().get("drivers", {}).get(name)


def approved_tables() -> set[str]:
    return set(load_catalog().get("tables", {}).keys())


def chunks() -> list[dict]:
    """
    Simulate the ChromaDB chunking step (Plan section 7): one semantic chunk
    per metric / table / driver, each tagged with governance metadata so the
    retrieval layer can validate version + content_hash before use.
    """
    cat = load_catalog()
    out: list[dict] = []
    v, h = version(), content_hash()
    for name, m in cat.get("metrics", {}).items():
        out.append({"source_type": "metric", "name": name, "domain": m.get("domain"),
                    "owner": m.get("owner"), "content": m.get("definition", "").strip(),
                    "version": v, "content_hash": h, "approved_for_mvp": True})
    for name, t in cat.get("tables", {}).items():
        out.append({"source_type": "table", "name": name, "domain": None,
                    "owner": t.get("owner"), "content": f"{name} ({t.get('grain')})",
                    "version": v, "content_hash": h, "approved_for_mvp": True})
    for name, d in cat.get("drivers", {}).items():
        out.append({"source_type": "driver", "name": name, "domain": d.get("domain"),
                    "owner": d.get("owner"), "content": d.get("hypothesis", ""),
                    "version": v, "content_hash": h, "approved_for_mvp": True})
    return out
