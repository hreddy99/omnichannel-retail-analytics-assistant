"""Retrieval governance: the certified metric is retrievable and every governed
chunk carries the metadata the version/sync gate needs (Checkpoint 6)."""
from skills import catalog_skill as catalog


def test_certified_conversion_definition_is_a_chunk():
    chunks = catalog.chunks()
    metric_chunks = [c for c in chunks if c.get("source_type") == "metric"]
    assert any("digital_conversion_rate" in (c.get("name") or "") for c in metric_chunks)


def test_every_chunk_has_source_file_and_content_hash():
    chunks = catalog.chunks()
    assert chunks
    for c in chunks:
        assert c.get("source_file"), f"chunk {c.get('id')} missing source_file"
        assert c.get("content_hash"), f"chunk {c.get('id')} missing content_hash"


def test_chunk_hashes_match_current_yaml():
    """A chunk built from the live YAML must match the current file hash (no drift)."""
    chunks = catalog.chunks()
    current = catalog.file_hashes()
    fresh = [c for c in chunks if current.get(c["source_file"]) == c["content_hash"]]
    assert len(fresh) == len(chunks)
