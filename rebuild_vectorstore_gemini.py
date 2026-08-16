"""
rebuild_vectorstore_gemini.py
-----------------------------
One-off migration: rebuild the vector store using Google's Gemini embedding
API (models/gemini-embedding-001) instead of the local HuggingFace
sentence-transformers model.

Why: the local embedder pulls in torch + transformers (~1 GB), which is the
main reason the app is slow to boot and heavy on memory. Switching to the
API embedder drops that whole stack.

Source of truth: the existing `chroma_db` already stores every chunk's text
and metadata, so we re-embed those directly — no need for raw_docs/.

Output: a NEW directory `chroma_gemini/` (the old `chroma_db/` is left intact
as a backup / rollback). octobot.py + build_vectorstore.py are pointed at the
new dir + embedder.

Run:  venv/Scripts/python.exe rebuild_vectorstore_gemini.py
"""

import os
import time
import shutil
from dotenv import dotenv_values

# Load .env explicitly (find_dotenv can fail in some launch contexts).
for _k, _v in dotenv_values(".env").items():
    if _v and _k not in os.environ:
        os.environ[_k] = _v

import chromadb
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

OLD_DIR         = "chroma_db"
NEW_DIR         = "chroma_gemini"
COLLECTION_NAME = "pharos_docs"
EMBEDDING_MODEL = "models/gemini-embedding-001"
# Free-tier gemini-embedding-001 allows ~100 embeddings/min. Stay well under.
BATCH           = 15
PAUSE_BETWEEN   = 12          # seconds between batches (~75/min)
PAUSE_ON_429    = 65          # seconds to wait out a per-minute quota reset


def read_existing_chunks():
    """Pull every chunk (id + text + metadata) out of the old Chroma store.
    Reading documents/metadatas does NOT require an embedder."""
    client = chromadb.PersistentClient(path=OLD_DIR)
    col = client.get_collection(COLLECTION_NAME)
    got = col.get(include=["documents", "metadatas"])
    ids, docs, metas = got["ids"], got["documents"], got["metadatas"]
    out = []
    for cid, text, meta in zip(ids, docs, metas):
        if text:
            out.append((cid, Document(page_content=text, metadata=meta or {})))
    print(f"Recovered {len(out)} chunks from '{OLD_DIR}'.")
    return out


def build(items):
    """Resumable, rate-limit-friendly build into NEW_DIR. Re-running picks up
    where a previous (interrupted / rate-limited) run left off."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY missing — cannot embed.")

    embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=key)
    vs = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=NEW_DIR,
    )

    # Skip anything already embedded (resume support).
    try:
        done_ids = set(vs._collection.get(include=[])["ids"])
    except Exception:
        done_ids = set()
    remaining = [(cid, d) for cid, d in items if cid not in done_ids]
    print(f"Already embedded: {len(done_ids)}.  Remaining: {len(remaining)}.")

    total = len(remaining)
    for i in range(0, total, BATCH):
        batch = remaining[i:i + BATCH]
        ids = [cid for cid, _ in batch]
        docs = [d for _, d in batch]
        for attempt in range(6):
            try:
                vs.add_documents(docs, ids=ids)
                break
            except Exception as e:
                is429 = "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)
                wait = PAUSE_ON_429 if is429 else 5 * (attempt + 1)
                print(f"  {type(e).__name__} — wait {wait}s ({str(e)[:70]})")
                time.sleep(wait)
        else:
            print(f"Stopped at {i}. Re-run the script to resume.")
            return vs._collection.count()
        print(f"  embedded {min(i+BATCH, total)}/{total} (this run)")
        time.sleep(PAUSE_BETWEEN)

    count = vs._collection.count()
    print(f"\nDone. New vector store '{NEW_DIR}/' has {count} chunks.")
    return count


if __name__ == "__main__":
    items = read_existing_chunks()
    if not items:
        raise SystemExit("No chunks recovered — aborting.")
    build(items)
