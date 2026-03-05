"""Text chunking for RAG."""

CHUNK_SIZE = 2000
CHUNK_OVERLAP = 100


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks, preserving paragraph boundaries where possible."""
    if not text or not text.strip():
        return []
    text = text.strip()
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:].strip())
            break
        # Try to break at paragraph or sentence boundary
        chunk = text[start:end]
        last_para = chunk.rfind("\n\n")
        last_sent = max(
            chunk.rfind(". "),
            chunk.rfind("! "),
            chunk.rfind("? "),
        )
        break_at = max(last_para, last_sent)
        if break_at > chunk_size // 2:
            end = start + break_at + 1
            chunk = text[start:end]
        else:
            chunk = text[start:end]
        chunks.append(chunk.strip())
        start = end - overlap
        if start < 0:
            start = end
    return [c for c in chunks if c]
