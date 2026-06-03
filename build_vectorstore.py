"""
build_vectorstore.py
--------------------
Phase 3: Load the crawled docs, split them into chunks,
generate embeddings using HuggingFace, and store everything in ChromaDB.

This creates a 'chroma_db' folder that acts as OctoBot's
long-term memory — it's what the chatbot searches every time
you ask a question.

How to run:
    python build_vectorstore.py

Expected output:
    📂 Loading documents from 'raw_docs'...
    📄 Loaded 25 documents
    ✂️  Splitting into chunks...
    📊 Created 312 chunks
    🧠 Generating embeddings and storing in ChromaDB...
    ✅ Vector store built! 312 chunks stored in 'chroma_db'
    🎉 Done! Next step: Run python test_retrieval.py
"""

import os
import glob
from dotenv import load_dotenv

# LangChain document loaders and splitters
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# HuggingFace embeddings (FREE)
from langchain_huggingface import HuggingFaceEmbeddings

# ChromaDB integration
from langchain_chroma import Chroma

load_dotenv()

def build_vectorstore():
    # Create embeddings using HuggingFace
    embeddings = HuggingFaceEmbeddings()

    # Load documents from the raw_docs directory
    documents = load_documents()  # This is your existing load function

    # Split documents into chunks
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(documents)

    # Connect to ChromaDB
    chroma_client = Chroma(persist_directory=CHROMA_DB_DIR)
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

    # Add each chunk and embedding to the collection
    for chunk in chunks:
        embedding = embeddings.embed_text(chunk.page_content)
        collection.add(
            embeddings=embedding,
            metadata={"source": chunk.metadata["source"]}
        )
    
    # Persist the database
    chroma_client.persist()
    print("Vector store successfully built and saved.")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
RAW_DOCS_DIR = "raw_docs"
CHROMA_DB_DIR = "chroma_db"
COLLECTION_NAME = "pharos_docs"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def load_documents():
    """Load all .txt files from the raw_docs folder."""
    print(f"📂 Loading documents from '{RAW_DOCS_DIR}'...")

    txt_files = glob.glob(os.path.join(RAW_DOCS_DIR, "*.txt"))
    txt_files = [f for f in txt_files if "_index" not in f]

    if not txt_files:
        print(f"❌ No .txt files found in '{RAW_DOCS_DIR}'.")
        print("Did you run crawl_docs.py first?")
        exit(1)

    documents = []

    for filepath in txt_files:
        try:
            loader = TextLoader(filepath, encoding="utf-8")
            docs = loader.load()

            source_url = "unknown"
            title = filepath

            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("SOURCE_URL:"):
                        source_url = line.replace("SOURCE_URL:", "").strip()
                    elif line.startswith("TITLE:"):
                        title = line.replace("TITLE:", "").strip()
                    elif line.startswith("="):
                        break

            for doc in docs:
                doc.metadata["source"] = source_url
                doc.metadata["title"] = title
                doc.metadata["filename"] = os.path.basename(filepath)

            documents.extend(docs)

        except Exception as e:
            print(f"⚠️ Could not load {filepath}: {e}")

    print(f"📄 Loaded {len(documents)} documents")
    return documents


def split_documents(documents):
    """Split documents into overlapping chunks."""

    print(
        f"\n✂️ Splitting into chunks "
        f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})..."
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_documents(documents)

    print(
        f"📊 Created {len(chunks)} chunks "
        f"from {len(documents)} documents"
    )

    return chunks


def build_vectorstore(chunks):
    """
    Generate embeddings using HuggingFace and
    store everything in ChromaDB.
    """

    print("\n🧠 Generating embeddings and storing in ChromaDB...")
    print("Using model: sentence-transformers/all-MiniLM-L6-v2")
    print("This is completely FREE and runs locally.\n")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    if os.path.exists(CHROMA_DB_DIR):
        import shutil

        print(f"🗑️ Removing old vector store at '{CHROMA_DB_DIR}'...")
        shutil.rmtree(CHROMA_DB_DIR)

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=CHROMA_DB_DIR,
    )

    count = vectorstore._collection.count()

    print(
        f"\n✅ Vector store built! "
        f"{count} chunks stored in '{CHROMA_DB_DIR}/'"
    )

    return vectorstore


if __name__ == "__main__":

    documents = load_documents()

    chunks = split_documents(documents)

    vectorstore = build_vectorstore(chunks)

    print("\n🎉 Done! Your vector store is ready.")
    print("Next step: Run python test_retrieval.py")
