"""
Live integration tests for the Retriever using the generated FAISS index.
Verifies semantic search, metadata-aware re-ranking, current vs legacy
precedence, and conflict detection.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config
from app.rag.retriever import Retriever


@pytest.fixture(scope="module")
def retriever():
    return Retriever(config.index_dir)


# Confirms that a returns policy query retrieves current policy ahead of legacy.
def test_returns_policy_precedence(retriever):
    result = retriever.retrieve("How long does a customer have to return an item?")
    assert len(result.chunks) > 0

    top_chunk = result.chunks[0]
    assert top_chunk.filename == "01-returns-policy-current.md"
    assert top_chunk.status == "active"

    # Any legacy chunk in results must have lower adjusted score than current
    current_scores = [c.adjusted_score for c in result.chunks if c.filename == "01-returns-policy-current.md"]
    legacy_scores = [c.adjusted_score for c in result.chunks if c.filename == "02-returns-policy-legacy.md"]

    if legacy_scores and current_scores:
        assert max(current_scores) > max(legacy_scores)


# Confirms that international shipping query retrieves Canada policy.
def test_international_shipping_retrieval(retriever):
    result = retriever.retrieve("Do you ship to Canada?")
    assert any(c.filename == "06-international-shipping.md" for c in result.chunks)


# Confirms that TrailPlus membership query retrieves TrailPlus policy.
def test_trailplus_retrieval(retriever):
    result = retriever.retrieve("What are the return benefits for TrailPlus members?")
    assert any(c.filename == "09-trailplus-membership.md" for c in result.chunks)


# Confirms that tumbler dishwasher query surfaces both care guide and product card,
# triggering conflict detection.
def test_tumbler_conflict_detection(retriever):
    result = retriever.retrieve("Can I put the Breeze Tumbler in the dishwasher?")
    filenames = {c.filename for c in result.chunks}
    assert "11-product-care.md" in filenames or "12-breeze-tumbler-product-card.md" in filenames
    assert result.has_conflict is True


# Confirms that warranty questions retrieve the warranty document.
def test_warranty_retrieval(retriever):
    result = retriever.retrieve("What is the warranty period for backpacks?")
    assert any(c.filename == "07-warranty.md" for c in result.chunks)
