"""
One-time script to build the FAISS index from the knowledge base.
Run this before starting the application:
    python scripts/build_index.py
"""

import sys
import os
import logging

# Add project root to path so imports work.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import config
from app.rag.loader import load_knowledge_base
from app.rag.chunker import chunk_all
from app.rag.indexer import build_index


# Entry point: loads documents, chunks them, generates embeddings,
# and saves the FAISS index to the indexes/ directory.
def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("Loading knowledge base from %s", config.knowledge_base_dir)
    documents = load_knowledge_base(config.knowledge_base_dir)

    if not documents:
        logger.error("No documents found. Check the knowledge-base directory.")
        sys.exit(1)

    logger.info("Chunking %d documents...", len(documents))
    chunks = chunk_all(documents)

    if not chunks:
        logger.error("No chunks created. Check the document format.")
        sys.exit(1)

    logger.info("Building FAISS index with %d chunks...", len(chunks))
    build_index(chunks, config.index_dir)

    logger.info("Index built successfully in %s", config.index_dir)


if __name__ == "__main__":
    main()
