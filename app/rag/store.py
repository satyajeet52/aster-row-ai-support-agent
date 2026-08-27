"""
Vector store: a numpy array on disk plus a JSON sidecar of chunk metadata.

The corpus is 14 documents, roughly 60 chunks. A dot product over 60 unit
vectors is instantaneous and exactly as accurate as an approximate-nearest-
neighbour index, so FAISS would add an install failure mode and a binary
artifact in exchange for nothing measurable. The sidecar is plain JSON, which
means a reviewer can read the index by eye — worth more here than throughput.

The sidecar records which embedding backend produced the vectors, and load()
refuses to hand back an index built by a different backend than the caller is
querying with. That mismatch is silent and ruins retrieval, so it is checked.
"""

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np

from app.rag.chunker import Chunk

VECTORS_FILENAME = "vectors.npy"
SIDECAR_FILENAME = "chunks.json"


@dataclass
class StoredIndex:
    """A loaded index: aligned vectors and chunk records, plus provenance."""

    vectors: np.ndarray
    chunks: list[Chunk] = field(default_factory=list)
    backend: str = ""
    built_at: str = ""


# Flattens a Chunk into a JSON-safe dict. The full front matter is kept under
# "metadata" so that adding a front-matter field later needs no schema change.
def chunk_to_dict(chunk: Chunk) -> dict[str, Any]:
    record = asdict(chunk)
    record["metadata"] = {k: _jsonable(v) for k, v in (chunk.metadata or {}).items()}
    return record


# Coerces YAML scalars (dates in particular) into JSON-safe values.
def _jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return str(value)


# Rebuilds a Chunk from a sidecar record, tolerating records written by an older
# version of the schema by falling back to the dataclass defaults.
def chunk_from_dict(record: dict[str, Any]) -> Chunk:
    fields = {f for f in Chunk.__dataclass_fields__}
    return Chunk(**{k: v for k, v in record.items() if k in fields})


# Writes vectors and sidecar to output_dir, creating it if needed. Vectors and
# chunks must be in the same order; that alignment is the store's only invariant.
def save(chunks: list[Chunk], vectors: np.ndarray, output_dir: str, backend: str) -> None:
    if len(chunks) != vectors.shape[0]:
        raise ValueError(
            f"index would be corrupt: {len(chunks)} chunks but {vectors.shape[0]} vectors"
        )
    os.makedirs(output_dir, exist_ok=True)
    np.save(os.path.join(output_dir, VECTORS_FILENAME), vectors.astype(np.float32))

    from datetime import datetime, timezone

    sidecar = {
        "embedding_backend": backend,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunk_count": len(chunks),
        "chunks": [chunk_to_dict(c) for c in chunks],
    }
    with open(os.path.join(output_dir, SIDECAR_FILENAME), "w", encoding="utf-8") as f:
        json.dump(sidecar, f, indent=2, ensure_ascii=False)


# Loads an index and verifies it was built with the expected backend. Raises a
# message naming the rebuild command rather than returning a degraded index.
def load(index_dir: str, expected_backend: str | None = None) -> StoredIndex:
    vectors_path = os.path.join(index_dir, VECTORS_FILENAME)
    sidecar_path = os.path.join(index_dir, SIDECAR_FILENAME)

    if not (os.path.exists(vectors_path) and os.path.exists(sidecar_path)):
        raise FileNotFoundError(
            f"No index in {index_dir!r}. Build it with: python scripts/build_index.py"
        )

    vectors = np.load(vectors_path)
    with open(sidecar_path, "r", encoding="utf-8") as f:
        sidecar = json.load(f)

    backend = sidecar.get("embedding_backend", "")
    if expected_backend and backend and backend != expected_backend:
        raise RuntimeError(
            f"Index in {index_dir!r} was built with embeddings={backend!r} but this process "
            f"is using embeddings={expected_backend!r}. Rebuild with: "
            f"EMBEDDINGS={expected_backend} python scripts/build_index.py"
        )

    chunks = [chunk_from_dict(r) for r in sidecar.get("chunks", [])]
    if len(chunks) != vectors.shape[0]:
        raise RuntimeError(
            f"Corrupt index in {index_dir!r}: {len(chunks)} chunk records for "
            f"{vectors.shape[0]} vectors. Rebuild with: python scripts/build_index.py"
        )

    return StoredIndex(
        vectors=vectors,
        chunks=chunks,
        backend=backend,
        built_at=sidecar.get("built_at", ""),
    )


# Cosine similarity of one unit query vector against all stored unit vectors.
# Both sides are normalized at creation, so the dot product *is* the cosine.
def cosine_scores(query_vector: np.ndarray, vectors: np.ndarray) -> list[float]:
    if vectors.size == 0:
        return []
    return [float(s) for s in vectors @ query_vector]
