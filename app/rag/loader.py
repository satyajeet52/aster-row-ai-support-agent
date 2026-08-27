"""
Loads Markdown files from the knowledge base directory, parses YAML
front matter into structured metadata, and returns (metadata, body)
pairs for downstream chunking and indexing.
"""

import os
import re
import yaml
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Document:
    """A single knowledge-base document with parsed metadata and body text."""
    filename: str
    metadata: dict[str, Any] = field(default_factory=dict)
    body: str = ""


# Regex that matches YAML front matter delimited by --- lines.
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# Parses a single markdown file, extracting YAML front matter and the
# remaining body text. Returns a Document with both parts.
def parse_document(filepath: str) -> Document:
    filename = os.path.basename(filepath)
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    metadata: dict[str, Any] = {}
    body = content

    match = _FRONT_MATTER_RE.match(content)
    if match:
        try:
            metadata = yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError as e:
            logger.warning("Failed to parse front matter in %s: %s", filename, e)
        body = content[match.end():]

    return Document(filename=filename, metadata=metadata, body=body)


# Loads all .md files from the knowledge-base directory and returns
# a list of parsed Document objects.
def load_knowledge_base(kb_dir: str) -> list[Document]:
    documents = []
    if not os.path.isdir(kb_dir):
        logger.error("Knowledge base directory not found: %s", kb_dir)
        return documents

    for fname in sorted(os.listdir(kb_dir)):
        if fname.endswith(".md"):
            filepath = os.path.join(kb_dir, fname)
            doc = parse_document(filepath)
            logger.info(
                "Loaded %s — status=%s, authority=%s, audience=%s",
                fname,
                doc.metadata.get("status", "unknown"),
                doc.metadata.get("policy_authority", "unknown"),
                doc.metadata.get("audience", "unknown"),
            )
            documents.append(doc)

    logger.info("Loaded %d documents from %s", len(documents), kb_dir)
    return documents
