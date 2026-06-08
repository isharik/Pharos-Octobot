<div align="center">

<img src="pharos_logo.jpg" width="80" alt="Pharos Logo" />

# 🐙 OctoBot — Pharos Knowledge Skill

**A reusable AI Skill that answers any question about the Pharos Network**
**using verified documentation. Zero hallucination. Built for the Pharos AI Agent Carnival.**

[![Pharos](https://img.shields.io/badge/Built%20on-Pharos%20Network-1A1AFF?style=for-the-badge)](https://pharos.xyz)
[![Hackathon](https://img.shields.io/badge/Pharos-AI%20Agent%20Carnival-blueviolet?style=for-the-badge)](https://dorahacks.io/hackathon/pharos-phase1)
[![FastAPI](https://img.shields.io/badge/Skill%20API-FastAPI-009688?style=for-the-badge)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/RAG-LangChain-1C3C3C?style=for-the-badge)](https://langchain.com)

</div>

---

## What is OctoBot?

OctoBot is a **Pharos Knowledge Skill** — a reusable AI module built for the
Pharos AI Agent Carnival. Any Agent deployed on Pharos can call it with a single
POST request and receive a structured, source-cited answer about the Pharos Network.

It is powered by a RAG (Retrieval Augmented Generation) pipeline that crawls
5 verified Pharos sources, stores them as vector embeddings in ChromaDB, and uses
Gemini (Google AI) to answer questions strictly from that knowledge base.

> **No hallucination. No guessing. If the answer isn't in the docs, OctoBot says so.**

---

## Live Demo

| Interface | URL | Description |
|---|---|---|
| 💬 Chat UI | Streamlit app | Full visual chat interface |
| ⚡ Skill API | `POST /query` | For Agents to call programmatically |
| 📖 Swagger UI | `/docs` | Interactive API tester in browser |
| ❤️ Health Check | `GET /` | Confirms Skill is online |

---

## How any Agent uses this Skill

**One POST request. Structured response. That's it.**

```
POST /query
Content-Type: application/json

{
  "question": "What are Special Processing Networks?"
}
```

**Response:**
```json
{
  "answer": "SPNs (Special Processing Networks) are specialized execution environments within Pharos that handle specific computation types...",
  "sources": [
    {
      "url": "https://docs.pharos.xyz/spns",
      "title": "Special Processing Networks — Pharos Docs"
    }
  ],
  "found_in_docs": true
}
```

If the answer is not in the documentation:
```json
{
  "answer": "I could not find that information in the Pharos documentation.",
  "sources": [],
  "found_in_docs": false
}
```

---

## Skill API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check — returns status and chunk count |
| `POST` | `/query` | Main Skill endpoint — ask any Pharos question |
| `GET` | `/info` | Skill metadata for Agent discovery |
| `GET` | `/docs` | Interactive Swagger UI to test live |

---

## Knowledge Sources

OctoBot is trained on **5 verified Pharos sources. More sources will be added as developments are made**:

| # | Source | Type | Coverage |
|---|---|---|---|
| 1 | [docs.pharos.xyz](https://docs.pharos.xyz) | Full site crawl | Official documentation |
| 2 | [buildonpharos.com](https://www.buildonpharos.com) | Full site crawl | Developer hub, grants, hackathons |
| 3 | [github.com/PharosNetwork](https://github.com/PharosNetwork) | Targeted fetch | READMEs, technical specs |
| 4 | Medium — 7 articles | Targeted fetch | Deep-dive technical analysis |
| 5 | Bitget Academy | Targeted fetch | Architecture and token explainers |

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| LLM | Gemini (Google AI Studio) | Generates answers from retrieved context |
| Embeddings | Google Generative AI Embeddings | Converts text to vectors |
| Vector DB | ChromaDB | Stores and searches document embeddings |
| RAG Framework | LangChain | Orchestrates retrieval + generation pipeline |
| Skill API | FastAPI | Exposes OctoBot as a callable Skill |
| Chat UI | Streamlit | Pharos-branded visual chat interface |
| Crawler | Python + BeautifulSoup | Crawls 5 documentation sources |
| Language | Python 3.11+ | Core language |

---

## Project Structure

```
octobot/
│
├── skill_api.py          ← Skill API (hackathon submission entry point)
├── skill.json            ← Skill metadata for Agent discovery
├── octobot.py            ← Core RAG engine (retrieval + generation)
├── app.py                ← Streamlit chat UI (Pharos-branded)
│
├── crawl_docs.py         ← Multi-source documentation crawler (5 sources)
├── build_vectorstore.py  ← Generates embeddings + builds ChromaDB
│
├── test_connection.py    ← Tests Gemini API connection
├── test_retrieval.py     ← Tests ChromaDB retrieval pipeline
│
├── requirements.txt      ← All Python dependencies
├── skill.json            ← Skill metadata
├── .env                  ← API keys (never commit this file)
│
├── raw_docs/             ← Crawled documentation text files (auto-generated)
├── chroma_db/            ← ChromaDB vector store (auto-generated)
└── pharos_logo.jpg       ← Pharos logo (used in the UI hero section)
```

---

## Run it Yourself — Step by Step

### Prerequisites
- Python 3.11 or higher installed
- A Google AI Studio API key (free at [aistudio.google.com](https://aistudio.google.com))
- Git installed

---

### Step 1 — Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/octobot.git
cd octobot
```

### Step 2 — Create a virtual environment
```bash
python -m venv venv

# Windows:
venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```

### Step 3 — Install all dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Add your API key
Create a `.env` file in the `octobot` folder:
```
GOOGLE_API_KEY=your-google-ai-studio-key-here
```

### Step 5 — Crawl the Pharos documentation
```bash
python crawl_docs.py
```
Expected output: 40+ pages collected from 5 sources, saved to `raw_docs/`

### Step 6 — Build the vector store
```bash
python build_vectorstore.py
```
Expected output: 300+ chunks embedded and stored in `chroma_db/`

### Step 7A — Start the Skill API
```bash
uvicorn skill_api:app --host 0.0.0.0 --port 8000
```

Then open in your browser:
- **Interactive tester:** http://localhost:8000/docs
- **Health check:** http://localhost:8000/
- **Skill info:** http://localhost:8000/info

**Test the Skill from terminal:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is Pharos Network?\"}"
```

### Step 7B — Start the Chat UI (optional)
```bash
streamlit run app.py
```
Opens at: http://localhost:8501

---

## Why This Skill Matters for the Pharos Ecosystem

Every Agent built on Pharos will eventually need to answer user questions about
the protocol — SPNs, staking, RWA, consensus, how to build on Pharos.

Instead of every Agent building its own documentation reader from scratch, they
call this one reusable Skill. It becomes the **foundational knowledge layer** for
the entire Pharos Agent ecosystem — exactly what the hackathon is asking for.

> *"Skills become infrastructure that lives on-chain permanently."*
> — Pharos AI Agent Carnival

---

## Hackathon Submission

| Field | Detail |
|---|---|
| Event | Pharos AI Agent Carnival — Phase 1 Skill Hackathon |
| Category | Data Fetch / Knowledge Base |
| Submission deadline | June 15, 2025 |
| Platform | [DoraHacks](https://dorahacks.io/hackathon/pharos-phase1) |
| Check out my submission and do Upvote :)| https://dorahacks.io/buidl/44453 |
---

## .gitignore

Make sure these are in your `.gitignore` before pushing to GitHub:
```
.env
chroma_db/
raw_docs/
venv/
__pycache__/
*.pyc
```

---

## License

MIT — free to use, fork, and build upon.

---

<div align="center">
Built with 🐙 for the Pharos community<br>
<a href="https://pharos.xyz">pharos.xyz</a> ·
<a href="https://docs.pharos.xyz">docs.pharos.xyz</a> ·
<a href="https://dorahacks.io/hackathon/pharos-phase1">DoraHacks</a>
</div>
