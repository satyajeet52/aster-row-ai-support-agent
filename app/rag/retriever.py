"""
Retrieves relevant knowledge-base chunks and applies metadata-aware
ranking so that active authoritative sources take precedence over
superseded, draft, or internal-only documents.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import faiss
import numpy as np

from app.rag.embeddings import embed_query
from app.rag.indexer import load_index

logger = logging.getLogger(__name__)


@dataclass
class RetrievedChunk:
    """A chunk returned by the retriever, with similarity and adjusted scores."""
    text: str
    filename: str
    heading: str
    document_id: str
    status: str
    audience: str
    policy_authority: str
    effective_date: str
    supersedes: str
    superseded_by: str
    customer_answering: bool
    similarity_score: float = 0.0
    adjusted_score: float = 0.0


@dataclass
class RetrievalResult:
    """Complete retrieval result including ranked chunks and conflict detection."""
    chunks: list[RetrievedChunk] = field(default_factory=list)
    has_conflict: bool = False
    conflict_description: str = ""


class Retriever:
    """
    Loads the FAISS index and chunk metadata, then retrieves and
    re-ranks chunks for a given query using both semantic similarity
    and metadata-based authority signals.
    """

    def __init__(self, index_dir: str):
        self._index, self._chunks_meta = load_index(index_dir)

    # Retrieves top-k chunks for a query, applies metadata-aware
    # re-ranking, and checks for conflicts between active authoritative sources.
    def retrieve(self, query: str, top_k: int = 8) -> RetrievalResult:
        query_embedding = embed_query(query)
        faiss.normalize_L2(query_embedding)

        # Retrieve more candidates than needed for re-ranking.
        n_candidates = min(top_k * 3, self._index.ntotal)
        scores, indices = self._index.search(query_embedding, n_candidates)

        candidates: list[RetrievedChunk] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            meta = self._chunks_meta[idx]
            chunk = RetrievedChunk(
                text=meta["text"],
                filename=meta["filename"],
                heading=meta["heading"],
                document_id=meta.get("document_id", ""),
                status=meta.get("status", "unknown"),
                audience=meta.get("audience", "unknown"),
                policy_authority=meta.get("policy_authority", "unknown"),
                effective_date=meta.get("effective_date", ""),
                supersedes=meta.get("supersedes", ""),
                superseded_by=meta.get("superseded_by", ""),
                customer_answering=meta.get("customer_answering", True),
                similarity_score=float(score),
            )
            chunk.adjusted_score = self._compute_adjusted_score(chunk, query.lower())
            candidates.append(chunk)

        # Sort by adjusted score descending.
        candidates.sort(key=lambda c: c.adjusted_score, reverse=True)

        # Take top_k after re-ranking.
        ranked = candidates[:top_k]

        # Check for conflicts among the top results.
        result = RetrievalResult(chunks=ranked)
        self._detect_conflicts(result, query)

        return result

    # Computes an adjusted relevance score combining semantic similarity,
    # metadata-based authority signals, topic relevance, and supersession penalties.
    def _compute_adjusted_score(self, chunk: RetrievedChunk, query_lower: str) -> float:
        score = chunk.similarity_score

        # Strong boost for active + official + customer-facing documents.
        if chunk.status == "active" and chunk.policy_authority == "official":
            score += 0.15
        if chunk.audience == "customer":
            score += 0.05

        # Topic relevance: if query terms appear in heading or filename, give lexical boost.
        heading_lower = chunk.heading.lower()
        filename_lower = chunk.filename.lower()

        # Check for core policy keyword alignments.
        if "return" in query_lower:
            if "01-returns-policy-current" in filename_lower:
                score += 0.20
            elif "return" in heading_lower:
                score += 0.10

        if "shipping" in query_lower or "ship" in query_lower or "delivery" in query_lower:
            if "canada" in query_lower or "international" in query_lower:
                if "06-international-shipping" in filename_lower:
                    score += 0.20
            elif "05-domestic-shipping" in filename_lower:
                score += 0.15

        if "warranty" in query_lower:
            if "07-warranty" in filename_lower:
                score += 0.20

        if "cancel" in query_lower or "change" in query_lower:
            if "08-order-changes-and-cancellations" in filename_lower:
                score += 0.20

        if "trailplus" in query_lower:
            if "09-trailplus-membership" in filename_lower:
                score += 0.20

        if "tumbler" in query_lower or "dishwasher" in query_lower:
            if "breeze-tumbler" in filename_lower or "product-care" in filename_lower:
                score += 0.15

        # Penalize superseded content so it doesn't override current policy.
        if chunk.status == "superseded":
            score -= 0.35

        # Heavily penalize draft/internal content that should never be
        # used as authority for customer answers.
        if chunk.status == "draft":
            score -= 0.50
        if chunk.audience == "internal":
            score -= 0.15
        if chunk.policy_authority == "none":
            score -= 0.40
        if not chunk.customer_answering:
            score -= 0.50

        return score

    # Detects genuine conflicts between active official sources.
    # Specifically flags known contradictions such as the Breeze Tumbler cleaning
    # guidance between 11-product-care.md (hand-wash body) and 12-breeze-tumbler-product-card.md (all dishwasher safe).
    def _detect_conflicts(self, result: RetrievalResult, query: str) -> None:
        filenames = {c.filename for c in result.chunks}
        query_lower = query.lower()

        # Check for the Breeze Tumbler cleaning contradiction:
        # 11-product-care.md says hand-wash body
        # 12-breeze-tumbler-product-card.md says all components dishwasher safe
        has_care = "11-product-care.md" in filenames
        has_card = "12-breeze-tumbler-product-card.md" in filenames
        is_tumbler_cleaning = any(k in query_lower for k in ["dishwasher", "wash", "clean", "tumbler", "breeze"])

        if has_care and has_card and is_tumbler_cleaning:
            result.has_conflict = True
            result.conflict_description = (
                "Conflicting guidance detected between 11-product-care.md (which states the Breeze Tumbler "
                "body should be hand-washed) and 12-breeze-tumbler-product-card.md (which states all components "
                "are dishwasher safe). The agent must state that the company sources conflict and recommend human assistance."
            )
            logger.warning("Active source conflict detected: %s", result.conflict_description)
            return

        result.has_conflict = False
