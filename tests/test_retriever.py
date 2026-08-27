"""
Tests for the RAG document loader and chunker.
Validates metadata extraction, chunking, and document properties.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config
from app.rag.loader import load_knowledge_base, parse_document
from app.rag.chunker import chunk_document, chunk_all

KB_DIR = config.knowledge_base_dir


@pytest.fixture
def documents():
    return load_knowledge_base(KB_DIR)


@pytest.fixture
def all_chunks(documents):
    return chunk_all(documents)


# --- Document Loading ---

# Confirms all 14 knowledge-base documents are loaded.
def test_loads_all_documents(documents):
    assert len(documents) == 14


# Confirms the current returns policy has correct metadata.
def test_current_returns_metadata(documents):
    doc = next(d for d in documents if d.filename == "01-returns-policy-current.md")
    assert doc.metadata["status"] == "active"
    assert doc.metadata["policy_authority"] == "official"
    assert doc.metadata["audience"] == "customer"
    assert doc.metadata["supersedes"] == "RET-2024-01"


# Confirms the legacy returns policy is marked as superseded.
def test_legacy_returns_metadata(documents):
    doc = next(d for d in documents if d.filename == "02-returns-policy-legacy.md")
    assert doc.metadata["status"] == "superseded"
    assert doc.metadata["superseded_by"] == "RET-2026-01"


# Confirms the internal migration notes are marked as draft/internal.
def test_internal_notes_metadata(documents):
    doc = next(d for d in documents if d.filename == "14-internal-content-migration-notes.md")
    assert doc.metadata["status"] == "draft"
    assert doc.metadata["audience"] == "internal"
    assert doc.metadata["policy_authority"] == "none"
    assert doc.metadata["customer_answering"] is False


# Confirms the escalation document is marked as internal audience.
def test_escalation_audience(documents):
    doc = next(d for d in documents if d.filename == "13-support-escalation.md")
    assert doc.metadata["audience"] == "internal"
    assert doc.metadata["policy_authority"] == "official"


# --- Chunking ---

# Confirms that chunking produces a reasonable number of chunks.
def test_chunks_created(all_chunks):
    assert len(all_chunks) > 20  # Should be well over 20 chunks


# Confirms each chunk has required metadata fields.
def test_chunk_metadata_preserved(all_chunks):
    for chunk in all_chunks:
        assert chunk.filename
        assert chunk.heading
        assert chunk.status in ("active", "superseded", "draft", "unknown")


# Confirms chunks from the current returns policy are marked active.
def test_current_returns_chunks_active(all_chunks):
    returns_chunks = [c for c in all_chunks if c.filename == "01-returns-policy-current.md"]
    assert len(returns_chunks) > 0
    for chunk in returns_chunks:
        assert chunk.status == "active"
        assert chunk.policy_authority == "official"


# Confirms chunks from the legacy returns policy are marked superseded.
def test_legacy_returns_chunks_superseded(all_chunks):
    legacy_chunks = [c for c in all_chunks if c.filename == "02-returns-policy-legacy.md"]
    assert len(legacy_chunks) > 0
    for chunk in legacy_chunks:
        assert chunk.status == "superseded"


# Confirms chunks from draft documents carry the draft status.
def test_draft_chunks_flagged(all_chunks):
    draft_chunks = [c for c in all_chunks if c.filename == "14-internal-content-migration-notes.md"]
    assert len(draft_chunks) > 0
    for chunk in draft_chunks:
        assert chunk.status == "draft"
        assert chunk.audience == "internal"
        assert chunk.customer_answering is False


# Confirms the Breeze Tumbler cleaning info conflict exists in chunks
# (product care says hand-wash, product card says dishwasher safe).
def test_tumbler_conflict_in_chunks(all_chunks):
    care_chunks = [c for c in all_chunks if c.filename == "11-product-care.md"
                   and "tumbler" in c.text.lower()]
    card_chunks = [c for c in all_chunks if c.filename == "12-breeze-tumbler-product-card.md"
                   and ("dishwasher" in c.text.lower() or "cleaning" in c.heading.lower())]
    # Both sources should produce relevant chunks about cleaning.
    assert len(care_chunks) > 0
    assert len(card_chunks) > 0
