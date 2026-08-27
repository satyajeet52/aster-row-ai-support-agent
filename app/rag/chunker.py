"""
Splits knowledge-base documents into heading-aware chunks.
Each chunk carries the parent document's metadata plus the specific
heading under which it appears, enabling metadata-aware retrieval.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any

from app.rag.loader import Document

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A single retrievable text segment with its associated metadata."""
    text: str
    filename: str
    heading: str
    document_id: str = ""
    status: str = "unknown"
    audience: str = "unknown"
    policy_authority: str = "unknown"
    effective_date: str = ""
    supersedes: str = ""
    superseded_by: str = ""
    customer_answering: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


# Regex that matches markdown headings (##, ###, etc.).
_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


# Splits a document body into sections by heading, creating one chunk
# per heading section. Each chunk inherits the document-level metadata.
def chunk_document(doc: Document) -> list[Chunk]:
    meta = doc.metadata
    base_kwargs = {
        "filename": doc.filename,
        "document_id": meta.get("document_id", ""),
        "status": meta.get("status", "unknown"),
        "audience": meta.get("audience", "unknown"),
        "policy_authority": meta.get("policy_authority", "unknown"),
        "effective_date": str(meta.get("effective_date", "")),
        "supersedes": str(meta.get("supersedes", "")),
        "superseded_by": str(meta.get("superseded_by", "")),
        "customer_answering": meta.get("customer_answering", True),
        "metadata": meta,
    }

    body = doc.body.strip()
    if not body:
        return []

    # Find all heading positions.
    headings = list(_HEADING_RE.finditer(body))

    chunks: list[Chunk] = []

    if not headings:
        # No headings — treat the entire body as one chunk.
        title = meta.get("title", doc.filename)
        chunks.append(Chunk(text=body, heading=title, **base_kwargs))
        return chunks

    # If there's text before the first heading, capture it.
    if headings[0].start() > 0:
        preamble = body[: headings[0].start()].strip()
        if preamble:
            title = meta.get("title", doc.filename)
            chunks.append(Chunk(text=preamble, heading=title, **base_kwargs))

    # Create one chunk per heading section.
    for i, match in enumerate(headings):
        heading_text = match.group(2).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(body)
        section_text = body[start:end].strip()

        if section_text:
            # Include heading in the chunk text for better semantic matching.
            full_text = f"{heading_text}\n\n{section_text}"
            chunks.append(Chunk(text=full_text, heading=heading_text, **base_kwargs))

    logger.info("Chunked %s into %d chunks", doc.filename, len(chunks))
    return chunks


# Chunks all documents from the knowledge base into a flat list
# of retrieval-ready Chunk objects.
def chunk_all(documents: list[Document]) -> list[Chunk]:
    all_chunks: list[Chunk] = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc))
    logger.info("Total chunks created: %d", len(all_chunks))
    return all_chunks
