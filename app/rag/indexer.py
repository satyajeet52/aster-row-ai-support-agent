"""
Builds and persists a FAISS index from knowledge-base chunks.
Stores both the vector index and the chunk metadata as a sidecar
JSON file so the retriever can reconstruct Chunk objects at query time.
"""

import os
import json
import logging
import numpy as np
import faiss

from app.rag.chunker import Chunk
from app.rag.embeddings import embed_texts

logger = logging.getLogger(__name__)

INDEX_FILENAME = "faiss.index"
METADATA_FILENAME = "chunks_metadata.json"


# Serializes a Chunk to a JSON-safe dictionary, excluding the raw text
# embedding but keeping all metadata needed for retrieval ranking.
def _chunk_to_dict(chunk: Chunk) -> dict:
    return {
        "text": chunk.text,
        "filename": chunk.filename,
        "heading": chunk.heading,
        "document_id": chunk.document_id,
        "status": chunk.status,
        "audience": chunk.audience,
        "policy_authority": chunk.policy_authority,
        "effective_date": chunk.effective_date,
        "supersedes": chunk.supersedes,
        "superseded_by": chunk.superseded_by,
        "customer_answering": chunk.customer_answering,
    }


# Builds a FAISS inner-product index from the given chunks and
# saves both the index and chunk metadata to the output directory.
def build_index(chunks: list[Chunk], output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)

    texts = [c.text for c in chunks]
    logger.info("Generating embeddings for %d chunks...", len(texts))
    embeddings = embed_texts(texts)

    # Normalize for cosine similarity via inner product.
    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    index_path = os.path.join(output_dir, INDEX_FILENAME)
    faiss.write_index(index, index_path)
    logger.info("FAISS index saved to %s (%d vectors, dim=%d)", index_path, index.ntotal, dim)

    meta_path = os.path.join(output_dir, METADATA_FILENAME)
    chunk_dicts = [_chunk_to_dict(c) for c in chunks]
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(chunk_dicts, f, indent=2)
    logger.info("Chunk metadata saved to %s", meta_path)


# Loads a previously built FAISS index and its chunk metadata.
# Returns the FAISS index and a list of chunk metadata dicts.
def load_index(index_dir: str) -> tuple[faiss.Index, list[dict]]:
    index_path = os.path.join(index_dir, INDEX_FILENAME)
    meta_path = os.path.join(index_dir, METADATA_FILENAME)

    if not os.path.exists(index_path) or not os.path.exists(meta_path):
        raise FileNotFoundError(
            f"Index not found in {index_dir}. Run 'python scripts/build_index.py' first."
        )

    index = faiss.read_index(index_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        chunks_meta = json.load(f)

    logger.info("Loaded FAISS index with %d vectors from %s", index.ntotal, index_dir)
    return index, chunks_meta
