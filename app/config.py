"""
Application configuration loaded from environment variables.

One Config dataclass is the single place that reads os.environ, so every other
module can be unit-tested by constructing a Config directly instead of poking
at the environment. Nothing here has a default that silently changes behaviour:
the LLM provider is deliberately empty when unset so the factory can fail loudly
rather than quietly substituting something that fakes answers.
"""

import os
from dataclasses import dataclass, field

try:  # python-dotenv is convenient but must not be required to import the app.
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - exercised only when dotenv is absent
    pass


# Reads a boolean-ish environment variable ("1", "true", "yes") into a real bool
# so callers never have to remember which spelling the env file used.
def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    """Central configuration for the application, sourced from the environment."""

    # LLM provider selection. Deliberately empty when unset: app.llm.factory
    # raises with instructions instead of falling back to a canned responder.
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "").strip().lower())

    # Mistral settings.
    mistral_api_key: str = field(default_factory=lambda: os.getenv("MISTRAL_API_KEY", "").strip())
    mistral_model: str = field(
        default_factory=lambda: os.getenv("MISTRAL_MODEL", "mistral-small-latest").strip()
    )

    # Ollama settings.
    ollama_base_url: str = field(
        default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    )
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.1:8b").strip())

    # Embedding backend: "minilm" (sentence-transformers) or "hash" (numpy only).
    # There is no automatic fallback between them; see app/rag/embeddings.py.
    embeddings_backend: str = field(
        default_factory=lambda: os.getenv("EMBEDDINGS", "minilm").strip().lower()
    )

    # Observability.
    debug: bool = field(default_factory=lambda: _env_flag("DEBUG"))
    trace_file: str = field(default_factory=lambda: os.getenv("TRACE_FILE", "").strip())

    # Ablation switch used to produce the baseline evaluation run. When true the
    # agent keeps the privacy sanitizer but drops precedence filtering, conflict
    # detection, tool gating, and grounded abstention. See README "Baseline".
    baseline_mode: bool = field(default_factory=lambda: _env_flag("ASTER_BASELINE"))

    # Paths, relative to the repository root.
    knowledge_base_dir: str = field(
        default_factory=lambda: os.getenv(
            "KNOWLEDGE_BASE_DIR",
            "assignment_files/knowledge-base" if os.path.isdir("assignment_files/knowledge-base") else "knowledge-base",
        )
    )
    orders_file: str = field(
        default_factory=lambda: os.getenv(
            "ORDERS_FILE",
            "assignment_files/data/orders.json" if os.path.isfile("assignment_files/data/orders.json") else "data/orders.json",
        )
    )
    index_dir: str = "indexes"

    # Retrieval settings. top_k is the number of chunks that survive precedence
    # filtering and reach the prompt; candidate_k is the pre-filter width.
    embedding_model: str = "all-MiniLM-L6-v2"
    top_k_retrieval: int = 6
    candidate_k: int = 24
    bm25_weight: float = 0.5
    vector_weight: float = 0.5

    # Server settings for the optional FastAPI view.
    host: str = field(default_factory=lambda: os.getenv("HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))


# Process-wide default config. Tests construct their own Config() instead of
# mutating this one, so there is no shared mutable state to leak between cases.
config = Config()
