"""
Governed catalog loader (Plan sections 7.1, 7.2).

Loads the split YAML catalog (metrics / tables / drivers / business_rules /
guardrails / examples + a versions manifest), computes a per-file content_hash,
and exposes the sync metadata used by the retrieval and graph layers to detect
drift and reject stale context. YAML is the authoritative source of truth.
"""
from __future__ import annotations

import functools
import hashlib
import pathlib

import yaml

CATALOG_DIR = pathlib.Path(__file__).resolve().parent.parent / "catalog"
SECTION_FILES = ["metrics", "tables", "drivers", "business_rules", "guardrails", "examples"]


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


@functools.lru_cache(maxsize=1)
def load_catalog() -> dict:
    """Merge all section files into one dict with per-file content hashes."""
    manifest = yaml.safe_load((CATALOG_DIR / "versions.yaml").read_text("utf-8"))
    cat: dict = {
        "catalog_version": manifest["catalog_version"],
        "last_updated": manifest["last_updated"],
        "approved_for_mvp": manifest["approved_for_mvp"],
        "_hashes": {},
    }
    for sec in SECTION_FILES:
        text = (CATALOG_DIR / f"{sec}.yaml").read_text("utf-8")
        data = yaml.safe_load(text)
        cat["_hashes"][f"{sec}.yaml"] = _hash(text)
        # lift the section payload keys to the top level (metrics, tables, ...)
        for k, v in data.items():
            if k == "section_id":
                continue
            cat[k] = v
    return cat


def version() -> str:
    return load_catalog()["catalog_version"]


def content_hash() -> str:
    """A single combined hash across all section files."""
    hashes = load_catalog()["_hashes"]
    return _hash("|".join(f"{k}:{v}" for k, v in sorted(hashes.items())))


def file_hashes() -> dict:
    return dict(load_catalog()["_hashes"])


def get_metric(name: str) -> dict | None:
    return load_catalog().get("metrics", {}).get(name)


def get_driver(name: str) -> dict | None:
    return load_catalog().get("drivers", {}).get(name)


def approved_tables() -> set[str]:
    return set(load_catalog().get("tables", {}).keys())


def sql_template(name: str) -> str | None:
    tmpl = load_catalog().get("sql_templates", {}).get(name)
    return tmpl.get("sql") if tmpl else None


def _hash_for_section(section: str) -> str:
    return load_catalog()["_hashes"].get(f"{section}.yaml", "")


def chunks() -> list[dict]:
    """
    Semantic chunks for ChromaDB (Plan section 8): one chunk per metric / table /
    driver / business rule / SQL template / example question, each tagged with the
    governance metadata used by the sync/version gate (Plan section 7.2).
    """
    cat = load_catalog()
    v = version()
    out: list[dict] = []

    def add(source_type, section, name, content, domain=None, owner=None, table=None,
            metric=None, freshness=None):
        out.append({
            "id": f"{source_type}:{name}",
            "source_type": source_type, "source_file": f"{section}.yaml",
            "section_id": section, "name": name, "metric_name": metric or (name if source_type == "metric" else None),
            "domain": domain, "table_name": table, "owner": owner,
            "freshness_level": freshness, "version": v,
            "last_updated": cat["last_updated"], "content_hash": _hash_for_section(section),
            "approved_for_mvp": True, "content": content,
        })

    for name, m in cat.get("metrics", {}).items():
        add("metric", "metrics", name, f"{m.get('label')}: {m.get('definition','').strip()}",
            domain=m.get("domain"), owner=m.get("owner"), metric=name,
            freshness=m.get("freshness_level"))
    for name, t in cat.get("tables", {}).items():
        add("table", "tables", name, f"{name} ({t.get('grain')}): {t.get('approved_use','')}",
            owner=t.get("owner"), table=name, freshness=t.get("freshness"))
    for name, d in cat.get("drivers", {}).items():
        add("driver", "drivers", name, f"{d.get('label')}: {d.get('hypothesis','')}",
            domain=d.get("domain"), owner=d.get("owner"))
    for name, r in cat.get("rules", {}).items():
        add("business_rule", "business_rules", name, r.get("description", ""))
    for name, tm in cat.get("sql_templates", {}).items():
        add("sql_template", "examples", name, tm.get("purpose", ""))
    for i, ex in enumerate(cat.get("example_questions", [])):
        add("example", "examples", f"example_{i}", ex.get("question", ""))
    return out
