"""Run RAG tests from CLI: python -m gerty.rag"""
import sys

from gerty.rag.embedder import check_embed_ready
from gerty.rag.store import KNOWLEDGE_DIR, get_status, index_folder, is_indexed, query


def main():
    print("=== RAG Knowledge Base Test ===\n")
    print(f"Knowledge folder: {KNOWLEDGE_DIR}")
    print(f"Exists: {KNOWLEDGE_DIR.exists()}")

    if KNOWLEDGE_DIR.exists():
        files = [p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_file()]
        print(f"Files in folder: {files or '(none)'}\n")
    else:
        print("Folder does not exist.\n")
        return 1

    print("1. Checking Ollama + embedding model...")
    ok, err = check_embed_ready()
    if not ok:
        print(f"   FAIL: {err}\n")
        return 1
    print("   OK\n")

    print("2. Indexing...")
    try:
        result = index_folder()
        if result.get("indexed"):
            print(f"   OK - {result.get('file_count', 0)} files, {result.get('chunks_added', 0)} chunks")
            if result.get("parse_errors"):
                print(f"   Parse errors: {result['parse_errors']}")
        else:
            print(f"   FAIL: {result.get('error', 'Unknown')}")
            return 1
    except Exception as e:
        print(f"   FAIL: {e}")
        return 1

    print(f"\n3. Indexed: {is_indexed()}")
    status = get_status()
    print(f"   Status: {status}\n")

    print("4. Test query: 'tell me about my family'")
    chunks = query("tell me about my family", top_k=3)
    print(f"   Retrieved {len(chunks)} chunks")
    for i, (text, meta) in enumerate(chunks[:2], 1):
        print(f"   Chunk {i} ({meta.get('file', '?')}): {text[:80]}...")

    print("\n=== Done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
