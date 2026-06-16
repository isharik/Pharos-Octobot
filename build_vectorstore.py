"""
build_vectorstore.py
--------------------
Builds the ChromaDB vector store from crawled docs.

Uses HuggingFace sentence-transformers embeddings —
MUST match exactly what octobot.py uses or retrieval breaks.

How to run:
    python build_vectorstore.py

Expected output:
    Loading documents from 'raw_docs'...
    Loaded 161 documents
    Splitting into chunks...
    Created XXX chunks
    Generating embeddings (this may take several minutes)...
    Vector store built! XXX chunks in 'chroma_db/'
"""

import os
import glob
import shutil
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

load_dotenv()

RAW_DOCS_DIR    = "raw_docs"
CHROMA_DB_DIR   = "chroma_db"
COLLECTION_NAME = "pharos_docs"
CHUNK_SIZE      = 1000
CHUNK_OVERLAP   = 150

# ── MUST match octobot.py exactly ──────────────────────────────
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def load_documents():
    print(f"Loading documents from '{RAW_DOCS_DIR}'...")
    txt_files = glob.glob(os.path.join(RAW_DOCS_DIR, "*.txt"))
    txt_files = [f for f in txt_files if "_index" not in f]

    if not txt_files:
        print(f"No .txt files found in '{RAW_DOCS_DIR}'.")
        print("Run crawl_docs.py first.")
        exit(1)

    documents = []
    for filepath in txt_files:
        try:
            loader = TextLoader(filepath, encoding="utf-8")
            docs   = loader.load()

            source_url = "unknown"
            title      = filepath
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("SOURCE_URL:"):
                        source_url = line.replace("SOURCE_URL:", "").strip()
                    elif line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("="):
                        break

            for doc in docs:
                doc.metadata["source"]   = source_url
                doc.metadata["title"]    = title
                doc.metadata["filename"] = os.path.basename(filepath)

            documents.extend(docs)
        except Exception as e:
            print(f"Could not load {filepath}: {e}")

    print(f"Loaded {len(documents)} documents")
    return documents


def split_documents(documents):
    print(f"\nSplitting into chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks from {len(documents)} documents")
    return chunks


def build_vectorstore(chunks):
    print(f"\nGenerating embeddings using: {EMBEDDING_MODEL}")
    print("This may take several minutes for large doc sets...\n")

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL
    )

    if os.path.exists(CHROMA_DB_DIR):
        print(f"Removing old vector store at '{CHROMA_DB_DIR}'...")
        shutil.rmtree(CHROMA_DB_DIR)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DB_DIR,
    )

    count = vectorstore._collection.count()
    print(f"\nVector store built! {count} chunks stored in '{CHROMA_DB_DIR}/'")
    return vectorstore


if __name__ == "__main__":
    documents   = load_documents()
    chunks      = split_documents(documents)
    vectorstore = build_vectorstore(chunks)
    print("\nDone! Run: streamlit run app.py")