"""
test_retrieval.py
-----------------
Phase 4: Test that our ChromaDB retrieval is working correctly.

How to run:
    python test_retrieval.py
"""

import os

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
CHROMA_DB_DIR = "chroma_db"
COLLECTION_NAME = "pharos_docs"
TOP_K = 4

TEST_QUESTIONS = [
    "What is Pharos Network?",
    "What are Special Processing Networks (SPNs)?",
    "How does consensus work in Pharos?",
]


def load_vectorstore():
    """Load the existing ChromaDB vector store from disk."""

    if not os.path.exists(CHROMA_DB_DIR):
        print(f"❌ Vector store not found at '{CHROMA_DB_DIR}'.")
        print("Please run build_vectorstore.py first.")
        exit(1)

    # SAME embedding model used during indexing
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    vectorstore = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_DIR,
    )

    count = vectorstore._collection.count()

    print(f"✅ Loaded vector store: {count} chunks available\n")

    return vectorstore


def test_retrieval(vectorstore, question):
    """Retrieve top matching chunks."""

    print(f'🔍 Testing retrieval for: "{question}"')
    print("─" * 60)

    results = vectorstore.similarity_search_with_score(
        question,
        k=TOP_K
    )

    if not results:
        print("⚠️ No results found.")
        return

    for i, (doc, score) in enumerate(results, start=1):

        source = doc.metadata.get("source", "unknown")
        title = doc.metadata.get("title", "unknown")

        preview = (
            doc.page_content[:200]
            .replace("\n", " ")
            .strip()
        )

        print(f"\nResult {i}")
        print(f"Source: {source}")
        print(f"Title : {title}")
        print(f"Score : {score:.4f}")
        print(f"Preview: {preview}...")

    print()


if __name__ == "__main__":

    vectorstore = load_vectorstore()

    for question in TEST_QUESTIONS:
        test_retrieval(vectorstore, question)
        print("=" * 60)

    print("\n✅ Retrieval test complete!")
    print("Next step: Run python test_octobot.py")
