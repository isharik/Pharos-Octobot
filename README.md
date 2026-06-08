🐙 OctoBot — AI Documentation & Agent Skill for Pharos

## What it does
A reusable AI Skill that answers any question about the Pharos Network
using verified documentation. Built for the Pharos AI Agent Carnival.

## Skill category
Data Fetch / Knowledge Base

## How any Agent can use this Skill
POST https://your-deployment/query
{
  "question": "What are SPNs?"
}

Returns:
{
  "answer": "SPNs (Special Processing Networks) are...",
  "sources": [{"url": "...", "title": "..."}],
  "found_in_docs": true
}

## Sources it knows about
- docs.pharos.xyz (full site)
- buildonpharos.com
- github.com/PharosNetwork
- 7 Medium deep-dive articles
- Bitget Academy

## Stack
LangChain · ChromaDB · GPT-4o mini · FastAPI · Streamlit

## Run locally
pip install -r requirements.txt
python build_vectorstore.py
uvicorn skill_api:app --port 8000




(Important : Before you try to run the app you might want to configure your api keys and chroma db properly so that no error persists , i haven't made the site public yet as its still wip , after i deploy the site and make the data locally available , you can easily test it out till then keep open sourcing)

OctoBot is a Retrieval-Augmented Generation (RAG) AI chatbot designed to answer questions strictly from the official Pharos documentation.

📚 Documentation Source: https://docs.pharos.xyz/

It ensures accurate, grounded, and hallucination-free responses by retrieving information directly from verified documents.

🚀 Features
🧠 RAG-based architecture for accurate answers
📄 Crawls and processes full Pharos documentation
✂️ Intelligent document chunking for better retrieval
🧬 Vector search using ChromaDB
🤖 OpenAI-powered response generation
🔍 Strict “no hallucination” response policy
💬 Streamlit chat interface for easy interaction
📌 Source-based answers with citations
⚙️ Tech Stack
🐍 Python 3.x
🔗 OpenAI API
🧠 LangChain (latest stable version)
🗄️ ChromaDB (vector database)
🎨 Streamlit (UI framework)
🕷️ BeautifulSoup (web scraping)
🔐 dotenv (environment variable management)
🏗️ How It Works

Video Guide : https://x.com/isharik99/status/2061857340744487276?s=20

Pharos Docs
⬇️
Web Crawler
⬇️
Text Extraction
⬇️
Chunking
⬇️
Embeddings (OpenAI)
⬇️
ChromaDB Vector Store
⬇️
Retriever System
⬇️
GPT Model
⬇️
🐙 OctoBot Response (with citations)

🧩 Project Phases
🔹 Phase 1: Setup
Virtual environment setup
Install dependencies
Configure .env file
Connect OpenAI API



🔹 Phase 2: Data Collection
Crawl full Pharos documentation
Extract and store raw text locally


🔹 Phase 3: Vector Database
Split text into chunks
Generate embeddings
Store in ChromaDB


🔹 Phase 4: Retrieval System
Build semantic search pipeline
Retrieve relevant context for queries


🔹 Phase 5: AI Engine
Integrate OpenAI with retrieval system
Ensure grounded answers only
Fallback response if no data found


🔹 Phase 6: UI
Build Streamlit chat interface
Display answers and sources


🔹 Phase 7: Enhancements
Add memory support
Improve retrieval accuracy
Add better citation handling




⚠️ Important Learning

During development, GitHub Push Protection blocked the repository due to an exposed API key in a .env file.



💡 Key Lesson:
Never just delete secrets — always remove them from Git history.

This highlighted real-world DevSecOps practices including:

Secret scanning
Git history safety
Secure environment handling



📌 Project Goal

OctoBot aims to become a reliable AI documentation assistant that:

Answers only from verified sources
Avoids hallucinations completely
Provides transparent, citation-based responses
Demonstrates real-world RAG architecture



🧑‍💻 Author Echoplex99 @discord

Built as a learning project exploring:

RAG systems
Modern AI architecture
OpenAI integration
Vector databases
⭐ Future Improvements
Better retrieval ranking
Multi-document support
Faster embedding pipeline
Deployment to cloud
Authentication system
