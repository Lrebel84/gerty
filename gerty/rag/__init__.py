"""RAG knowledge base for Gerty."""

from gerty.rag.store import (
    get_status,
    index_folder,
    is_indexed,
    query,
)

__all__ = ["index_folder", "query", "is_indexed", "get_status"]
