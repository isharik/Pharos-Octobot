# 🐙 Pharos Knowledge Skill — OctoBot

> **Pharos AI Agent Carnival — Phase 1 Submission**
> Category: Data Fetch / Knowledge Base

---

## What it does

OctoBot is a reusable AI Skill that answers any question about the Pharos Network using verified documentation. Any Agent on Pharos can call it via a single POST request and receive a structured answer with source citations.

**Zero hallucination** — OctoBot only answers from real documentation sources. If the answer isn't in the docs, it says so explicitly instead of guessing.

---

## Why this Skill matters for the Pharos ecosystem

Every Agent built on Pharos will eventually need to answer user questions about the protocol itself — what are SPNs, how does staking work, what is RWA, how do I build on Pharos.

Instead of every Agent building its own documentation reader, they call this one reusable Skill. It becomes the foundational knowledge layer for the entire Pharos Agent ecosystem.

---

## How any Agent calls this Skill

**Endpoint:** `POST /query`

**Request:**
```json
{
  "question": "What are Special Processing Networks?"
}
```

**Response:**
```json
{
  "answer": "SPNs (Special Processing Networks) are specialized...",
  "sources": [
    {
      "url": "https://docs.pharos.xyz/spns",
      "title": "Special Processing Networks"
    }
  ],
  "found_in_docs": true
}
```

---

## Knowledge sources

- **docs.pharos.xyz** — full site crawl (official documentation)
- **buildonpharos.com** — developer hub, grants, hackathons
- **github.com/PharosNetwork** — repository READMEs and technical docs
- **Medium** — 7 verified Pharos deep-dive articles
- **Bitget Academy** — Pharos architecture and token explainers

---

## Run it locally

**Step 1 — Clone and install:**
```
git clone <your-repo>
cd octobot
pip install -r requirements.txt
```

**Step 2 — Add your OpenAI API key:**
```
# Create a .env file with:
OPENAI_API_KEY=sk-your-key-here
```

**Step 3 — Crawl the docs and build the knowledge base:**
```
python crawl_docs.py
python build_vectorstore.py
```

**Step 4 — Start the Skill API:**
```
uvicorn skill_api:app --host 0.0.0.0 --port 8000
```

**Step 5 — Test it:**
```
# Health check
curl http://localhost:8000/

# Ask a question
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is Pharos Network?\"}"
```

**Step 6 — Open the interactive Swagger UI:**
```
http://localhost:8000/docs
```

**Step 7 — Run the chat UI (optional):**
```
streamlit run app.py
```

---

## Tech stack

| Component | Technology |
|---|---|
| LLM | GPT-4o mini (OpenAI) |
| Embeddings | text-embedding-3-small (OpenAI) |
| Vector DB | ChromaDB |
| RAG Framework | LangChain |
| Skill API | FastAPI |
| Chat UI | Streamlit |
| Language | Python 3.11+ |

---

## Project structure

```
octobot/
├── skill_api.py          # Skill API — the hackathon submission
├── skill.json            # Skill metadata
├── octobot.py            # Core RAG engine
├── app.py                # Streamlit chat UI
├── crawl_docs.py         # Multi-source documentation crawler
├── build_vectorstore.py  # Embeddings + ChromaDB builder
├── requirements.txt      # All dependencies
├── .env                  # Your API key (never commit this)
├── raw_docs/             # Crawled documentation (auto-generated)
└── chroma_db/            # Vector store (auto-generated)
```

---

## Built for

**Pharos AI Agent Carnival — Phase 1: Skill Hackathon**
Submission deadline: June 15, 2025
Register at: dorahacks.io/hackathon/pharos-phase1