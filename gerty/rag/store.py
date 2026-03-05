"""ChromaDB vector store and indexing for RAG."""

import hashlib
import json
from pathlib import Path
from typing import Any

from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

from gerty.config import DATA_DIR
from gerty.rag.chunker import chunk_text
from gerty.rag.embedder import check_embed_ready, embed
from gerty.rag.parsers import parse_file

KNOWLEDGE_DIR = DATA_DIR / "knowledge"
RAG_DIR = DATA_DIR / "rag"
CHROMA_PATH = RAG_DIR / "chroma_db"
INDEX_FILE = RAG_DIR / "index.json"
COLLECTION_NAME = "gerty_knowledge"


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """ChromaDB embedding function using Ollama."""

    def __init__(self, model: str = "nomic-embed-text"):
        self.model = model

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
    embed_model: str = "nomic-embed-text",
) -> dict[str, Any]:
    """Index all supported files in the knowledge folder. Returns status dict."""
    folder = folder or KNOWLEDGE_DIR
    folder = Path(folder)
    RAG_DIR.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)

    ok, err = check_embed_ready(model=embed_model)
    if not ok:
        return {"indexed": False, "error": err, "file_count": 0, "chunks_added": 0}

    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
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


def query(text: str, top_k: int = 5, embed_model: str = "nomic-embed-text") -> list[tuple[str, dict]]:
    """Query the vector store. Returns list of (chunk_text, metadata)."""
    if not CHROMA_PATH.exists():
        return []
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        coll = client.get_collection(
            COLLECTION_NAME,
            embedding_function=OllamaEmbeddingFunction(model=embed_model),
        )
        n = coll.count()
        if n == 0:
            return []
        results = coll.query(query_texts=[text], n_results=min(top_k, n))
        if not results or not results.get("documents"):
            return []
        chunks = []
        docs = results["documents"][0]
        metas = results.get("metadatas", [[]])[0] or []
        for i, doc in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            chunks.append((doc, meta))
        return chunks
    except Exception:
        return []


def is_indexed() -> bool:
    """Check if RAG has indexed documents."""
    if not INDEX_FILE.exists():
        return False
    data = _load_index()
    return bool(data.get("files"))


def get_status() -> dict[str, Any]:
    """Return RAG status for API."""
    data = _load_index()
    return {
        "indexed": bool(data.get("files")),
        "file_count": len(data.get("files", {})),
        "last_indexed": data.get("last_indexed"),
        "knowledge_path": str(KNOWLEDGE_DIR),
    }
