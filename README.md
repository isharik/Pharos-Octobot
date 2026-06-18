
<div align="center">

<img src="pharos_logo.jpg" width="90" alt="Pharos Logo" />

# 🐙 OctoBot — The AI Knowledge & Experience Layer for Pharos

### Your AI companion for the Pharos ecosystem

Documentation • Live Data • Voice • Multilingual • Web Experience

**Built for the Pharos AI Agent Carnival ⚓**


## Updated Demo:
https://youtu.be/PeoMUNVTvGg

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

OctoBot started as a Pharos Knowledge Skill and is now evolving into a complete AI-powered Pharos companion.
Instead of behaving like a traditional documentation chatbot, OctoBot combines:

Verified documentation retrieval
Live ecosystem information
Real time token tracking
Multilingual interaction
Voice support
Modern web experience
Agent-ready API infrastructure

Any Agent deployed on Pharos can call OctoBot through a single endpoint and receive structured, source-aware responses. OctoBot’s architecture is built on a robust RAG pipeline, leveraging ChromaDB for vector retrieval and Gemini for generative responses. This scalable design allows seamless integration across Pharos Agents, ensuring accurate, source-grounded knowledge retrieval at scale

---

# 🚀 Why OctoBot?

General AI tools can answer broad questions. OctoBot empowers developers with a skill-first approach, ensuring that every Pharos Agent can focus on unique business logic while OctoBot handles the deep, technical knowledge retrieval and structured responses

OctoBot was built to answer Pharos questions the Pharos way.

The goal is to create an experience where users can:

→ Explore ecosystem updates & Learn about Pharos → Understand technical concepts → Access live market information → Interact naturally in their own language → Use AI without leaving the ecosystem

The long term vision is to make OctoBot become an embedded intelligence layer across the entire Pharos experience.**


## What problem does this solve?

Every Agent built on Pharos will eventually need to answer user questions about the protocol itself — what are SPNs, how does staking work, what is RWA, how do I build here, what is the consensus mechanism.

Traditionally, each Pharos Agent would have to individually build its own documentation retrieval logic leading to duplicated effort and inconsistent quality. OctoBot solves this by providing a single, reusable skill: a plug-and-play knowledge layer that any Agent can call, saving developers countless hours

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

<img width="1230" height="541" alt="Screenshot 2026-06-18 120804" src="https://github.com/user-attachments/assets/9849b527-c715-48b4-8fdb-655c3155971c" />


It:
First tries the RAG pipeline with a relevant question about that goal
Feeds the RAG context (if found) into a Gemini prompt asking for structured JSON: goal label, 4-5 numbered steps (title + description), 2-3 doc links, 2-3 action links
Returns the parsed dict or falls back to the RAG text answer

<img width="1193" height="580" alt="image" src="https://github.com/user-attachments/assets/5971a00a-598c-43b6-bd4b-a94ba2328e76" />



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

<!-- ===================================================== -->

<!--                    HOW TO TEST                        -->

<!-- ===================================================== -->

# 🧪 How to Test

OctoBot can be tested through multiple interfaces depending on whether you want to validate the Skill API directly, test structured responses, or experience the full UI.

---

## ① Interactive Swagger UI *(Fastest — No Code Needed)*

Use Swagger to test the Skill directly in your browser.

### Start the Skill API

```bash
uvicorn skill_api:app --host 0.0.0.0 --port 8000
```

### Open Swagger UI

```text
http://localhost:8000/docs
```

---

### Execute a Query

Navigate to:

```http
POST /query
```

Click:

```text
Try it out → Execute
```

Paste:

```json
{
  "question": "What are Special Processing Networks?"
}
```

Expected behavior:

✅ Structured response
✅ Documentation retrieval
✅ Source-aware output

---

## ② Call the Skill from Terminal

Direct API access for developers.

### Request

```bash
curl -X POST http://localhost:8000/query \
-H "Content-Type: application/json" \
-d "{\"question\":\"What is Native Restaking on Pharos?\"}"
```

### Response

```json
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
```

---

## ③ Use the Chat UI *(Recommended Experience)*

Launch the complete web experience.

### Start Streamlit

```bash
streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### Included Experience

| Feature               | Included |
| --------------------- | -------- |
| Animated Hero Section | ✅        |
| Pharos Theme          | ✅        |
| Source Citations      | ✅        |
| Sidebar Prompts       | ✅        |
| Conversation Memory   | ✅        |
| Responsive Layout     | ✅        |

---

## ④ Test the Health Check

Verify the Skill status.

### Request

```http
GET http://localhost:8000/
```

### Response

```json
{
  "skill": "pharos-knowledge",
  "status": "online",
  "knowledge_chunks": 350,
  "model": "gemini"
}
```

---

## ⑤ Discover Skill Metadata

Retrieve metadata for Agent integration.

### Request

```http
GET http://localhost:8000/info
```

### Returns

```text
✓ Input Schema
✓ Output Schema
✓ Skill Tags
✓ Categories
✓ Discovery Metadata
```

Useful for future Agent orchestration and reusable integrations.

---

<br>

# 🔌 Skill API Reference

<div align="center">

| Method | Endpoint | Description            |
| :----: | :------: | ---------------------- |
|   GET  |    `/`   | Health check           |
|  POST  | `/query` | Ask Pharos questions   |
|   GET  |  `/info` | Retrieve metadata      |
|   GET  |  `/docs` | Interactive Swagger UI |

</div>

---

# 📨 POST `/query`

### Request Body

```json
{
  "question": "string — any question about Pharos Network"
}
```

---

### Response Schema

```json
{
  "answer": "string — answer extracted from documentation",

  "sources": [
    {
      "url": "string — source page URL",
      "title": "string — source page title"
    }
  ],

  "found_in_docs": true
}
```

---

## Response Fields

| Field           | Type      | Description                                       |
| --------------- | --------- | ------------------------------------------------- |
| `answer`        | `string`  | Final generated answer                            |
| `sources`       | `array`   | Supporting references                             |
| `found_in_docs` | `boolean` | Whether information originated from verified docs |

---

<div align="center">

### ⚓ Built for reusable Agent integration

</div>



```

<!-- ===================================================== -->

<!--                ECOSYSTEM DAPPS SECTION                -->

<!-- ===================================================== -->

# 🧩 Ecosystem Tab — Easy Access to Pharos DApps

To make ecosystem discovery easier, OctoBot introduces a dedicated **Ecosystem navigation tab** directly inside the application.

This section transforms discovery from scattered searching into a **single curated experience**.

---

## 🌐 New Navigation Section

A dedicated sidebar tab:

```text
🧩 Ecosystem
```

Built to provide quick access to verified projects across the Pharos ecosystem.

---

## 🚀 Included Ecosystem DApps

Currently includes **14 confirmed Pharos ecosystem DApps**:

| DApp          | Category       |
| ------------- | -------------- |
| Faroswap      | DeFi           |
| Bitverse      | Ecosystem      |
| AquaFlux      | Infrastructure |
| Asseto        | Assets         |
| AutoStaking   | Staking        |
| Brokex        | Trading        |
| OpenFi        | Finance        |
| Zenith        | Infrastructure |
| Fiamma        | Ecosystem      |
| Gotchipus     | Gaming         |
| Buzzing Club  | Community      |
| PNS           | Identity       |
| Spout Finance | Finance        |
| Grandline     | Ecosystem      |

---

## ✨ Experience Features

Every ecosystem entry includes:

* 🏷️ Category classification
* 📝 Short description
* 🎨 Dedicated emoji icon
* 🔗 Direct access links

---

## 🔎 Discovery Experience

The Ecosystem page also introduces:

```text
Category Filter Pills
```

Allowing users to:

* Filter by category
* Discover projects faster
* Explore ecosystem sectors
* Reduce navigation friction

---

## 🎯 Goal

The Ecosystem section was designed to make discovering Pharos projects feel:

```text
Fast • Visual • Curated • Accessible
```

instead of requiring users to search externally across multiple platforms.

---

<div align="center">

### ⚓ Explore the entire Pharos ecosystem in one place

</div>

      
<img width="1210" height="880" alt="image" src="https://github.com/user-attachments/assets/1f4acba2-2529-4636-87d1-bbd7113774bf" />

    
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

# What OctoBot delivers:

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



# 📌 Recent Updates (Check @isharik on X for more details and walkthroughs on Updates :) )

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
