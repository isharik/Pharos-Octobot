"""
skill_api.py
------------
OctoBot Skill API — Pharos AI Agent Carnival Phase 1 submission.

FEATURES:
  1. Answers any Pharos question from verified RAG documentation
  2. Live $PROS price from CoinGecko — cached 5 min, graceful fallback
  3. On-chain wallet profiling via Pharos RPC — read-only, zero gas
  4. Plain-language transaction explanation via Pharos RPC + Gemini

ENDPOINTS:
  GET  /                health check + knowledge base size + live price
  POST /query           RAG answer from Pharos docs + optional live price
  GET  /pros-price      live $PROS price + market cap (CoinGecko)
  POST /wallet-profile  on-chain wallet intelligence profile
  POST /explain-tx      plain-language transaction explanation
  GET  /info            Skill metadata for Agent discovery
  GET  /docs            interactive Swagger UI

HOW TO RUN:
    uvicorn skill_api:app --host 0.0.0.0 --port 8000

.env must contain:
    GEMINI_API_KEY=your-gemini-key-here

chroma_db/ must exist:
    python build_vectorstore.py
"""

import os
import re
import json
import time
import requests as http_requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# ─────────────────────────────────────────────
# PHAROS RPC CONFIG
# ─────────────────────────────────────────────
PHAROS_RPC_URL      = "https://rpc.pharos.xyz"
PHAROS_RPC_FALLBACK = "https://pharos.drpc.org"
PHAROS_EXPLORER_URL = "https://pharosscan.xyz"
RPC_HEADERS         = {"Content-Type": "application/json"}

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
        "skill_name":    "octobot-pharos",
        "version":       "2.0.0",
        "description":   (
            "4-endpoint Pharos AI Skill suite: RAG documentation answers, "
            "live $PROS price, on-chain wallet profiling, and transaction explanation. "
            "All on-chain reads are public, read-only, zero gas, no signature."
        ),
        "category":      "data-fetch + on-chain-intelligence",
        "endpoints": {
            "POST /query":          "RAG answer from Pharos docs + optional live price",
            "GET  /pros-price":     "Live $PROS market data from CoinGecko",
            "POST /wallet-profile": "On-chain wallet intelligence profile",
            "POST /explain-tx":     "Plain-language transaction explanation",
        },
        "live_data": {
            "price_provider": "CoinGecko",
            "chain_rpc":      PHAROS_RPC_URL,
            "explorer":       PHAROS_EXPLORER_URL,
            "cache_mins":     PRICE_CACHE_SECONDS // 60,
        },
        "safety": "Read-only · No funds accessed · No signature required · Zero gas",
        "tags": [
            "pharos", "documentation", "RAG", "on-chain",
            "wallet", "transaction", "live-price", "AI", "skill"
        ],
    }


# ─────────────────────────────────────────────
# WALLET PROFILE SKILL
# ─────────────────────────────────────────────

class WalletRequest(BaseModel):
    address: str

    class Config:
        json_schema_extra = {
            "example": {"address": "0x1234567890abcdef1234567890abcdef12345678"}
        }


class WalletResponse(BaseModel):
    address:      str
    balance_pros: float | None
    tx_count:     int | None
    is_contract:  bool
    profile:      dict | None
    available:    bool
    explorer_url: str
    error:        str | None = None


def _rpc_call(payload: dict) -> dict:
    """Try primary RPC then fallback. Returns parsed JSON result."""
    for url in [PHAROS_RPC_URL, PHAROS_RPC_FALLBACK]:
        try:
            r = http_requests.post(url, json=payload,
                                   headers=RPC_HEADERS, timeout=8)
            r.raise_for_status()
            return r.json()
        except Exception:
            continue
    raise RuntimeError("All Pharos RPC endpoints unreachable")


def _synthesize_profile(address: str, balance: float | None,
                         tx_count: int | None, is_contract: bool) -> dict:
    """Call Gemini to build a wallet intelligence profile."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _deterministic_profile(balance, tx_count)
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.4,
            google_api_key=api_key,
        )
        prompt = (
            "You are OctoBot's on-chain intelligence module for Pharos Network. "
            "Based on this read-only wallet data, write a SHORT (3-4 sentence) "
            "friendly profile summary as if OctoBot already knows this user. "
            "Then suggest 3 short descriptive tags (2-3 words each) and a one-word "
            "risk profile (Conservative / Moderate / Active / New Wallet).\n\n"
            f"Wallet: {address}\n"
            f"PROS Balance: {balance if balance is not None else 'unknown'}\n"
            f"Transaction count: {tx_count if tx_count is not None else 'unknown'}\n"
            f"Is contract address: {is_contract}\n\n"
            "Return ONLY valid JSON, no markdown fences:\n"
            '{"summary":"...","tags":["tag1","tag2","tag3"],'
            '"risk":"...","insight":"one actionable suggestion for Pharos"}'
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw  = re.sub(r"^```(?:json)?\n?", "", resp.content.strip(), flags=re.IGNORECASE)
        raw  = re.sub(r"\n?```$", "", raw)
        parsed = json.loads(raw)
        if all(k in parsed for k in ("summary", "tags", "risk", "insight")):
            return parsed
    except Exception:
        pass
    return _deterministic_profile(balance, tx_count)


def _deterministic_profile(balance: float | None, tx_count: int | None) -> dict:
    n = tx_count or 0
    if n == 0:    label, risk = "New Wallet",     "Unknown"
    elif n <= 20: label, risk = "Early Explorer", "Conservative"
    elif n <= 150:label, risk = "Active Trader",  "Moderate"
    else:         label, risk = "Power User",     "Active"
    bal_str = f"{balance:.4f}" if balance is not None else "unknown amount of"
    return {
        "summary": (
            f"This wallet has made {n} transaction{'s' if n!=1 else ''} on Pharos "
            f"with a current balance of {bal_str} PROS."
        ),
        "tags":    [label, "Pharos Native", "On-chain Verified"],
        "risk":    risk,
        "insight": "Explore Pharos DApps to grow your on-chain activity.",
    }


@app.post("/wallet-profile", response_model=WalletResponse, tags=["On-Chain"])
def wallet_profile(request: WalletRequest):
    """
    On-chain wallet intelligence profile.

    Reads public blockchain data via Pharos RPC:
    - PROS balance
    - Transaction count
    - Contract vs wallet detection

    Then synthesises an AI-generated intelligence profile via Gemini.
    Read-only · No signature · Zero gas · No funds accessed.
    """
    addr = request.address.strip()
    if not (addr.startswith("0x") and len(addr) == 42):
        raise HTTPException(
            status_code=400,
            detail="Invalid address — must be 0x... (42 characters)"
        )

    balance, tx_count, is_contract = None, None, False
    available = False
    error     = None

    try:
        # Balance
        r1 = _rpc_call({"jsonrpc":"2.0","id":1,
                         "method":"eth_getBalance","params":[addr,"latest"]})
        if r1.get("result"):
            balance = int(r1["result"], 16) / 1e18

        # Tx count
        r2 = _rpc_call({"jsonrpc":"2.0","id":2,
                         "method":"eth_getTransactionCount","params":[addr,"latest"]})
        if r2.get("result"):
            tx_count = int(r2["result"], 16)

        # Contract check
        r3 = _rpc_call({"jsonrpc":"2.0","id":3,
                         "method":"eth_getCode","params":[addr,"latest"]})
        code = r3.get("result", "0x")
        is_contract = code not in ("0x", "0x0", None) and len(code) > 2

        available = True

    except Exception as e:
        error = str(e)

    profile = _synthesize_profile(addr, balance, tx_count, is_contract) if available else None

    return WalletResponse(
        address=      addr,
        balance_pros= balance,
        tx_count=     tx_count,
        is_contract=  is_contract,
        profile=      profile,
        available=    available,
        explorer_url= PHAROS_EXPLORER_URL + "/address/" + addr,
        error=        error,
    )


# ─────────────────────────────────────────────
# TRANSACTION EXPLAINER SKILL
# ─────────────────────────────────────────────

class TxRequest(BaseModel):
    tx_hash: str

    class Config:
        json_schema_extra = {
            "example": {"tx_hash": "0xabc123...66-character-hash"}
        }


class TxResponse(BaseModel):
    tx_hash:         str
    from_addr:       str | None
    to_addr:         str | None
    value_pros:      float | None
    gas_used:        int | None
    gas_price_gwei:  float | None
    status:          str | None
    block_number:    int | None
    is_contract_call:bool
    explanation:     dict | None
    available:       bool
    explorer_url:    str
    error:           str | None = None


def _explain_tx(tx_data: dict) -> dict:
    """Call Gemini to explain a transaction in plain language."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _deterministic_tx_explain(tx_data)
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.3,
            google_api_key=api_key,
        )
        prompt = (
            "You are OctoBot's transaction explainer for Pharos Network. "
            "Based on this read-only, publicly-verifiable transaction data, "
            "write a SHORT (2-3 sentence) plain-language explanation that a "
            "non-technical person could understand — what happened, and why "
            "it likely happened. Then classify it into one short category label.\n\n"
            f"From: {tx_data.get('from_addr')}\n"
            f"To: {tx_data.get('to_addr')}\n"
            f"Value: {tx_data.get('value_pros')} PROS\n"
            f"Status: {tx_data.get('status')}\n"
            f"Is contract call: {tx_data.get('is_contract_call')}\n"
            f"Gas used: {tx_data.get('gas_used')}\n\n"
            "Return ONLY valid JSON, no markdown fences:\n"
            '{"summary":"...","category":"...","plain_steps":["step1","step2","step3"]}'
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw  = re.sub(r"^```(?:json)?\n?", "", resp.content.strip(), flags=re.IGNORECASE)
        raw  = re.sub(r"\n?```$", "", raw)
        parsed = json.loads(raw)
        if all(k in parsed for k in ("summary", "category", "plain_steps")):
            return parsed
    except Exception:
        pass
    return _deterministic_tx_explain(tx_data)


def _deterministic_tx_explain(tx_data: dict) -> dict:
    status = tx_data.get("status")
    status_label = (
        "completed successfully" if status == "success" else
        "failed"                 if status == "failed"  else
        "is still pending"
    )
    value = tx_data.get("value_pros")
    kind  = "a smart contract interaction" if tx_data.get("is_contract_call") else "a simple PROS transfer"
    parts = [f"This transaction {status_label} and was {kind}."]
    if value is not None and value > 0:
        parts.append(f"It moved {value:.6f} PROS.")
    if tx_data.get("gas_used"):
        parts.append(f"It consumed {tx_data['gas_used']:,} gas units.")
    return {
        "summary":     " ".join(parts),
        "category":    "Contract Call" if tx_data.get("is_contract_call") else "Transfer",
        "plain_steps": [
            f"Sent from {(tx_data.get('from_addr') or 'unknown')[:10]}…",
            f"Received by {(tx_data.get('to_addr') or 'contract creation')[:10]}…",
            f"Status: {status_label}",
        ],
    }


@app.post("/explain-tx", response_model=TxResponse, tags=["On-Chain"])
def explain_tx(request: TxRequest):
    """
    Plain-language transaction explanation.

    Reads a Pharos transaction by hash via public RPC:
    - Sender, recipient, value, gas, status, block
    - Detects contract calls vs plain transfers

    Then generates a plain-language explanation via Gemini
    (with deterministic fallback if AI is unavailable).
    Read-only · No signature · Zero gas · No funds accessed.
    """
    tx_h = request.tx_hash.strip()
    if not (tx_h.startswith("0x") and len(tx_h) == 66):
        raise HTTPException(
            status_code=400,
            detail="Invalid tx hash — must be 0x... (66 characters)"
        )

    result = {
        "tx_hash": tx_h, "from_addr": None, "to_addr": None,
        "value_pros": None, "gas_used": None, "gas_price_gwei": None,
        "status": None, "block_number": None, "is_contract_call": False,
        "available": False, "error": None,
    }

    try:
        # Transaction details
        r1 = _rpc_call({"jsonrpc":"2.0","id":1,
                         "method":"eth_getTransactionByHash","params":[tx_h]})
        tx = r1.get("result")
        if not tx:
            return TxResponse(
                **result,
                explanation=None,
                explorer_url=PHAROS_EXPLORER_URL + "/tx/" + tx_h,
                error="Transaction not found on Pharos — check the hash.",
                available=True,
            )

        result["from_addr"]    = tx.get("from")
        result["to_addr"]      = tx.get("to")
        if tx.get("value"):
            result["value_pros"] = int(tx["value"], 16) / 1e18
        if tx.get("gasPrice"):
            result["gas_price_gwei"] = int(tx["gasPrice"], 16) / 1e9
        if tx.get("blockNumber"):
            result["block_number"] = int(tx["blockNumber"], 16)
        input_data = tx.get("input", "0x")
        result["is_contract_call"] = (
            input_data not in ("0x", "0x0", None) and len(input_data) > 2
        )

        # Receipt
        r2 = _rpc_call({"jsonrpc":"2.0","id":2,
                         "method":"eth_getTransactionReceipt","params":[tx_h]})
        receipt = r2.get("result")
        if receipt:
            s = receipt.get("status")
            result["status"]   = "success" if s == "0x1" else "failed" if s else None
            if receipt.get("gasUsed"):
                result["gas_used"] = int(receipt["gasUsed"], 16)

        result["available"] = True

    except Exception as e:
        result["error"] = str(e)

    explanation = _explain_tx(result) if result["available"] else None

    return TxResponse(
        tx_hash=          result["tx_hash"],
        from_addr=        result["from_addr"],
        to_addr=          result["to_addr"],
        value_pros=       result["value_pros"],
        gas_used=         result["gas_used"],
        gas_price_gwei=   result["gas_price_gwei"],
        status=           result["status"],
        block_number=     result["block_number"],
        is_contract_call= result["is_contract_call"],
        explanation=      explanation,
        available=        result["available"],
        explorer_url=     PHAROS_EXPLORER_URL + "/tx/" + tx_h,
        error=            result.get("error"),
    )