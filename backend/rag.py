"""
RAG (Retrieval-Augmented Generation) engine for AquaCapital.

Index lifecycle
---------------
- PDFs in database/ are chunked (word-based, with overlap) and embedded via
  Azure OpenAI.
- Chunks are stored in a ChromaDB PersistentClient on disk so they survive
  restarts without re-embedding.
- A manifest file (database/rag_manifest.json) records a fingerprint of the
  current PDFs.  build_index() is a no-op when the fingerprint matches,
  making every retrieve() call fast after the first run.

Scaling path
------------
Swap chromadb.PersistentClient for chromadb.HttpClient("http://your-server")
and everything else stays the same.
"""

import hashlib
import json
import os

import chromadb
from pypdf import PdfReader

from .llm_client import EMBEDDING_DEPLOYMENT, get_client

# ── Paths ──────────────────────────────────────────────────────────────────────
_DB_DIR      = os.path.join(os.path.dirname(__file__), "..", "database")
_CHROMA_DIR  = os.path.join(_DB_DIR, "chroma_db")
_MANIFEST    = os.path.join(_DB_DIR, "rag_manifest.json")
_COLLECTION  = "quote_documents"

# ── Chunking parameters ────────────────────────────────────────────────────────
_CHUNK_WORDS   = 400   # target words per chunk
_OVERLAP_WORDS = 60    # word overlap between consecutive chunks
_EMBED_BATCH   = 16    # texts per Azure OpenAI embedding request


# ── Internal helpers ───────────────────────────────────────────────────────────

def _pdf_paths() -> list[str]:
    return sorted(
        os.path.join(_DB_DIR, f)
        for f in os.listdir(_DB_DIR)
        if f.lower().endswith(".pdf")
    )


def _fingerprint() -> str:
    """MD5 of (name, mtime, size) for every PDF — changes when files are added/replaced."""
    parts = []
    for p in _pdf_paths():
        s = os.stat(p)
        parts.append(f"{os.path.basename(p)}:{s.st_mtime:.0f}:{s.st_size}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()


def _chunk(text: str) -> list[str]:
    words = text.split()
    chunks, start = [], 0
    while start < len(words):
        end = min(start + _CHUNK_WORDS, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += _CHUNK_WORDS - _OVERLAP_WORDS
    return [c for c in chunks if c.strip()]


def _embed(texts: list[str]) -> list[list[float]]:
    client = get_client()
    embeddings = []
    for i in range(0, len(texts), _EMBED_BATCH):
        batch = texts[i : i + _EMBED_BATCH]
        resp = client.embeddings.create(model=EMBEDDING_DEPLOYMENT, input=batch)
        embeddings.extend(item.embedding for item in resp.data)
    return embeddings


def _chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=_CHROMA_DIR)


# ── Public API ─────────────────────────────────────────────────────────────────

def build_index(force: bool = False) -> dict:
    """
    Build (or rebuild) the vector index from all PDFs in database/.

    Returns a dict with build stats: {"status", "chunks", "pdfs"}.
    A no-op returns {"status": "fresh", ...} immediately.
    """
    current_fp = _fingerprint()

    if not force and os.path.exists(_MANIFEST):
        with open(_MANIFEST, encoding="utf-8") as f:
            stored = json.load(f)
        if stored.get("fingerprint") == current_fp:
            return {"status": "fresh", "chunks": stored.get("chunks", 0), "pdfs": stored.get("pdfs", 0)}

    # ── Rebuild ────────────────────────────────────────────────────────────────
    client = _chroma_client()
    try:
        client.delete_collection(_COLLECTION)
    except Exception:
        pass
    col = client.create_collection(_COLLECTION, metadata={"hnsw:space": "cosine"})

    ids, docs, metas = [], [], []

    for pdf_path in _pdf_paths():
        fname = os.path.basename(pdf_path)
        # "WQ-2025-003_20251107.pdf"  →  "WQ-2025-003"
        quote_id = fname.rsplit("_", 1)[0] if "_" in fname else fname.replace(".pdf", "")

        try:
            reader = PdfReader(pdf_path)
            text = "\n".join(p.extract_text() or "" for p in reader.pages).strip()
        except Exception:
            continue

        chunks = _chunk(text)
        for i, chunk in enumerate(chunks):
            ids.append(f"{quote_id}__c{i}")
            docs.append(chunk)
            metas.append({
                "source":       fname,
                "quote_id":     quote_id,
                "chunk_index":  i,
                "total_chunks": len(chunks),
            })

    if ids:
        embeddings = _embed(docs)
        col.add(ids=ids, documents=docs, metadatas=metas, embeddings=embeddings)

    manifest = {"fingerprint": current_fp, "chunks": len(ids), "pdfs": len(_pdf_paths())}
    with open(_MANIFEST, "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    return {"status": "rebuilt", **manifest}


def retrieve(query: str, k: int = 6) -> list[dict]:
    """
    Return the k most relevant chunks for *query*.

    Each result: {"text", "source", "quote_id", "chunk_index", "score"}.
    Automatically triggers a build_index() if the index is stale or missing.
    """
    build_index()

    col = _chroma_client().get_or_create_collection(
        _COLLECTION, metadata={"hnsw:space": "cosine"}
    )
    total = col.count()
    if total == 0:
        return []

    k = min(k, total)
    q_emb = _embed([query])[0]
    results = col.query(
        query_embeddings=[q_emb],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        chunks.append({
            "text":        doc,
            "source":      meta["source"],
            "quote_id":    meta["quote_id"],
            "chunk_index": meta["chunk_index"],
            "score":       round(1.0 - float(dist), 4),  # cosine similarity
        })
    return chunks


def retrieve_by_document(query: str, top_docs: int = 3, chunks_per_doc: int = 2) -> list[dict]:
    """
    Retrieve the most relevant chunks, then return the best *chunks_per_doc*
    chunks from each of the top *top_docs* unique documents.

    Useful for find_comparable_quotes where you want document-level coverage.
    Each result: {"quote_id", "source", "excerpts": [str, ...]}.
    """
    raw = retrieve(query, k=top_docs * chunks_per_doc * 3)

    # Group by quote_id, keeping insertion order (best score first)
    seen: dict[str, dict] = {}
    for chunk in raw:
        qid = chunk["quote_id"]
        if qid not in seen:
            seen[qid] = {"quote_id": qid, "source": chunk["source"], "excerpts": [], "best_score": chunk["score"]}
        if len(seen[qid]["excerpts"]) < chunks_per_doc:
            seen[qid]["excerpts"].append(chunk["text"])

    # Sort by best score descending, keep top_docs
    docs = sorted(seen.values(), key=lambda d: d["best_score"], reverse=True)
    return docs[:top_docs]
