# RAG Knowledge Base & Long-Term Memory

Gerty can search your documents and remember facts you tell it. Both use the same ChromaDB vector store and embedding model.

---

## Documents (Knowledge Base)

### Setup

1. Drop PDF, Excel, Word, or text files into `data/knowledge/`
2. Open Settings → Knowledge base → **Index now**
3. Enable **RAG** in Settings (required for the tool to run)
4. Pull embedding model: `ollama pull nomic-embed-text`

### Usage

Say or type phrases like:

- "check my docs for X"
- "search my files for Y"
- "what do my documents say about Z"

The RAG tool retrieves relevant chunks from your indexed files and passes them to the LLM. **On-demand only** – no automatic injection into every message, so chat stays fast.

### Supported Formats

PDF, Excel (.xlsx, .xls, .csv), Word (.docx), plain text (.txt, .md)

### Storage

- **Index metadata:** `data/rag/index.json`
- **Vectors:** `data/rag/chroma_db/` (ChromaDB)
- **Collection:** `gerty_knowledge`

---

## Long-Term Memory

### What It Does

When you save a chat (close the window or start a new chat), Gerty extracts **facts** you stated about yourself and stores them in a separate ChromaDB collection. Examples: name, job, family, preferences, likes, dislikes.

### When Extraction Runs

- **Trigger:** Chat is saved (2+ user messages)
- **Condition:** `memory_enabled` is True in Settings (default)
- **Deduplication:** Only runs when chat content has changed since last extract

### How Facts Are Extracted

The LLM is prompted to extract only facts the user asserted as true (family, friends, likes, work, preferences, etc.). It excludes questions, requests, hypotheticals, and things the user didn't state as fact. Output is a JSON array of strings.

### How Memory Is Used

When you say "check my docs for X" or "search my files for Y", the RAG tool queries **both**:

1. **Documents** – chunks from indexed files in `data/knowledge/`
2. **Memory** – extracted facts from past conversations

Results are merged and passed to the LLM. So "what do my files say about my job?" can return both document chunks and remembered facts like "User is a tattoo artist".

### Settings

- **Long-term memory** – Toggle in Settings → Knowledge base. When off, no facts are extracted or stored.
- **Embedding model** – Same as documents (`nomic-embed-text` default). Memory uses `rag_embed_model` from Settings.

### Storage

- **Collection:** `gerty_memory` (in `data/rag/chroma_db/`)
- **Metadata:** `source: "memory"`, `file: "user_facts"`
- **IDs:** `memory_{timestamp}_{index}`

### CLI Test

```bash
python3 -m gerty.rag
```

Runs end-to-end check: index, add a test fact, query.
