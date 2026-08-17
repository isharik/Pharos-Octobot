# 🐙 OctoBot

**The AI Financial Copilot for the Pharos Ecosystem**

[![Built with Streamlit](https://img.shields.io/badge/Built%20with-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Google%20Gemini-4285F4?logo=googlegemini&logoColor=white)](https://ai.google.dev)
[![RAG: LangChain + ChromaDB](https://img.shields.io/badge/RAG-LangChain%20%2B%20ChromaDB-1C3C3C)](https://www.trychroma.com)
[![Pharos AI Agent Carnival](https://img.shields.io/badge/Pharos-AI%20Agent%20Carnival-6B4EFF)](https://docs.pharos.xyz)

OctoBot is a single conversational interface for the Pharos ecosystem. It answers questions from verified Pharos documentation, reads and explains wallets and transactions straight off Pharos RPC, surfaces live ecosystem data, and exposes all of it as an agent-callable API — so users get one AI copilot instead of a dozen tabs of explorers, docs, and dashboards.

---

## Why this exists

Pharos is expanding fast — RWAs, DeFi, payments, lending, stablecoins, AI agents, on-chain infrastructure — but today, using any of it means bouncing between the docs site, a block explorer, a wallet UI, and a handful of dashboards just to answer one simple question ("what does this transaction actually do?", "is this protocol part of Pharos?", "how do I build on Pharos with Foundry?").

OctoBot collapses that into one interface: ask it, and it reads the docs, reads the chain, and answers in plain language — with sources, not guesses.

---

## What it actually does

| Capability | What's really happening |
|---|---|
| **Verified Q&A (RAG)** | Every ecosystem question is answered from a Chroma vector store built from a full crawl of `docs.pharos.xyz`, the Pharos GitHub orgs, and vetted deep-dive articles — grounded in real sources, not model memory. |
| **Wallet Intelligence** | Give it any address; it pulls live on-chain data via Pharos RPC (balance, tx count, contract status) and has Gemini synthesize a plain-English profile — read-only, nothing is ever signed or spent. |
| **Transaction Explanation** | Paste a tx hash and get a human explanation of what happened, the transfer flow, and how it executed — no more staring at raw calldata. |
| **Memory Ledger** | Wallet profiles and explained transactions persist per-session as an inspectable, searchable ledger — not a one-off answer that disappears. |
| **Live Ecosystem Data** | $PROS price, ecosystem news, and the official Pharos X feed, all served through a non-blocking background-fetch layer so pages never hang waiting on the network. |
| **x402 Micro-payments** | Implements Pharos's own `x402` HTTP 402 pay-per-call standard for premium, higher-depth AI replies — a working example of on-chain-native monetization, not just a mock. |
| **Payment Agent** | Send $PROS with plain English ("send 5 PROS to 0x1234…") — OctoBot builds and routes the request. |
| **Multilingual, dual-mode chat** | Ask in any language; toggle between "Docs only" (strictly source-grounded) and "Docs + General" (Gemini fills gaps outside the docs). |
| **Agent-callable Skill API** | A standalone FastAPI service (`skill_api.py`) exposes the RAG answer engine, wallet profiling, and tx explanation as REST endpoints with OpenAPI docs — built for the **Pharos AI Agent Carnival**, so other agents can call OctoBot's intelligence directly. |

Plus a full ecosystem hub around it: live network stats, campaigns, SPN discovery, and a DeFi surface — all in the same app.

---

## How it's built

```
┌─────────────────────────────┐        ┌──────────────────────────┐
│   Streamlit app (app.py)    │        │  skill_api.py (FastAPI)  │
│  chat · wallet · tx · feed  │        │  agent-callable REST API │
└──────────────┬───────────────┘        └─────────────┬────────────┘
               │                                        │
               ▼                                        ▼
      ┌─────────────────┐                      ┌─────────────────┐
      │   octobot.py     │◄────── shared ──────►│   ChromaDB       │
      │  RAG engine      │                      │  vector store    │
      └────────┬─────────┘                      └─────────────────┘
               │
      ┌────────┴────────┐
      │  Google Gemini   │   LLM answers + embeddings
      └──────────────────┘

      ┌──────────────────┐   ┌──────────────────┐
      │   Pharos RPC      │   │  CoinGecko / X    │
      │  wallet + tx read  │   │  price + feed      │
      └──────────────────┘   └──────────────────┘
```

The knowledge base (`chroma_gemini/`) is built once from a full crawl of Pharos documentation (`crawl_docs.py` → `build_vectorstore.py`), then queried live at chat time — retrieval happens first, generation happens second, so answers stay grounded.

---

## Tech stack

- **App / UI:** [Streamlit](https://streamlit.io)
- **Agent API:** [FastAPI](https://fastapi.tiangolo.com) + Uvicorn
- **RAG:** [LangChain](https://www.langchain.com) + [ChromaDB](https://www.trychroma.com)
- **LLM & embeddings:** [Google Gemini](https://ai.google.dev) (`gemini-2.5-flash`, `gemini-embedding-001`)
- **Chain data:** `web3.py` over Pharos RPC
- **Market data:** CoinGecko API
- **Language:** Python 3

---

## Getting started

```bash
git clone https://github.com/isharik/Pharos-Octobot.git
cd Pharos-Octobot

python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your-gemini-api-key
```

Run the app:

```bash
streamlit run app.py
```

Run the agent-callable Skill API (optional, separate process):

```bash
uvicorn skill_api:app --host 0.0.0.0 --port 8000
# Interactive docs at http://localhost:8000/docs
```

> The knowledge base ships pre-built in `chroma_gemini/`. To rebuild it from scratch, run `crawl_docs.py` then `build_vectorstore.py` — you'll need `GEMINI_API_KEY` set, since embeddings are generated via the Gemini API.

---

## Project structure

```
app.py                      # the full Streamlit app — every page, all UI
octobot.py                  # RAG engine: embeddings + Chroma + Gemini LLM
skill_api.py                # standalone FastAPI agent-callable API
build_vectorstore.py        # builds the Chroma vector store from raw_docs/
crawl_docs.py                # crawls docs.pharos.xyz into raw_docs/
rebuild_vectorstore_gemini.py # migration: re-embed an existing store with Gemini
chroma_gemini/                # active knowledge base (committed, required to run)
raw_docs/                    # crawled source documentation
```

---

## Roadmap

- AI portfolio intelligence & personalized recommendations
- Yield opportunity discovery across Pharos DeFi
- RWA, lending, and stablecoin analytics
- Deeper protocol integrations as new RealFi apps launch on Pharos
- Expanded x402 premium workflows and AI-driven transaction automation

---

## Vision

Web3's biggest usability problem isn't a lack of infrastructure — it's that using it still means becoming your own integrator. OctoBot's bet is that the right interface for an ecosystem this complex is conversational: one place that already knows the docs, can read the chain, and can act on both.

---

## Credits

Built by **Echo** for the **Pharos AI Agent Carnival**.

- Discord: `@echoplex99`
- X: [@isharik99](https://x.com/isharik99)
- GitHub: [isharik/Pharos-Octobot](https://github.com/isharik/Pharos-Octobot)
