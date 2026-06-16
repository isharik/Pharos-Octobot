
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

---

# 🖥️ Website Experience (NEW)

OctoBot is no longer just chat.

The app now includes a redesigned website experience while keeping the original Pharos identity.

### Homepage

* Minimal welcome experience
* Cleaner structure
* Better onboarding
* Animated live UI feeling
* Improved hero section

### Added Sections

* 💬 Chat with OctoBot
* 📖 Direct Docs Access
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

Ask questions directly from verified Pharos sources.

## Model Fallback

If information isn't available in documentation, OctoBot intelligently responds instead of failing.

## Multilingual + Voice Support

Ask in your own language.

Examples:

```text
Hindi → PROS ka price kya hai
Spanish → ¿Qué son las SPNs?
Japanese → Pharosとは何ですか？
Arabic → ما هو فاروس؟
```

Replies preserve technical terms while adapting language naturally.

---

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

Example:

```bash
GET /pros-price
```

---

# 🔍 Knowledge Sources

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
