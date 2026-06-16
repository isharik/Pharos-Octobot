"""
skill_api.py
------------
OctoBot Skill API — Pharos AI Agent Carnival submission.

FEATURES:
  1. Answers any Pharos question from verified documentation
  2. Live $PROS price from CoinGecko (verified ID: pharos)
     - Cached 5 minutes
     - Injected into answers when question is token-related
     - Graceful fallback if CoinGecko is unavailable
  3. GET /pros-price endpoint returns full market data

ENDPOINTS:
  GET  /            health check
  POST /query       main Skill — ask any Pharos question
  GET  /pros-price  live $PROS price + market cap
  GET  /info        Skill metadata
  GET  /docs        interactive Swagger UI

HOW TO RUN:
    uvicorn skill_api:app --host 0.0.0.0 --port 8000

.env must contain:
    GEMINI_API_KEY=your-gemini-key-here

chroma_db/ must exist:
    python build_vectorstore.py
"""

import os
import time
import requests as http_requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# ─────────────────────────────────────────────
# STARTUP CHECKS
# ─────────────────────────────────────────────
if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError(
        "GEMINI_API_KEY not found in .env file. "
        "Add: GEMINI_API_KEY=your-key"
    )

if not os.path.exists("chroma_db"):
    raise RuntimeError(
        "chroma_db/ not found. Run: python build_vectorstore.py"
    )

# ─────────────────────────────────────────────
# LOAD OCTOBOT
# ─────────────────────────────────────────────
from octobot import OctoBot

print("Loading OctoBot knowledge base...")
bot = OctoBot()
print("OctoBot ready — Skill API starting.")

# ─────────────────────────────────────────────
# COINGECKO INTEGRATION
#
# Verified CoinGecko asset ID: "pharos"
# Confirmed from: coingecko.com/en/coins/pharos
# Free API — no key required
# Rate limit: 100 calls/min (we cache 5 min so ~1 call/5min)
# ─────────────────────────────────────────────
COINGECKO_ASSET_ID    = "pharos-network"
COINGECKO_URL         = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=" + COINGECKO_ASSET_ID +
    "&vs_currencies=usd"
    "&include_24hr_change=true"
    "&include_market_cap=true"
    "&include_24hr_vol=true"
)
PRICE_CACHE_SECONDS   = 300   # 5 minutes

# Single shared cache dict — updated by fetch_pros_price()
_price_cache: dict = {
    "price_usd":      None,
    "market_cap_usd": None,
    "volume_24h":     None,
    "change_24h":     None,
    "last_updated":   None,   # ISO string shown to users
    "fetched_at":     0.0,    # Unix timestamp for cache logic
    "available":      False,  # False if CoinGecko unreachable
    "error":          None,
}


def fetch_pros_price() -> dict:
    """
    Fetch live $PROS price from CoinGecko.

    Returns cached result if fetched less than 5 minutes ago.
    On any failure sets available=False and preserves last
    known values — app never crashes because of this.
    """
    now = time.time()
    if now - _price_cache["fetched_at"] < PRICE_CACHE_SECONDS:
        return _price_cache

    try:
        resp = http_requests.get(
            COINGECKO_URL,
            timeout=8,
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json().get(COINGECKO_ASSET_ID, {})

        if not data:
            raise ValueError(
                "CoinGecko returned empty data for ID: " + COINGECKO_ASSET_ID
            )

        _price_cache.update({
            "price_usd":      data.get("usd"),
            "market_cap_usd": data.get("usd_market_cap"),
            "volume_24h":     data.get("usd_24h_vol"),
            "change_24h":     data.get("usd_24h_change"),
            "last_updated":   datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "fetched_at":     now,
            "available":      True,
            "error":          None,
        })

    except Exception as e:
        _price_cache.update({
            "available":  False,
            "fetched_at": now,   # don't retry immediately
            "error":      str(e),
        })

    return _price_cache


def build_price_snippet(price: dict) -> str:
    """
    Build a short markdown string appended to doc answers
    when the question is about the token/price/market.
    Returns empty string if price data is unavailable.
    """
    if not price.get("available") or price.get("price_usd") is None:
        return ""

    usd      = price["price_usd"]
    mcap     = price.get("market_cap_usd")
    chg      = price.get("change_24h")
    updated  = price.get("last_updated", "N/A")

    chg_str  = f"{chg:+.2f}%" if chg  is not None else "N/A"
    mcap_str = f"${mcap:,.0f}" if mcap is not None else "N/A"

    return (
        "\n\n---\n"
        "**Live $PROS Market Data** *(via CoinGecko)*\n\n"
        f"| Price (USD) | Market Cap | 24h Change | Updated |\n"
        f"|---|---|---|---|\n"
        f"| **${usd:.4f}** | {mcap_str} | {chg_str} | {updated} |"
    )


# Keywords that trigger price injection into documentation answers
PRICE_KEYWORDS = [
    "pros", "$pros", "price", "token", "coin",
    "market cap", "market", "worth", "value",
    "cost", "trading", "buy", "sell",
    "usd", "dollar", "volume", "statistics",
    "tokenomics", "circulating", "supply",
]


def is_price_question(question: str) -> bool:
    """Return True if the question is about token/price/market data."""
    q = question.lower()
    return any(kw in q for kw in PRICE_KEYWORDS)


# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="Pharos Knowledge Skill",
    description=(
        "Reusable AI Skill — Pharos AI Agent Carnival Phase 1.\n\n"
        "Answers questions about Pharos Network from verified documentation. "
        "Returns live $PROS market data from CoinGecko when relevant. "
        "Zero hallucination — only answers from real sources."
    ),
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────
class SkillRequest(BaseModel):
    question: str

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is the PROS token used for?"
            }
        }


class SourceItem(BaseModel):
    url:   str
    title: str


class SkillResponse(BaseModel):
    answer:        str
    sources:       list[SourceItem]
    found_in_docs: bool
    pros_price:    dict | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "The PROS token is used for...\n\n---\n**Live $PROS Market Data**...",
                "sources": [
                    {"url": "https://docs.pharos.xyz", "title": "Pharos Docs"}
                ],
                "found_in_docs": True,
                "pros_price": {
                    "price_usd":      0.5828,
                    "market_cap_usd": 75000000,
                    "change_24h":     7.39,
                    "available":      True,
                    "source":         "CoinGecko",
                }
            }
        }


class PriceResponse(BaseModel):
    price_usd:      float | None
    market_cap_usd: float | None
    volume_24h:     float | None
    change_24h:     float | None
    last_updated:   str | None
    available:      bool
    source:         str = "CoinGecko"
    asset_id:       str = COINGECKO_ASSET_ID
    warning:        str | None = None


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """
    Health check.
    Returns Skill status, knowledge base size, and current PROS price.
    """
    price  = fetch_pros_price()
    chunks = bot.vectorstore._collection.count()
    return {
        "skill":             "pharos-knowledge",
        "version":           "1.1.0",
        "status":            "online",
        "knowledge_chunks":  chunks,
        "model":             "gemini",
        "pros_price_usd":    price.get("price_usd"),
        "coingecko_status":  "ok" if price.get("available") else "unavailable",
    }


@app.post("/query", response_model=SkillResponse, tags=["Skill"])
def query_pharos_docs(request: SkillRequest):
    """
    Main Skill endpoint.

    - Retrieves answer from Pharos documentation (RAG pipeline)
    - Preserves the full documentation answer unchanged
    - Appends live $PROS market data when question is token-related
    - If CoinGecko is down: documentation answer still returned, price omitted
    - Returns found_in_docs=False when answer is not in documentation
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="question field cannot be empty."
        )

    question = request.question.strip()

    # ── Step 1: Get documentation answer from OctoBot ──
    try:
        answer, raw_sources = bot.ask(question)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="OctoBot RAG error: " + str(e)
        )

    not_found = "I could not find that information" in answer
    found     = not not_found

    # ── Step 2: Optionally append live price ──────────
    price_payload = None
    if is_price_question(question):
        price = fetch_pros_price()
        if price.get("available"):
            snippet = build_price_snippet(price)
            if snippet:
                answer += snippet      # append after doc answer, never replace
                price_payload = {
                    "price_usd":      price.get("price_usd"),
                    "market_cap_usd": price.get("market_cap_usd"),
                    "change_24h":     price.get("change_24h"),
                    "last_updated":   price.get("last_updated"),
                    "available":      True,
                    "source":         "CoinGecko",
                }
        # If CoinGecko unavailable — silently skip, doc answer still returned

    # ── Step 3: Build response ────────────────────────
    sources = [
        SourceItem(url=s.get("url", ""), title=s.get("title", ""))
        for s in raw_sources
    ]

    return SkillResponse(
        answer=answer,
        sources=sources,
        found_in_docs=found,
        pros_price=price_payload,
    )


@app.get("/pros-price", response_model=PriceResponse, tags=["Live Data"])
def get_pros_price():
    """
    Live $PROS token price and market data from CoinGecko.

    - Cached for 5 minutes
    - Returns warning if CoinGecko is unavailable
    - Never returns 500 — always returns a valid response
    - asset_id field confirms which CoinGecko ID is being used
    """
    price = fetch_pros_price()

    warning = None
    if not price.get("available"):
        warning = (
            "CoinGecko data temporarily unavailable. "
            "Error: " + str(price.get("error", "unknown"))
        )

    return PriceResponse(
        price_usd=      price.get("price_usd"),
        market_cap_usd= price.get("market_cap_usd"),
        volume_24h=     price.get("volume_24h"),
        change_24h=     price.get("change_24h"),
        last_updated=   price.get("last_updated"),
        available=      price.get("available", False),
        warning=        warning,
    )


@app.get("/info", tags=["Skill"])
def skill_info():
    """Skill metadata for Agent discovery and integration."""
    return {
        "skill_name":    "pharos-knowledge",
        "version":       "1.1.0",
        "description":   (
            "Answers questions about Pharos Network from verified documentation. "
            "Appends live $PROS market data for token-related questions."
        ),
        "category":      "data-fetch",
        "input": {
            "question": "string — any question about Pharos Network"
        },
        "output": {
            "answer":        "string — documentation answer + optional price data",
            "sources":       "array of {url, title}",
            "found_in_docs": "boolean",
            "pros_price":    "object (present only for token-related questions)",
        },
        "live_data": {
            "provider":   "CoinGecko",
            "asset_id":   COINGECKO_ASSET_ID,
            "cache_mins": PRICE_CACHE_SECONDS // 60,
        },
        "tags": [
            "pharos", "documentation", "RAG",
            "knowledge-base", "live-price", "AI"
        ],
    }