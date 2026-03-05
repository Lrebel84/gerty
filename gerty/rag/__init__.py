"""RAG knowledge base for Gerty."""

from gerty.rag.store import (
    add_memory_facts,
    get_status,
    index_folder,
    is_indexed,
    query,
)

__all__ = ["add_memory_facts", "index_folder", "query", "is_indexed", "get_status"]
