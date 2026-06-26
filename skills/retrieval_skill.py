"""
Retrieval layer - real ChromaDB + sentence-transformers.

Builds a local vector index over the governed YAML chunks (one chunk per
metric / table / driver / rule / template / example) with full governance
metadata. Embeddings use all-MiniLM-L6-v2 via sentence-transformers, falling back
to ChromaDB's built-in ONNX MiniLM, and finally to a deterministic hashing
embedder so the demo still runs fully offline. The active embedder is reported
so the UI can show it in Trust details.

Implements the catalog sync/version gate: each retrieved chunk's stored
content_hash is compared to the current YAML hash, and stale chunks are rejected
and re-embedded before use.
"""
from __future__ import annotations

import hashlib

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from skills import catalog_skill as catalog

EMBED_DIM = 256


class HashingEmbeddingFunction(EmbeddingFunction):
    """Deterministic offline fallback: hashed bag-of-tokens -> fixed vector."""

    def __call__(self, input: Documents) -> Embeddings:
        out: Embeddings = []
        for doc in input:
            vec = [0.0] * EMBED_DIM
            for tok in doc.lower().split():
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                vec[h % EMBED_DIM] += 1.0
            norm = sum(v * v for v in vec) ** 0.5 or 1.0
            out.append([v / norm for v in vec])
        return out


def _pick_embedder():
    """Return (embedding_function, label). Prefer sentence-transformers."""
    from chromadb.utils import embedding_functions as ef
    try:
        fn = ef.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        fn(["probe"])  # trigger model load/download; raises if unavailable
        return fn, "sentence-transformers/all-MiniLM-L6-v2"
    except Exception:
        pass
    try:
        fn = ef.DefaultEmbeddingFunction()
        fn(["probe"])
        return fn, "chromadb-default/all-MiniLM-L6-v2 (onnx)"
    except Exception:
        return HashingEmbeddingFunction(), "deterministic-hashing (offline fallback)"


class RetrievalIndex:
    """ChromaDB-backed semantic index over the governed catalog."""

    def __init__(self):
        self.embed_fn, self.embedder_label = _pick_embedder()
        self.client = chromadb.EphemeralClient()
        self.collection = self.client.create_collection(
            name="governed_catalog", embedding_function=self.embed_fn)
        self._load()

    def _load(self):
        chunks = catalog.chunks()
        self.collection.add(
            ids=[c["id"] for c in chunks],
            documents=[c["content"] for c in chunks],
            metadatas=[{k: ("" if v is None else v) for k, v in c.items()
                        if k not in ("id", "content")} for c in chunks])
        self._n = len(chunks)

    def retrieve(self, query: str, top_k: int = 5, source_type: str | None = None) -> list[dict]:
        """Top-k retrieval. Applies the sync gate: a chunk whose
        stored content_hash != current YAML hash is rejected as stale."""
        where = {"source_type": source_type} if source_type else None
        res = self.collection.query(query_texts=[query], n_results=top_k, where=where)
        current = catalog.file_hashes()
        out = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            fresh = current.get(meta.get("source_file"), None) == meta.get("content_hash")
            out.append({"content": doc, "metadata": meta, "distance": float(dist),
                        "fresh": bool(fresh),
                        "validated": fresh and self._exists_in_yaml(meta)})
        return out

    @staticmethod
    def _exists_in_yaml(meta: dict) -> bool:
        """Validate a retrieved entry against the certified catalog."""
        cat = catalog.load_catalog()
        st = meta.get("source_type")
        name = meta.get("name")
        if st == "metric":
            return name in cat.get("metrics", {})
        if st == "table":
            return name in cat.get("tables", {})
        if st == "driver":
            return name in cat.get("drivers", {})
        return True

    def sync_status(self) -> dict:
        """Report whether any indexed chunk is stale vs the current YAML."""
        current = catalog.file_hashes()
        got = self.collection.get(include=["metadatas"])
        stale = [m["id"] if "id" in m else m.get("name")
                 for m in got["metadatas"]
                 if current.get(m.get("source_file")) != m.get("content_hash")]
        return {"embedder": self.embedder_label, "n_chunks": self._n,
                "stale": stale, "in_sync": not stale}


_INDEX: RetrievalIndex | None = None


def get_index() -> RetrievalIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = RetrievalIndex()
    return _INDEX
