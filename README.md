🐙 OctoBot — AI Documentation RAG Chatbot

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
