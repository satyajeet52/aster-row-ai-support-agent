"""
Embedding backends for the vector retrieval channel.

Two backends, chosen explicitly by the EMBEDDINGS environment variable:

  minilm  sentence-transformers all-MiniLM-L6-v2 (384-d), runs locally, ~80 MB
          download on first use. The default and the better retriever.
  hash    a deterministic hashing vectorizer built on numpy alone. No download,
          no network, byte-identical vectors on every machine. This is what lets
          the test suite and CI run with nothing installed.

There is deliberately NO automatic fallback from minilm to hash. A silent
downgrade would mean two machines reporting different retrieval quality under
the same command, which is the class of bug this repository is trying not to
have. If minilm cannot load, load_backend raises and tells you your two options.
"""

import hashlib
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Dimensionality of the hashing vectorizer. 384 matches MiniLM so that an index
# built with either backend has the same shape and the sidecar records which.
HASH_DIM = 384

_minilm_model = None


# Loads (once) and returns the sentence-transformers model, raising a message
# that names the two supported ways forward if the package or weights are absent.
def _get_minilm(model_name: str = "all-MiniLM-L6-v2"):
    global _minilm_model
    if _minilm_model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:  # pragma: no cover - depends on the machine
            raise RuntimeError(
                "EMBEDDINGS=minilm needs sentence-transformers, which is not importable "
                f"({exc}). Either 'pip install sentence-transformers' or run with "
                "EMBEDDINGS=hash to use the deterministic numpy-only backend."
            ) from exc
        logger.info("Loading embedding model %s", model_name)
        _minilm_model = SentenceTransformer(model_name)
    return _minilm_model


# Maps one token to a signed position in the vector. The sign comes from a
# separate hash bit so that unrelated tokens colliding on an index tend to
# cancel rather than reinforce, which keeps cosine similarity meaningful.
def _token_slot(token: str) -> tuple[int, float]:
    digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "big")
    return value % HASH_DIM, (1.0 if (value >> 63) & 1 else -1.0)


# Turns text into a unit-length hashed bag-of-words vector. Deterministic across
# machines and Python runs because blake2b is stable, unlike hash().
def hash_embed(text: str) -> np.ndarray:
    from app.rag.bm25 import tokenize

    vector = np.zeros(HASH_DIM, dtype=np.float32)
    tokens = tokenize(text)
    for token in tokens:
        slot, sign = _token_slot(token)
        vector[slot] += sign
        # Character trigrams give the vector some tolerance for morphology
        # ("dishwasher" vs "dishwashers") that a pure bag of words lacks.
        padded = f"^{token}$"
        for i in range(len(padded) - 2):
            slot, sign = _token_slot(padded[i : i + 3])
            vector[slot] += 0.35 * sign
    norm = float(np.linalg.norm(vector))
    if norm > 0.0:
        vector /= norm
    return vector


class EmbeddingBackend:
    """
    A named, callable embedding function.

    Wrapping the two backends in one object means the retriever, the index
    builder and the trace all refer to the same `name`, so a stored index can
    never be silently queried with vectors from the other backend.
    """

    def __init__(self, name: str, dim: int, encode_fn):
        self.name = name
        self.dim = dim
        self._encode = encode_fn

    # Embeds a list of texts into a (n, dim) float32 matrix of unit vectors.
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        matrix = self._encode(texts)
        matrix = np.asarray(matrix, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        return matrix / norms

    # Embeds a single query string into a 1-D unit vector.
    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_texts([text])[0]


# Returns the requested backend by name, raising on an unknown name rather than
# guessing. Called by both the index builder and the retriever.
def load_backend(name: str, model_name: str = "all-MiniLM-L6-v2") -> EmbeddingBackend:
    name = (name or "").strip().lower()

    if name == "hash":
        return EmbeddingBackend(
            "hash", HASH_DIM, lambda texts: np.stack([hash_embed(t) for t in texts])
        )

    if name in {"minilm", "sentence-transformers", "st"}:
        model = _get_minilm(model_name)
        return EmbeddingBackend(
            "minilm",
            int(model.get_sentence_embedding_dimension()),
            lambda texts: model.encode(texts, convert_to_numpy=True, show_progress_bar=False),
        )

    raise ValueError(f"Unknown EMBEDDINGS backend {name!r}. Supported values: minilm, hash.")


_default_backend = None


def _get_default_backend():
    global _default_backend
    if _default_backend is None:
        _default_backend = load_backend("minilm")
    return _default_backend


# Embeds a list of texts into a 2D numpy array using the default backend.
def embed_texts(texts: list[str]) -> np.ndarray:
    return _get_default_backend().embed_texts(texts)


# Embeds a single query string into a 2D numpy array (1, dim) using the default backend.
def embed_query(query: str) -> np.ndarray:
    vec = _get_default_backend().embed_query(query)
    if vec.ndim == 1:
        vec = vec.reshape(1, -1)
    return vec.astype(np.float32)

