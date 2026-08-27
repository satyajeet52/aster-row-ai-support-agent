"""
Okapi BM25 over the knowledge-base chunks, in pure Python.

This exists because lexical exactness is what embeddings blur. "Germany",
"lifetime", "dishwasher", "TrailPlus" and "gift card" are the terms that decide
which document is correct, and BM25 rewards them appearing *in the document*
rather than relying on a hand-written rule about what the user typed. It is the
honest replacement for a keyword-to-filename boost table.

No dependency: the corpus is ~60 chunks, so a dict of postings is plenty.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field

# Word tokenizer that keeps digits and intra-word hyphens/apostrophes together
# so "45-calendar-day", "ORD-1007" and "don't" survive as useful units.
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)*")

# Very small stopword list. Deliberately short: dropping too much hurts a corpus
# this size, and BM25's IDF already discounts common words.
_STOPWORDS = frozenset(
    """
    a an the and or of to in for on at by is are was were be been being do does did
    it its this that these those with as from i you my me we our your they them
    """.split()
)


# Lowercases and splits text into comparable terms, dropping stopwords.
# Shared by indexing and querying so both sides see identical tokens.
def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class BM25Index:
    """
    An in-memory BM25 index over a fixed list of documents.

    Holds term frequencies per document, document lengths, and document
    frequencies. Built once at query time from the chunk texts; rebuilding is
    cheap enough at this corpus size that persisting it would add risk without
    saving measurable time.
    """

    k1: float = 1.5
    b: float = 0.75
    doc_terms: list[Counter] = field(default_factory=list)
    doc_lengths: list[int] = field(default_factory=list)
    doc_freq: Counter = field(default_factory=Counter)
    avg_doc_length: float = 0.0

    # Builds the index from raw document texts, in the caller's order, so that
    # score() results can be zipped straight back onto the chunk list.
    @classmethod
    def build(cls, texts: list[str], k1: float = 1.5, b: float = 0.75) -> "BM25Index":
        index = cls(k1=k1, b=b)
        for text in texts:
            terms = Counter(tokenize(text))
            index.doc_terms.append(terms)
            index.doc_lengths.append(sum(terms.values()))
            for term in terms:
                index.doc_freq[term] += 1
        n = len(index.doc_lengths)
        index.avg_doc_length = (sum(index.doc_lengths) / n) if n else 0.0
        return index

    # Returns the BM25 score of every indexed document against the query, in
    # index order. Unmatched documents score 0.0 rather than being omitted, so
    # the caller can fuse this channel positionally with the vector channel.
    def score(self, query: str) -> list[float]:
        n = len(self.doc_lengths)
        if n == 0:
            return []

        query_terms = tokenize(query)
        scores = [0.0] * n

        for term in set(query_terms):
            df = self.doc_freq.get(term, 0)
            if df == 0:
                continue
            # Standard BM25 IDF with the +0.5 smoothing, floored at zero so a
            # term present in every document cannot push a score negative.
            idf = max(0.0, math.log(1.0 + (n - df + 0.5) / (df + 0.5)))
            for i in range(n):
                tf = self.doc_terms[i].get(term, 0)
                if tf == 0:
                    continue
                length_norm = 1.0 - self.b + self.b * (
                    self.doc_lengths[i] / self.avg_doc_length if self.avg_doc_length else 1.0
                )
                scores[i] += idf * (tf * (self.k1 + 1.0)) / (tf + self.k1 * length_norm)

        return scores
