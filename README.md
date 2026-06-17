
<div align="center">

<img src="pharos_logo.jpg" width="90" alt="Pharos Logo" />

# 🐙 OctoBot — The AI Knowledge & Experience Layer for Pharos

### Your AI companion for the Pharos ecosystem

Documentation • Live Data • Voice • Multilingual • Web Experience

**Built for the Pharos AI Agent Carnival ⚓**


## Demo before updates:

https://www.youtube.com/watch?v=gIsav6XI6HE

## 🌐 New Live Demo after updates

https://x.com/isharik99/status/2066777239627387353?s=20

## Check out the Dora Hacks page for more details on updates :

https://dorahacks.io/buidl/44453

## Public Link (Always under Development)
https://pharos-octobot-by-echo.streamlit.app/

*(If unavailable, the request quota may have expired. You can clone the repo and run locally with your own API key.)*

[![Pharos](https://img.shields.io/badge/Built%20on-Pharos%20Network-1A1AFF?style=for-the-badge)](https://pharos.xyz)
[![Hackathon](https://img.shields.io/badge/Pharos-AI%20Agent%20Carnival-blueviolet?style=for-the-badge)](https://dorahacks.io/hackathon/pharos-phase1)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/RAG-LangChain-1C3C3C?style=for-the-badge)](https://langchain.com)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red?style=for-the-badge)](https://streamlit.io)

</div>

---

# ✨ What is OctoBot?

OctoBot started as a **Pharos Knowledge Skill** and evolved into a **complete AI experience for the Pharos ecosystem**.

Instead of acting like a traditional docs chatbot, OctoBot combines:

📚 Verified documentation retrieval
🌐 Live ecosystem information
💹 Real time token data
🗣️ Voice interactions
🌎 Multilingual conversations
🧠 Intelligent model fallback
🎨 Modern website experience
⚡ Agent-ready APIs

Any AI Agent deployed on Pharos can integrate OctoBot using a single API request and receive structured, context-aware responses.

---

# 🚀 Why OctoBot?

General AI can answer questions.

OctoBot was designed to answer **Pharos questions with Pharos context.**

It combines:

* Verified documentation
* Real ecosystem updates
* Dynamic market information
* AI powered assistance
* Better onboarding for new users
* Developer friendly integrations

The long term goal is to become an **embedded AI layer across the Pharos ecosystem.**


## What problem does this solve?

Every Agent built on Pharos will eventually need to answer user questions about the protocol itself — what are SPNs, how does staking work, what is RWA, how do I build here, what is the consensus mechanism.
Right now, every builder would have to build their own documentation reader from scratch. OctoBot solves this once, for everyone. It is a plug-and-play knowledge layer that any Agent can call instantly.

---

# 🖥️ Website Experience (NEW)




OctoBot is no longer just chat.

<img width="1400" height="811" alt="image" src="https://github.com/user-attachments/assets/cf7898a4-ed04-4dec-bc8e-c4033db33faa" />

The app now includes a redesigned website experience while keeping the original Pharos identity.

### Homepage

* Minimal welcome experience
* Cleaner structure
* Better onboarding
* Animated live UI feeling
* Improved hero section

### Added Sections

* 💬 Chat with OctoBot
* 📖 Ecosystem Dapps
* 📢 Campaigns Section
* 📰 Updates Section
* 💹 Trade Pharos Area
* ⚡ Featured Actions
* 📊 Live Token Dashboard

### UI Improvements

* Improved visual hierarchy
* Better spacing and layouts
* Cleaner cards
* Responsive structure
* More polished interactions

---

# 🧠 AI Features

## Documentation Intelligence

Ask questions directly from verified Pharos sources and LLM Models.

## Model Fallback

If information isn't available in documentation, OctoBot intelligently responds instead of failing. 

<img width="1147" height="218" alt="image" src="https://github.com/user-attachments/assets/f7357531-eea0-4819-b364-5f98c30387ca" />


## Multilingual + Read answers Support

Ask in your own language.

Chat input placeholder updates too  when Hindi is selected it shows "Ask OctoBot in Hindi 🌐" so users know the language is active.
English stays clean when English is selected, no prefix is added and the fallback prompt uses standard English instructions, so there's zero overhead for the default case.

Examples:

```text
Hindi → PROS ka price kya hai
Spanish → ¿Qué son las SPNs?
Japanese → Pharosとは何ですか？
Arabic → ما هو فاروس؟
```

Replies preserve technical terms while adapting language naturally.

---
## Build Path Generator

It:
First tries the RAG pipeline with a relevant question about that goal
Feeds the RAG context (if found) into a Gemini prompt asking for structured JSON: goal label, 4-5 numbered steps (title + description), 2-3 doc links, 2-3 action links
Returns the parsed dict or falls back to the RAG text answer
<img width="1195" height="300" alt="image" src="https://github.com/user-attachments/assets/167d961a-9a69-4559-b884-ce9403bc90a0" />



# 📈 Live Ecosystem Data

## PROS Token Integration

Powered via CoinGecko.

Features:

* Live Price
* Market Cap
* Volume
* Auto refresh (5 min)
* Dedicated API endpoint
* Table visualization in Streamlit
* Token responses directly inside chat

 <img width="1158" height="678" alt="image" src="https://github.com/user-attachments/assets/f91fd1a4-5170-4dec-a882-bfd210be9e00" />


## How to Test it ?

Option 1 — Interactive Swagger UI (easiest, no code needed)
Start the Skill API:
uvicorn skill_api:app --host 0.0.0.0 --port 8000
Open in your browser:
http://localhost:8000/docs

Click POST /query → Try it out → Execute
Type any question about Pharos in the request body:
{
  "question": "What are Special Processing Networks?"
}
Hit Execute and see the full structured response instantly.
Option 2 — Call the Skill from Terminal
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d "{\"question\": \"What is Native Restaking on Pharos?\"}"
Response:

{
  "answer": "Native Restaking on Pharos allows validators to...",
  "sources": [
    {
      "url": "https://docs.pharos.xyz/restaking",
      "title": "Native Restaking — Pharos Docs"
    }
  ],
  "found_in_docs": true
}

# Option 3 — Use the Chat UI (Recommended)
streamlit run app.py

Opens a full Pharos-branded chat interface at http://localhost:8501 with:

Logo hero section with animated glow effects
Dark Pharos blue theme matching the brand
Source citations shown for every answer
Example questions in the sidebar
Conversation memory

# Option 4 — Test the Health Check
GET http://localhost:8000/
Returns:

{
  "skill": "pharos-knowledge",
  "status": "online",
  "knowledge_chunks": 350,
  "model": "gemini"
}

# Option 5 — Discover Skill Metadata

GET http://localhost:8000/info
Returns the full Skill spec — input/output schema, tags, category — for Agent discovery and integration.

Skill API Reference
MethodEndpointWhat it doesGET/Health check — is the Skill online?POST/queryAsk any Pharos question, get structured answerGET/infoSkill metadata for Agent discoveryGET/docsInteractive Swagger UI — test in browser

Request body for POST /query
{
  "question": "string — any question about Pharos Network"
}
Response schema
{
  "answer": "string — answer extracted from documentation",
  "sources": [
    {
      "url": "string — source page URL",
      "title": "string — source page title"
    }
  ],
  "found_in_docs": "boolean — true if answer was found"
}

Example:

```bash
GET /pros-price
```

---

## Ecosystem Tab for Easy Access to Dapps :

# Ecosystem DApps page  new nav tab
 "🧩 Ecosystem" with 14 confirmed Pharos DApps: Faroswap, Bitverse, AquaFlux, Asseto, AutoStaking, Brokex, OpenFi, Zenith, Fiamma, Gotchipus, Buzzing Club, PNS, Spout Finance, and Grandline 
      Each with category, description, emoji, and direct link. Category filter pills at the top.

      <img width="1210" height="906" alt="image" src="https://github.com/user-attachments/assets/1f96b9ea-2232-41b6-beda-881dd19ae130" />



# 🔍 Knowledge Sources other than LLM responses

OctoBot currently retrieves from verified sources:

| Source            | Coverage               |
| ----------------- | ---------------------- |
| docs.pharos.xyz   | Official Documentation |
| buildonpharos.com | Developer Resources    |
| Pharos GitHub     | Technical References   |
| Medium Articles   | Deep Technical Content |
| Bitget Academy    | Ecosystem Explanations |

More sources continue to be crawled and indexed.

---

# ⚙️ Tech Stack

| Layer      | Technology           |
| ---------- | -------------------- |
| LLM        | Gemini               |
| Embeddings | Google Generative AI |
| Vector DB  | ChromaDB             |
| Framework  | LangChain            |
| Backend    | FastAPI              |
| Frontend   | Streamlit            |
| Crawling   | BeautifulSoup        |
| Language   | Python 3.11+         |

---

## My Pitch for Phase 1 :)

# The hackathon asked for a Skill that solves a focused problem well and can be reused across the ecosystem instead of being tied to a single application.
# OctoBot was built around that idea.

Rather than every Agent rebuilding its own documentation search, retrieval logic, and answer validation layer, OctoBot provides a single reusable knowledge interface for Pharos.
What OctoBot delivers:

✅ Simple input — send a question string

✅ Structured output — returns answer + sources + found_in_docs status

✅ Agent friendly integration — callable through a standard HTTP POST request

✅ Discoverable architecture — exposed through the /info metadata endpoint

✅ Source grounded responses — answers include references for verification

✅ Transparent behavior — clearly indicates when information is unavailable instead of pretending certainty

✅ Built to reduce hallucinations — retrieval first, generation second

✅ Composable by design — can plug into future Agents and workflows that require Pharos knowledge

The goal was not to build another chatbot.
The goal was to create a reusable knowledge layer that any future Pharos Agent can rely on.



# 📌 Recent Updates

## ✅ 8 June 2026

* Added Skill Test feature
* Expanded data crawling
* Website improvements

## ✅ 12 June 2026

* Added live PROS integration
* Added dedicated token endpoint
* Added Streamlit token support

## ✅ 13 June 2026

* Added real time price tables
* Added market data visualization

## ✅ 14 June 2026

* Added multilingual support
* Added voice interactions
* Added automatic response translation

## ✅ Latest Update

* Full homepage redesign
* New website sections
* Campaigns integration
* Updates center
* Trade Pharos section
* Better navigation
* Improved responsiveness
* Cleaner layouts
* Enhanced AI routing
* More polished experience

## FOR MORE UPDATES CHECK OUT THE CODE & DORA HACKS SITE 

---

# 🧩 API Endpoints

| Method | Endpoint      | Purpose        |
| ------ | ------------- | -------------- |
| GET    | `/`           | Health Check   |
| POST   | `/query`      | Ask OctoBot    |
| GET    | `/info`       | Skill Metadata |
| GET    | `/docs`       | Swagger UI     |
| GET    | `/pros-price` | Live PROS Data |

---

# 🛠️ Run Locally

```bash
git clone https://github.com/YOUR_USERNAME/octobot.git

cd octobot

python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create `.env`

```env
GOOGLE_API_KEY=your_key_here
```

Run:

```bash
python crawl_docs.py

python build_vectorstore.py

uvicorn skill_api:app --reload

streamlit run app.py
```

---

# 🎯 Vision

OctoBot is becoming more than a knowledge skill.

The goal is to create the **AI front page of Pharos** where users can explore documentation, discover updates, access live data, and interact with the ecosystem in one place.

---

<div align="center">

Built with 🐙 for the Pharos community

⭐ Star the repo if you enjoyed it

</div>
