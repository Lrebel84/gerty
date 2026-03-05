"""ChromaDB vector store and indexing for RAG."""

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

logger = logging.getLogger(__name__)

from gerty.config import DATA_DIR, RAG_EMBED_MODEL, RAG_RELEVANCE_THRESHOLD
from gerty.rag.chunker import chunk_text
from gerty.rag.embedder import check_embed_ready, embed
from gerty.rag.parsers import parse_file

KNOWLEDGE_DIR = DATA_DIR / "knowledge"
RAG_DIR = DATA_DIR / "rag"
CHROMA_PATH = RAG_DIR / "chroma_db"
INDEX_FILE = RAG_DIR / "index.json"
COLLECTION_NAME = "gerty_knowledge"
MEMORY_COLLECTION_NAME = "gerty_memory"


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """ChromaDB embedding function using Ollama."""

    def __init__(self, model: str | None = None):
        self.model = model or RAG_EMBED_MODEL

    def __call__(self, input: Documents) -> Embeddings:
        if not input:
            return []
        return embed(list(input), model=self.model)


def _file_hash(path: Path) -> str:
    """Return a hash of file path + mtime for change detection."""
    stat = path.stat()
    return hashlib.sha256(f"{path}{stat.st_mtime}".encode()).hexdigest()


def _load_index() -> dict:
    """Load index metadata."""
    if not INDEX_FILE.exists():
        return {"files": {}, "last_indexed": None}
    try:
        with open(INDEX_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"files": {}, "last_indexed": None}


def _save_index(data: dict) -> None:
    """Save index metadata."""
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w") as f:
        json.dump(data, f, indent=2)


def index_folder(
    folder: Path | None = None,
    embed_model: str | None = None,
) -> dict[str, Any]:
    """Index all supported files in the knowledge folder. Returns status dict."""
    folder = folder or KNOWLEDGE_DIR
    folder = Path(folder)
    embed_model = embed_model or RAG_EMBED_MODEL
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)

    ok, err = check_embed_ready(model=embed_model)
    if not ok:
        return {"indexed": False, "error": err, "file_count": 0, "chunks_added": 0}

    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception as e:
        logger.debug("Delete collection (expected if new): %s", e)
    coll = client.create_collection(
        COLLECTION_NAME,
        embedding_function=OllamaEmbeddingFunction(model=embed_model),
    )

    files_indexed: dict[str, str] = {}
    parse_errors: list[str] = []
    all_docs: list[str] = []
    all_metas: list[dict] = []
    all_ids: list[str] = []
    doc_id = 0

    for path in sorted(folder.iterdir()):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext not in {".pdf", ".xlsx", ".xls", ".csv", ".docx", ".txt", ".md", ""}:
            continue
        try:
            for text, meta in parse_file(path):
                for chunk in chunk_text(text):
                    # ChromaDB only accepts str, int, float, bool - no None
                    m = {**meta, "file": str(path.name)}
                    clean_meta = {k: (v if v is not None else (0 if k == "page" else "")) for k, v in m.items()}
                    all_docs.append(chunk)
                    all_metas.append(clean_meta)
                    all_ids.append(f"{path.name}_{doc_id}")
                    doc_id += 1
            files_indexed[str(path)] = _file_hash(path)
        except Exception as e:
            parse_errors.append(f"{path.name}: {e}")

    if all_docs:
        coll.add(ids=all_ids, documents=all_docs, metadatas=all_metas)

    from datetime import datetime

    index_data = {"files": files_indexed, "last_indexed": datetime.utcnow().isoformat() + "Z"}
    _save_index(index_data)

    result: dict[str, Any] = {
        "indexed": True,
        "file_count": len(files_indexed),
        "chunks_added": len(all_docs),
        "last_indexed": index_data["last_indexed"],
    }
    if parse_errors:
        result["parse_errors"] = parse_errors
    return result


def query(
    text: str,
    top_k: int = 5,
    embed_model: str | None = None,
    relevance_threshold: float | None = None,
) -> list[tuple[str, dict]]:
    """Query both knowledge and memory collections. Returns merged list of (chunk_text, metadata).
    Chunks with distance above relevance_threshold are filtered out."""
    if not CHROMA_PATH.exists():
        return []
    embed_model = embed_model or RAG_EMBED_MODEL
    relevance_threshold = relevance_threshold if relevance_threshold is not None else RAG_RELEVANCE_THRESHOLD
    try:
        import chromadb

        # Embed once, query both collections with same embedding (avoids 2x Ollama calls)
        query_embedding = embed([text], model=embed_model)
        if not query_embedding:
            return []

        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        ef = OllamaEmbeddingFunction(model=embed_model)
        chunks: list[tuple[str, dict]] = []
        seen: set[str] = set()

        # Query knowledge collection with pre-computed embedding
        try:
            coll = client.get_collection(COLLECTION_NAME, embedding_function=ef)
            n = coll.count()
            if n > 0:
                k_docs = min(top_k, n)
                results = coll.query(query_embeddings=query_embedding, n_results=k_docs)
                if results and results.get("documents"):
                    docs = results["documents"][0]
                    metas = results.get("metadatas", [[]])[0] or []
                    dists = results.get("distances", [[]])[0] or []
                    for i, doc in enumerate(docs):
                        if doc and doc not in seen:
                            d = dists[i] if i < len(dists) else 0
                            if d <= relevance_threshold:
                                seen.add(doc)
                                meta = metas[i] if i < len(metas) else {}
                                chunks.append((doc, meta))
        except Exception as e:
            logger.debug("Knowledge collection query failed: %s", e)

        # Query memory collection with same embedding
        try:
            coll = client.get_collection(MEMORY_COLLECTION_NAME, embedding_function=ef)
            n = coll.count()
            if n > 0:
                k_mem = min(top_k, n)
                results = coll.query(query_embeddings=query_embedding, n_results=k_mem)
                if results and results.get("documents"):
                    docs = results["documents"][0]
                    metas = results.get("metadatas", [[]])[0] or []
                    dists = results.get("distances", [[]])[0] or []
                    for i, doc in enumerate(docs):
                        if doc and doc not in seen:
                            d = dists[i] if i < len(dists) else 0
                            if d <= relevance_threshold:
                                seen.add(doc)
                                meta = metas[i] if i < len(metas) else {}
                                chunks.append((doc, meta))
        except Exception as e:
            logger.debug("Memory collection query failed: %s", e)

        return chunks
    except Exception as e:
        logger.debug("RAG query failed: %s", e)
        return []


def add_memory_facts(facts: list[str], embed_model: str | None = None) -> int:
    """Add extracted user facts to the memory collection. Incremental, no rebuild. Returns count added."""
    if not facts:
        return 0
    facts = [f.strip() for f in facts if f and f.strip()]
    if not facts:
        return 0
    embed_model = embed_model or RAG_EMBED_MODEL
    try:
        import chromadb
        from datetime import datetime

        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        try:
            coll = client.get_collection(
                MEMORY_COLLECTION_NAME,
                embedding_function=OllamaEmbeddingFunction(model=embed_model),
            )
        except Exception as e:
            logger.debug("Memory collection get failed, creating: %s", e)
            coll = client.create_collection(
                MEMORY_COLLECTION_NAME,
                embedding_function=OllamaEmbeddingFunction(model=embed_model),
            )
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        ids = [f"memory_{ts}_{i}" for i in range(len(facts))]
        metas = [{"source": "memory", "file": "user_facts"} for _ in facts]
        coll.add(ids=ids, documents=facts, metadatas=metas)
        return len(facts)
    except Exception as e:
        logger.warning("add_memory_facts failed: %s", e)
        return 0


def is_indexed() -> bool:
    """Check if RAG has indexed documents or memory to query."""
    if INDEX_FILE.exists():
        data = _load_index()
        if data.get("files"):
            return True
    if CHROMA_PATH.exists():
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            coll = client.get_collection(
                MEMORY_COLLECTION_NAME,
                embedding_function=OllamaEmbeddingFunction(model=RAG_EMBED_MODEL),
            )
            if coll.count() > 0:
                return True
        except Exception as e:
            logger.debug("is_indexed memory check failed: %s", e)
    return False


def get_status() -> dict[str, Any]:
    """Return RAG status for API."""
    data = _load_index()
    memory_count = 0
    if CHROMA_PATH.exists():
        try:
            import chromadb

            client = chromadb.PersistentClient(path=str(CHROMA_PATH))
            coll = client.get_collection(
                MEMORY_COLLECTION_NAME,
                embedding_function=OllamaEmbeddingFunction(model=RAG_EMBED_MODEL),
            )
            memory_count = coll.count()
        except Exception as e:
            logger.debug("get_status memory count failed: %s", e)
    return {
        "indexed": bool(data.get("files")),
        "file_count": len(data.get("files", {})),
        "last_indexed": data.get("last_indexed"),
        "knowledge_path": str(KNOWLEDGE_DIR),
        "memory_count": memory_count,
    }
