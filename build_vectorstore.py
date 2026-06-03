"""
build_vectorstore.py
--------------------
Build ChromaDB vector database from crawled Pharos docs.

Run:
python build_vectorstore.py
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

RAW_DOCS_DIR = "raw_docs"
CHROMA_DB_DIR = "chroma_db"

COLLECTION_NAME = "pharos_docs"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150


def load_documents():

    print(f"📂 Loading documents from '{RAW_DOCS_DIR}'...")

    txt_files = glob.glob(
        os.path.join(
            RAW_DOCS_DIR,
            "*.txt"
        )
    )

    txt_files = [
        f for f in txt_files
        if "_index" not in f
    ]

    if not txt_files:
        raise Exception(
            "No documents found. Run crawl_docs.py first."
        )

    docs = []

    for file in txt_files:

        loader = TextLoader(
            file,
            encoding="utf-8"
        )

        loaded = loader.load()

        docs.extend(loaded)

    # Here is where you print the debug info
    print(f"DEBUG: Loaded {len(docs)} documents from '{RAW_DOCS_DIR}'")
    for doc in docs[:3]:  # Log first three documents for inspection
        print(f" - Title: {doc.metadata.get('title')}, Source: {doc.metadata.get('source')}")


        for doc in loaded:

            source = "unknown"
            title = file

            with open(
                file,
                "r",
                encoding="utf-8"
            ) as f:

                for line in f:

                    if line.startswith(
                        "SOURCE_URL:"
                    ):
                        source = (
                            line
                            .replace(
                                "SOURCE_URL:",
                                ""
                            )
                            .strip()
                        )

                    elif line.startswith(
                        "TITLE:"
                    ):
                        title = (
                            line
                            .replace(
                                "TITLE:",
                                ""
                            )
                            .strip()
                        )

                    elif line.startswith("="):
                        break

            doc.metadata["source"] = source
            doc.metadata["title"] = title

        docs.extend(loaded)

    print(f"📄 Loaded {len(docs)} documents")
    for doc in docs[:3]:print(f" - Title: {doc.metadata.get('title')}, Source: {doc.metadata.get('source')}")

    return docs


def split_documents(documents):

    print(
        f"\n✂️ Splitting into chunks "
        f"(size={CHUNK_SIZE})"
    )

    splitter = (
        RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
    )

    chunks = (
        splitter
        .split_documents(
            documents
        )
    )

    print(
        f"📊 Created "
        f"{len(chunks)} chunks"
    )

    return chunks


def build_vectorstore(chunks):

    print(
        "\n🧠 Generating embeddings..."
    )

    embeddings = (
        HuggingFaceEmbeddings(
            model_name=(
                "sentence-transformers/"
                "all-MiniLM-L6-v2"
            )
        )
    )

    if os.path.exists(
        CHROMA_DB_DIR
    ):

        print(
            "🗑 Removing old DB..."
        )

        shutil.rmtree(
            CHROMA_DB_DIR
        )

    vectorstore = (
        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection_name=(
                COLLECTION_NAME
            ),
            persist_directory=(
                CHROMA_DB_DIR
            ),
        )
    )

    count = (
        vectorstore
        ._collection
        .count()
    )

    print(
        f"\n✅ Stored "
        f"{count} chunks"
    )

    return vectorstore


if __name__ == "__main__":

    docs = (
        load_documents()
    )

    chunks = (
        split_documents(
            docs
        )
    )

    build_vectorstore(
        chunks
    )

    print(
        "\n🎉 Done!"
    )

    print(
        "Next → python test_retrieval.py"
    )

