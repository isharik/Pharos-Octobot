"""
app.py — OctoBot · Pharos Network Hub
======================================
Full website experience with multiple sections:
  Home       — animated welcome, live price, quick links
  Chat       — OctoBot AI assistant (docs + fallback)
  Campaigns  — Active Campaigns section (live data)
  Updates    — Pharos News & active updates
  Trade      — CEX trade links for PROS

Architecture: single-page with st.session_state["page"] router.
All CSS in plain triple-quoted strings (no f-prefix).
"""

import os, time, base64, json, re, hashlib, urllib.parse, threading
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import html
from urllib.parse import urlparse

# ─────────────────────────────────────────────
# SECURITY HELPERS
# Validation + escaping used across the app. These constrain untrusted
# input (URL params, manual entry, remote API + LLM output) to safe
# shapes and escape text before it is placed into HTML. They do not
# change any feature behaviour for legitimate values.
# ─────────────────────────────────────────────
_ADDR_RE   = re.compile(r"^0x[0-9a-fA-F]{40}$")
_TXHASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")

def esc(x) -> str:
    """Escape any value before putting it in unsafe_allow_html / components.html."""
    return html.escape(str(x if x is not None else ""), quote=True)

def valid_addr(a):
    a = (a or "").strip()
    return a if _ADDR_RE.match(a) else None

def valid_txhash(h):
    h = (h or "").strip()
    return h if _TXHASH_RE.match(h) else None

def valid_amount(a):
    try:
        v = float(a)
        return v if 0 < v < 1e12 else None
    except (TypeError, ValueError):
        return None

def esc_url(u) -> str:
    u = (u or "").strip()
    p = urlparse(u)
    return esc(u) if p.scheme in ("http", "https") else "#"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="OctoBot · Pharos Hub",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="auto",
)

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
COINGECKO_ASSET_ID  = "pharos-network"
COINGECKO_PRICE_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=pharos-network&vs_currencies=usd"
    "&include_24hr_change=true&include_market_cap=true&include_24hr_vol=true"
)
COINGECKO_NEWS_URL = (
    "https://api.coingecko.com/api/v3/news"
)
PRICE_CACHE  = 300
CHART_CACHE  = 900
NEWS_CACHE   = 600

PHAROS_DOCS_URL    = "https://docs.pharos.xyz"
PHAROS_MAIN_URL    = "https://pharos.xyz"
PHAROS_DISCORD_URL = "https://discord.com/invite/pharos"
PHAROS_X_URL       = "https://x.com/pharos_network"

CEX_LINKS = [
    {"name": "OKX",      "url": "https://www.okx.com/trade-spot/pros-usdt?channelid=35427002",                 "desc": "PROS/USDT · Highest Volume", "logo": "https://www.google.com/s2/favicons?domain=okx.com&sz=64"},
    {"name": "Bitget",   "url": "https://www.bitget.com/spot/PROSUSDT?channelCode=y53z&vipCode=s3t2",          "desc": "PROS/USDT", "logo": "https://www.google.com/s2/favicons?domain=bitget.com&sz=64"},
    {"name": "KuCoin",   "url": "https://www.kucoin.com/trade/PROS-USDT?rcode=rPH7VCS",                        "desc": "PROS/USDT", "logo": "https://www.google.com/s2/favicons?domain=kucoin.com&sz=64"},
    {"name": "Upbit",    "url": "https://www.upbit.com/exchange?code=CRIX.UPBIT.KRW-PROS",                     "desc": "PROS/USDT · KRW · BTC", "logo": "https://www.google.com/s2/favicons?domain=upbit.com&sz=64"},
    {"name": "Coinbase", "url": "https://exchange.coinbase.com/trade/PROS-USD",                                "desc": "PROS/USDT", "logo": "https://www.google.com/s2/favicons?domain=coinbase.com&sz=64"},
]

CAMPAIGNS = [
     {
        "title": "Pharos X AnvitaFlow 🌊",
        "tag":   "LIVE · Ist Anniversary ",
        "desc":  "Community Co-Creation Campaign.",
        "link":  "https://port.pharos.xyz/agent-carnival/",
        "cta":   "Join",
        "color": "#1A1AFF",
        "logo":  "https://pbs.twimg.com/profile_images/2035669028132503552/q2Dd5GoS_400x400.png",
        "icon":  "🏆",
        "bg":    "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
    },

    {
        "title": "$PROS X Faroo ⚡",
        "tag":   "LIVE ·Pre Mint ",
        "desc":  "Earn before stPROS native yield goes live.",
        "link":  "https://app.faroo.xyz/pre-mint",
        "cta":   "Join",
        "color": "#1A1AFF",
        "logo":  "https://app.faroo.xyz/img/tokens/stPROS-dark.svg",
        "icon":  "🏆",
        "bg":    "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
    },
   {
        "title": "Create Like a PRO Phase 2",
        "tag":   "LIVE · Agent Carnival",
        "desc":  "Join the Alpha Summer. Build Skills. Launch Agents. Earn PROS",
        "link":  "https://port.pharos.xyz/agent-carnival/",
        "cta":   "Join",
        "color": "#1A1AFF",
        "logo":  "https://pbs.twimg.com/profile_images/2035669028132503552/q2Dd5GoS.png",
        "icon":  "🏆",
        "bg":    "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
    },
   {
        "title": "TopNod Million Cup",
        "tag":   "LIVE · Prediction",
        "desc":  "Predict the football winners and Earn $PROS",
        "link":  "https://topnod.com/",
        "cta":   "Join",
        "color": "#1A1AFF",
        "logo":  "https://pbs.twimg.com/profile_images/1953370784698937344/b7j3JHqn_400x400.jpg",
        "icon":  "🏆",
        "bg":    "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
    },
    
   {
        "title": "Pharos Inner Circle",
        "tag":   "# Make a Million, Become a PRO",
        "desc":  "Merit-based initiative designed to recognize and reward the most committed Pharos supporters",
        "link":  "https://app.notion.com/p/Pharos-Inner-Circle-Make-a-Million-Become-a-PRO-3808ec314f75806e960bcb15e147c10d",
        "cta":   "Grow with Us",
        "color": "#1A1AFF",
        "logo":  "https://www.google.com/s2/favicons?domain=pharos.xyz&sz=64",
        "icon":  "👑",
        "bg":    "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
    },
  
    {
        "title": "Pharos Expedition Season 2",
        "tag":   "LIVE · Post Mainnet Voyage",
        "desc":  "Showcase your skills and support on X and Discord to participate.",
        "link":  "https://www.notion.so/Pharos-Expedition-Season-2-3578ec314f7580488f69ca722cc31cf9",
        "cta":   "Join here",
        "color": "#1A1AFF",
        "logo":  "https://www.google.com/s2/favicons?domain=pharos.xyz&sz=64",
        "icon":  "🚀",
        "bg":    "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
    },
    {
        "title": "Storyteller Program 2.0",
        "tag":   "LIVE · Content Creators",
        "desc":  "Create impactful educational content about Pharos and earn perks. Open to writers, educators, meme creators.",
        "link":  "https://silken-muskox-24e.notion.site/pharos-storyteller-program-2-0",
        "cta":   "Apply now",
        "color": "#1A1AFF",
        "logo":  "https://www.google.com/s2/favicons?domain=notion.so&sz=64",
        "icon":  "✍️",
        "bg":    "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
    },
    
]


PHAROS_DAPPS = [
    {
        "name":  "Faroswap",
        "cat":   ["DEX"],
        "desc":  "Native DEX on Pharos. Swap tokens with deep liquidity, low fees, and a points system that earns Pharos rewards.",
        "url":   "https://faroswap.xyz",
        "logo":  "https://www.google.com/s2/favicons?domain=faroswap.xyz&sz=64",
        "bg":    "#E8F4FF",
    },
    {
        "name":  "Bitverse",
        "cat":   ["Dex", "RWA", "Perp"],
        "desc":  "All-in-one RWA perp DEX bringing real-world assets and U.S. stock futures onto a single AI-powered trading platform.",
        "url":   "https://www.bitverse.zone",
        "logo":  "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQcd3T03MuTOTnv7Q173YWoQHibpIpDb33H-a-lAkDOBu88U7fpA5LHUgUO&s=10",
        "bg":    "#E8F0FF",
    },
    {
        "name":  "AquaFlux",
        "cat":   ["RWAfi"],
        "desc":  "RWA liquidity protocol with a Tri-Token model (P/C/S) — unlock structured real-world asset derivatives on-chain.",
        "url":   "https://www.aquaflux.pro/",
        "logo":  "https://www.google.com/s2/favicons?domain=aquaflux.pro&sz=64",
        "bg":    "#E8F8FF",
    },
    {
        "name":  "Asseto",
        "cat":   ["RWA", "RWAfi"],
        "desc":  "Top-tier RWA tokenization technology service platform, bridging traditional finance and DeFi for on-chain asset issuance.",
        "url":   "https://www.asseto.finance/",
        "logo":  "https://www.google.com/s2/favicons?domain=asseto.finance&sz=64",
        "bg":    "#FFF4E8",
    },
    {
        "name":  "AutoStaking",
        "cat":   ["Stake", "Yield"],
        "desc":  "AI-powered stablecoin yield aggregator. Deposit testnet stablecoins and let AI optimize yield — ~10% APY on testnet.",
        "url":   "https://testnet.pharosnetwork.xyz",
        "logo":  "https://www.google.com/s2/favicons?domain=pharosnetwork.xyz&sz=64",
        "bg":    "#F0FFE8",
    },
    {
        "name":  "Brokex",
        "cat":   ["Trade", "CFD"],
        "desc":  "First fully on-chain CFD exchange (CLOB) on Pharos. Trade forex, gold, and derivatives powered by Supra Oracle.",
        "url":   "https://brokex.trade/",
        "logo":  "https://www.google.com/s2/favicons?domain=brokex.trade&sz=64",
        "bg":    "#F8E8FF",
    },
    {
        "name":  "ZAN",
        "cat":   ["RPC", "Infra", "Tools"],
        "desc":  "A Suite of Plug-And-Play Tools and Services for Web3 Endeavors.",
        "url":   "https://zan.top/",
        "logo":  "https://www.google.com/s2/favicons?domain=zan.top&sz=64",
        "bg":    "#F8E8FF",
    },
    {
        "name":  "OpenFi",
        "cat":   ["Lend & Borrow"],
        "desc":  "RWA-backed lending protocol supporting tokenized US stocks, gold, and money market funds as collateral for stablecoin liquidity.",
        "url":   "https://app.open-fi.xyz/",
        "logo":  "https://www.google.com/s2/favicons?domain=app.open-fi.xyz&sz=64",
        "bg":    "#E8FFF4",
    },
    {
        "name":  "Zenith",
        "cat":   ["Lend & Borrow"],
        "desc":  "Yield-optimized lending and borrowing platform with institutional-grade risk management built natively on Pharos.",
        "url":   "https://testnet.zenithfinance.xyz/home",
        "logo":  "https://pbs.twimg.com/profile_images/1912204746074501120/u7tIPl9T_400x400.jpg",
        "bg":    "#FFFAE8",
    },
    {
        "name":  "Fiamma",
        "cat":   ["Bridge"],
        "desc":  "Trust-minimised Bitcoin bridge leveraging BitVM2 and zero-knowledge proofs. Move BTC onto Pharos securely on-chain.",
        "url":   "https://www.fiammalabs.io/",
        "logo":  "https://www.google.com/s2/favicons?domain=fiammalabs.io&sz=64",
        "bg":    "#FFE8E8",
    },
    
    {
        "name":  "Buzzing Club",
        "cat":   ["Prediction Market"],
        "desc":  "Trade your opinion on any trending topic — politics, sports, entertainment, business, crypto, and breaking news.",
        "url":   "https://testnet.pharosnetwork.xyz",
        "logo":  "https://www.google.com/s2/favicons?domain=pharosnetwork.xyz&sz=64",
        "bg":    "#FFF0E8",
    },
    {
        "name":  "PNS",
        "cat":   ["Identity", "Wallet"],
        "desc":  "Pharos Name Service — register human-readable wallet identities (yourname.pharos) on the Pharos network.",
        "url":   "https://test.pharosname.com/",
        "logo":  "https://www.google.com/s2/favicons?domain=test.pharosname.com&sz=64",
        "bg":    "#E8F8F0",
    },
    {
        "name":  "Spout Finance",
        "cat":   ["RWAfi"],
        "desc":  "Transforms collateral in DeFi using predictable real-world yield-bearing assets with seamless redemption mechanisms.",
        "url":   "https://www.spout.finance/",
        "logo":  "https://images.cryptorank.io/coins/150x150.spout_finance1776399650650.png",
        "bg":    "#E8F0F8",
    },
    {
        "name":  "TopNod",
        "cat":   ["RWAfi"],
        "desc":  "A simple, secure self-custody wallet for managing RWA and other digital assets.",
        "url":   "https://topnod.com/",
        "logo":  "https://www.google.com/s2/favicons?domain=topnod.com&sz=64",
        "bg":    "#F8F0E8",
    },
]
# ─────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────
if "page"            not in st.session_state: st.session_state.page            = "home"
if "messages"        not in st.session_state: st.session_state.messages        = []
if "sources_history" not in st.session_state: st.session_state.sources_history = []
if "show_sources"    not in st.session_state: st.session_state.show_sources    = True
if "voice_reply"     not in st.session_state: st.session_state.voice_reply     = False
if "chat_mode"       not in st.session_state: st.session_state.chat_mode       = "docs"
if "octobot_lang"    not in st.session_state: st.session_state.octobot_lang    = "English"
if "build_path_goal" not in st.session_state: st.session_state.build_path_goal = None
if "build_path_data" not in st.session_state: st.session_state.build_path_data = None
if "sailor_name"     not in st.session_state: st.session_state.sailor_name     = ""
if "sailor_done"     not in st.session_state: st.session_state.sailor_done     = False
if "wallet_address"  not in st.session_state: st.session_state.wallet_address  = ""
if "w3_address"      not in st.session_state: st.session_state.w3_address      = ""     # live EIP-1193 account
if "w3_chain"        not in st.session_state: st.session_state.w3_chain        = ""     # hex chain id
if "w3_label"        not in st.session_state: st.session_state.w3_label        = ""     # wallet name
if "wallet_data"     not in st.session_state: st.session_state.wallet_data     = None
if "wallet_profile"  not in st.session_state: st.session_state.wallet_profile  = None
if "wallet_loading"  not in st.session_state: st.session_state.wallet_loading  = False
if "tx_hash_input"   not in st.session_state: st.session_state.tx_hash_input   = ""
if "tx_data"         not in st.session_state: st.session_state.tx_data         = None
if "tx_explanation"  not in st.session_state: st.session_state.tx_explanation  = None
if "pay_intent_raw"  not in st.session_state: st.session_state.pay_intent_raw  = ""
if "pay_parsed"      not in st.session_state: st.session_state.pay_parsed      = None
if "pay_confirmed"   not in st.session_state: st.session_state.pay_confirmed   = False
if "pay_result"      not in st.session_state: st.session_state.pay_result      = None
if "pay_history"     not in st.session_state: st.session_state.pay_history     = []
if "pay_network"     not in st.session_state: st.session_state.pay_network     = "mainnet"
if "req_invoices"    not in st.session_state: st.session_state.req_invoices    = []
if "req_draft"       not in st.session_state: st.session_state.req_draft       = None
if "net_stats_cache" not in st.session_state: st.session_state.net_stats_cache = {}
if "spn_filter"      not in st.session_state: st.session_state.spn_filter      = "all"
# ── x402 pay-per-call state ──
if "x402_enabled"    not in st.session_state: st.session_state.x402_enabled    = False   # premium mode toggle (free is default)
if "x402_challenge"  not in st.session_state: st.session_state.x402_challenge  = None    # active 402 challenge awaiting payment
if "x402_unlocked"   not in st.session_state: st.session_state.x402_unlocked   = {}      # resource_id -> verified tx hash
if "x402_receipts"   not in st.session_state: st.session_state.x402_receipts   = []      # list of settled premium calls
if "x402_payto"      not in st.session_state: st.session_state.x402_payto      = os.getenv("X402_PAYTO_ADDRESS", "")  # user-set receiving address

# Logo assistant bubble → navigate to chat
_goto = st.query_params.get("goto", "")
if _goto == "chat":
    st.session_state.page = "chat"
    st.query_params.clear()

# Wallet connect widget → navigate back with address
_wallet = valid_addr(st.query_params.get("wallet", ""))
if _wallet and _wallet.lower() != st.session_state.wallet_address.lower():
    st.session_state.wallet_address = _wallet
    st.session_state.wallet_data    = None
    st.session_state.wallet_profile = None
    st.session_state.page = "memory"
    st.query_params.clear()

# ── Global EIP-1193 wallet bridge (browser → Python) ──────────
# The connect button lives in the parent document and talks to the real
# injected provider (MetaMask / OKX / Rabby / Coinbase / any EVM wallet).
# It reports state back by setting query params and re-running the app.
# Only well-formed values are accepted; everything is validated here.
_w3_addr  = valid_addr(st.query_params.get("w3_addr", ""))
_w3_chain = st.query_params.get("w3_chain", "")[:12]
_w3_label = st.query_params.get("w3_label", "")[:24]
_w3_act   = st.query_params.get("w3_act", "")[:12]

if _w3_act == "disconnect":
    st.session_state.w3_address = ""
    st.session_state.w3_chain   = ""
    st.session_state.w3_label   = ""
    st.query_params.clear()
elif _w3_addr:
    _changed = (_w3_addr.lower() != (st.session_state.w3_address or "").lower()
                or _w3_chain != st.session_state.w3_chain)
    if _changed:
        st.session_state.w3_address = _w3_addr
        st.session_state.w3_chain   = _w3_chain if re.match(r"^0x[0-9a-fA-F]{1,8}$", _w3_chain or "") else ""
        st.session_state.w3_label   = re.sub(r"[^A-Za-z0-9 ]", "", _w3_label or "") or "Wallet"
        # A connected wallet is the app's single source of identity: keep
        # the read-only address views in sync so every page agrees.
        st.session_state.wallet_address = _w3_addr
        st.session_state.wallet_data    = None
        st.session_state.wallet_profile = None
        st.query_params.clear()

# ── Incoming payment-request link handler ─────────────────────────────────
_req_to   = valid_addr(st.query_params.get("req_to", ""))
_req_amt  = valid_amount(st.query_params.get("req_amt", ""))
_req_for  = esc(st.query_params.get("req_for", "")[:120])
_req_from = valid_addr(st.query_params.get("req_from", "")) or ""
_req_net  = st.query_params.get("req_net", "mainnet")
if _req_net not in ("mainnet", "testnet"):
    _req_net = "mainnet"
if _req_to and _req_amt is not None:
    st.session_state.page      = "request"
    st.session_state.req_draft = {
        "to":      _req_to,
        "amount":  str(_req_amt),
        "note":    _req_for,
        "from":    _req_from,
        "network": _req_net,
        "mode":    "pay_invoice",
    }
    st.query_params.clear()
    

# Voice query from mic widget
_voice_q = st.query_params.get("voice_q", "")[:300]
if _voice_q:
    st.session_state["pending_q"] = _voice_q
    st.session_state.page = "chat"
    st.query_params.clear()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_logo_b64() -> str:
    for path, mime in [("pharos_logo.jpg","image/jpeg"),("pharos_logo.png","image/png")]:
        if os.path.exists(path):
            with open(path,"rb") as f:
                return "data:"+mime+";base64,"+base64.b64encode(f.read()).decode()
    return ""

def get_pros_price() -> dict:
    now    = time.time()
    cached = st.session_state.get("pros_price_cache", {})
    if cached and now - cached.get("fetched_at", 0) < PRICE_CACHE:
        return cached
    try:
        r = requests.get(COINGECKO_PRICE_URL, timeout=5, headers={"Accept":"application/json"})
        r.raise_for_status()
        data = r.json().get(COINGECKO_ASSET_ID, {})
        if not data: raise ValueError("Empty")
        result = {
            "price_usd": data.get("usd"), "market_cap_usd": data.get("usd_market_cap"),
            "volume_24h": data.get("usd_24h_vol"), "change_24h": data.get("usd_24h_change"),
            "last_updated": datetime.now(timezone.utc).strftime("%H:%M UTC"),
            "fetched_at": now, "available": True, "error": None,
        }
    except Exception as e:
        prev   = st.session_state.get("pros_price_cache", {})
        result = {k: prev.get(k) for k in ["price_usd","market_cap_usd","volume_24h","change_24h","last_updated"]}
        result.update({"fetched_at": now, "available": False, "error": str(e)})
    st.session_state["pros_price_cache"] = result
    return result

def get_pharos_news() -> list:
    now    = time.time()
    cached = st.session_state.get("pharos_news_cache", {})
    if cached.get("items") and now - cached.get("fetched_at", 0) < NEWS_CACHE:
        return cached["items"]
    items = []
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/news",
            params={"category": "pharos-network"},
            timeout=6, headers={"Accept":"application/json"}
        )
        if r.status_code == 200:
            data = r.json()
            raw  = data if isinstance(data, list) else data.get("data", [])
            for art in raw[:8]:
                items.append({
                    "title":       art.get("title", ""),
                    "description": art.get("description", ""),
                    "url":         art.get("url", "#"),
                    "thumb":       art.get("thumb_2x", ""),
                    "source":      art.get("news_site", ""),
                    "date":        art.get("updated_at", ""),
                })
    except Exception:
        pass
    st.session_state["pharos_news_cache"] = {"items": items, "fetched_at": now}
    return items

# ─────────────────────────────────────────────
# LIVE X (TWITTER) FEED — @pharos_network
# Layered sources, all read-only and rate-limit friendly:
#   1. Official X API v2 (if X_BEARER_TOKEN / TWITTER_BEARER_TOKEN is
#      configured in env or st.secrets) — post text, timestamp, media.
#   2. Public Nitter RSS mirrors (no key required).
#   3. Curated latest-known official updates as a graceful fallback so
#      the Updates page is never empty.
# Cached briefly so the feed refreshes automatically.
# ─────────────────────────────────────────────
X_FEED_CACHE     = 120          # seconds — feed auto-refreshes
PHAROS_X_HANDLE  = "pharos_network"
PHAROS_X_AVATAR  = "https://pbs.twimg.com/profile_images/2005491865450430464/ta6znFqT_400x400.jpg"
_NITTER_MIRRORS  = [
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacyredirect.com",
    "https://nitter.tiekoetter.com",
]

def _x_bearer_token():
    for k in ("X_BEARER_TOKEN", "TWITTER_BEARER_TOKEN"):
        v = os.environ.get(k)
        if v:
            return v.strip()
    try:
        for k in ("X_BEARER_TOKEN", "TWITTER_BEARER_TOKEN"):
            v = st.secrets.get(k)
            if v:
                return str(v).strip()
    except Exception:
        pass
    return None

def _x_rel_time(dt):
    """'2h ago' style relative timestamp (UTC-safe)."""
    try:
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        s = max(0, int((now - dt).total_seconds()))
        if s < 60:        return "just now"
        if s < 3600:      return f"{s // 60}m ago"
        if s < 86400:     return f"{s // 3600}h ago"
        if s < 86400 * 7: return f"{s // 86400}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return ""

def _fetch_x_api_v2(token) -> list:
    """Official X API v2 — most reliable when a bearer token is set."""
    h = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    uid = st.session_state.get("_pharos_x_uid")
    if not uid:
        r = requests.get(
            "https://api.twitter.com/2/users/by/username/" + PHAROS_X_HANDLE,
            headers=h, timeout=8,
        )
        r.raise_for_status()
        uid = r.json().get("data", {}).get("id")
        if not uid:
            return []
        st.session_state["_pharos_x_uid"] = uid
    r = requests.get(
        f"https://api.twitter.com/2/users/{uid}/tweets",
        params={
            "max_results": "10",
            "exclude": "replies",
            "tweet.fields": "created_at,text",
            "expansions": "attachments.media_keys",
            "media.fields": "url,preview_image_url,type",
        },
        headers=h, timeout=8,
    )
    r.raise_for_status()
    body   = r.json()
    media  = {m.get("media_key"): (m.get("url") or m.get("preview_image_url") or "")
              for m in body.get("includes", {}).get("media", [])}
    items  = []
    for t in body.get("data", []) or []:
        tid = t.get("id", "")
        try:
            dt = datetime.fromisoformat((t.get("created_at") or "").replace("Z", "+00:00"))
        except Exception:
            dt = None
        keys  = (t.get("attachments") or {}).get("media_keys") or []
        thumb = next((media.get(k) for k in keys if media.get(k)), "")
        items.append({
            "text":  t.get("text", ""),
            "url":   f"https://x.com/{PHAROS_X_HANDLE}/status/{tid}",
            "media": thumb,
            "dt":    dt,
            "rel":   _x_rel_time(dt) if dt else "",
        })
    return items

def _fetch_nitter_rss() -> list:
    """Key-free fallback: parse the public Nitter RSS mirror of the account."""
    import xml.etree.ElementTree as ET
    from email.utils import parsedate_to_datetime
    for base in _NITTER_MIRRORS:
        try:
            r = requests.get(
                f"{base}/{PHAROS_X_HANDLE}/rss", timeout=6,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/rss+xml,application/xml"},
            )
            if r.status_code != 200 or "<rss" not in r.text[:2000]:
                continue
            root  = ET.fromstring(r.text)
            items = []
            for it in root.iter("item"):
                title = (it.findtext("title") or "").strip()
                link  = (it.findtext("link") or "").strip()
                desc  = it.findtext("description") or ""
                pub   = it.findtext("pubDate") or ""
                # Rewrite the mirror link back to the original X post
                try:
                    pr = urlparse(link)
                    link = "https://x.com" + pr.path.split("#")[0]
                except Exception:
                    pass
                m     = re.search(r'<img[^>]+src="([^"]+)"', desc)
                thumb = m.group(1) if m else ""
                try:
                    dt = parsedate_to_datetime(pub)
                except Exception:
                    dt = None
                items.append({
                    "text":  title,
                    "url":   link,
                    "media": thumb,
                    "dt":    dt,
                    "rel":   _x_rel_time(dt) if dt else "",
                })
                if len(items) >= 10:
                    break
            if items:
                return items
        except Exception:
            continue
    return []

# Curated latest-known official updates — shown only if every live
# source is unreachable, so the section never dead-ends.
_PHAROS_X_FALLBACK = [
    {"text": "Excited to announce @Farooxyz as the FIRST project of the Pharos Incubator ⚓", "url": "https://x.com/pharos_network", "media": PHAROS_X_AVATAR, "dt": None, "rel": ""},
    {"text": "The next allocation window for pALPHA Stage 2 is almost here — following a fully subscribed $50M first round, the next opportunity opens July 10–16.", "url": "https://app.yieldnetwork.io/pharos-2/", "media": "https://res.cloudinary.com/dhkxvwmjd/image/upload/v1781750528/Pharos_onrmbe.jpg", "dt": None, "rel": ""},
    {"text": "Cross-chain access is expanding on Pharos — @StargateFinance now supports Pharos, enabling users to transfer and swap assets across EVM chains.", "url": "https://x.com/pharos_network/status/2067208187615576378", "media": "https://pbs.twimg.com/profile_images/1928147506699145217/n7-KQGNJ_400x400.png", "dt": None, "rel": ""},
    {"text": "Pharos is partnering with @avalonfinance and @FunctionBTC to expand Bitcoin utility within the Pharos ecosystem.", "url": "https://x.com/pharos_network/status/2066993885784822019", "media": "https://pbs.twimg.com/profile_images/1874986577774145536/Uvumm1eb_400x400.jpg", "dt": None, "rel": ""},
    {"text": "The Builders Harbor on Pharos has been upgraded — new tools, templates, and technical resources.", "url": "https://www.pharos.xyz/devhub", "media": "https://www.google.com/s2/favicons?domain=pharos.xyz&sz=64", "dt": None, "rel": ""},
    {"text": "Expedition Season 2 is ongoing — participate in the ecosystem.", "url": "https://discord.gg/pharos", "media": "https://www.google.com/s2/favicons?domain=discord.com&sz=64", "dt": None, "rel": ""},
    {"text": "Pharos x XLayer & OKX — fellow partners in bringing World Cup outcomes onchain.", "url": "https://x.com/pharos_network/status/2065362220851335650", "media": "https://www.google.com/s2/favicons?domain=okx.com&sz=64", "dt": None, "rel": ""},
    {"text": "Follow @pharos_network on X for announcements, ecosystem launches, partnerships, campaigns and protocol updates.", "url": "https://x.com/pharos_network", "media": PHAROS_X_AVATAR, "dt": None, "rel": ""},
]

_X_PRIORITY_TERMS = (
    "announc", "launch", "partner", "campaign", "protocol", "upgrade",
    "mainnet", "testnet", "incubator", "ecosystem", "integrat", "stake",
    "expedition", "live", "reward",
)

# ─────────────────────────────────────────────
# VERIFIED PHAROS MAINNET CONTRACTS
# Source of truth: the official Pharos documentation
#   · https://docs.pharos.xyz/getting-started/token-registry.md
#   · https://docs.pharos.xyz/getting-started/canonical-contracts.md
# Every address below is copied from those pages. Nothing here is
# guessed or inferred. If an address is not published by Pharos, it is
# NOT in this file — the corresponding feature deep-links to the
# official protocol UI instead of calling an unverified contract.
# ─────────────────────────────────────────────
PHAROS_TOKENS = [
    # (symbol, address, decimals, label)
    ("WPROS", "0x52c48d4213107b20bc583832b0d951fb9ca8f0b0", 18, "Wrapped PROS"),
    ("USDC",  "0xc879c018db60520f4355c26ed1a6d572cdac1815",  6, "USDC (Circle)"),
    ("WETH",  "0x1f4b7011Ee3d53969bb67F59428a9ec0477856E9", 18, "Wrapped ETH"),
    ("LINK",  "0x51e2A24742Db77604B881d6781Ee16B5b8fcBE29", 18, "Chainlink"),
]
MULTICALL3_ADDR = "0xcA11bde05977b3631167028862bE2a173976CA11"  # canonical
PERMIT2_ADDR    = "0x000000000022D473030F116dDEE9F6B43aC78BA3"  # canonical

# Official ecosystem destinations (verified from pharos.xyz / project sites).
PHAROS_PORT_URL      = "https://port.pharos.xyz"
PHAROS_ECOSYSTEM_URL = "https://port.pharos.xyz/ecosystem"
PHAROS_DEVHUB_URL    = "https://www.pharos.xyz/devhub"
PHAROS_BLOG_URL      = "https://www.pharos.xyz/resources"
FAROSWAP_URL         = "https://faroswap.xyz"
FAROSWAP_DOCS_URL    = "https://docs.faroswap.xyz"

# NOTE FOR FUTURE MAINTAINERS
# ---------------------------
# A PROS staking contract (stPROS) and a FaroSwap mainnet router are NOT
# published in the Pharos docs at the time of writing, and stPROS is
# described publicly as "not yet live". They are therefore intentionally
# absent. To enable native staking/swap transactions later, add the
# verified addresses here and implement the calls in the DeFi page —
# do not populate these from blog posts or third-party sites.
PROS_STAKING_ADDR = None   # ← set to the official address once published
FAROSWAP_ROUTER   = None   # ← set to the official address once published


def get_pharos_x_posts() -> list:
    """Latest posts from the official Pharos Network X account.
    Live-source layered fetch, briefly cached, official-news-first."""
    now    = time.time()
    cached = st.session_state.get("pharos_x_cache", {})
    if cached.get("items") and now - cached.get("fetched_at", 0) < X_FEED_CACHE:
        return cached["items"]

    items, live = [], False
    token = _x_bearer_token()
    if token:
        try:
            items = _fetch_x_api_v2(token)
        except Exception:
            items = []
    if not items:
        items = _fetch_nitter_rss()
    live = bool(items)
    if not items:
        # Keep serving the previous good fetch if the network blips.
        prev = cached.get("items")
        if prev:
            st.session_state["pharos_x_cache"] = {"items": prev, "fetched_at": now, "live": cached.get("live", False)}
            return prev
        items = list(_PHAROS_X_FALLBACK)

    # Prioritise official announcements / launches / partnerships /
    # campaigns / protocol updates (stable sort keeps recency order).
    def _prio(p):
        t = (p.get("text") or "").lower()
        return 0 if any(k in t for k in _X_PRIORITY_TERMS) else 1
    items = sorted(items, key=_prio)

    st.session_state["pharos_x_cache"] = {"items": items, "fetched_at": now, "live": live}
    return items

# ─────────────────────────────────────────────
# LIVE RWA MARKET SNAPSHOT — public CoinGecko, cached, key-free
# ─────────────────────────────────────────────
RWA_CACHE  = 300
RWA_ASSETS = [
    ("ondo-finance", "ONDO",  "Ondo Finance",   "Tokenised treasuries"),
    ("pax-gold",     "PAXG",  "Pax Gold",       "Tokenised gold"),
    ("centrifuge",   "CFG",   "Centrifuge",     "Private credit RWA"),
    ("maple",        "SYRUP", "Maple Finance",  "Institutional credit"),
    ("goldfinch",    "GFI",   "Goldfinch",      "RWA lending"),
    ("pharos-network","PROS", "Pharos Network", "RWA-native L1"),
]

def fetch_rwa_market() -> dict:
    now    = time.time()
    cached = st.session_state.get("rwa_market_cache", {})
    if cached.get("rows") and now - cached.get("fetched_at", 0) < RWA_CACHE:
        return cached
    rows = []
    try:
        ids = ",".join(a[0] for a in RWA_ASSETS)
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ids, "vs_currencies": "usd",
                    "include_24hr_change": "true", "include_market_cap": "true"},
            timeout=6, headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        for cid, sym, name, tag in RWA_ASSETS:
            d = data.get(cid) or {}
            if d.get("usd") is None:
                continue
            rows.append({"sym": sym, "name": name, "tag": tag,
                         "price": d.get("usd"),
                         "chg": d.get("usd_24h_change"),
                         "mcap": d.get("usd_market_cap")})
    except Exception:
        rows = cached.get("rows", [])
    out = {"rows": rows, "fetched_at": now,
           "as_of": datetime.now(timezone.utc).strftime("%H:%M UTC")}
    st.session_state["rwa_market_cache"] = out
    return out

def get_price_chart_df(days: str = "1"):
    now       = time.time()
    cache_all = st.session_state.get("pros_chart_cache", {})
    cached    = cache_all.get(days, {})
    if cached.get("df") is not None and now - cached.get("fetched_at", 0) < CHART_CACHE:
        return cached["df"]
    try:
        url = ("https://api.coingecko.com/api/v3/coins/" + COINGECKO_ASSET_ID +
               "/market_chart?vs_currency=usd&days=" + days)
        r = requests.get(url, timeout=5, headers={"Accept":"application/json"})
        r.raise_for_status()
        prices = r.json().get("prices", [])
        if not prices: raise ValueError("Empty")
        df = pd.DataFrame(prices, columns=["time","price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")
        cache_all[days] = {"df": df, "fetched_at": now}
        st.session_state["pros_chart_cache"] = cache_all
        return df
    except Exception:
        return cached.get("df")

def render_price_chart(df, chart_key="chart", days="1"):
    if df is None or df.empty:
        st.markdown('<div style="font-size:11px;color:#9499A8;padding:0.4rem 0;">Chart unavailable.</div>', unsafe_allow_html=True)
        return
    tick_format  = "%H:%M"     if days == "1" else ("%b %d" if days in ("7","30") else "%b %Y")
    hover_format = "$%{y:.4f}<br>%{x|%H:%M}<extra></extra>" if days=="1" else "$%{y:.4f}<br>%{x|%b %d, %Y}<extra></extra>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["price"], mode="lines",
        line=dict(color="#1A1AFF", width=2, shape="spline", smoothing=0.4),
        fill="tozeroy", fillcolor="rgba(26,26,255,0.10)",
        hovertemplate=hover_format, name="PROS",
    ))
    fig.update_layout(
        height=180, margin=dict(l=0,r=0,t=6,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False, hovermode="x unified",
        font=dict(family="DM Sans,sans-serif", color="#5B5F6E", size=10),
        xaxis=dict(showgrid=False, showline=False, tickfont=dict(size=9,color="#9499A8"), tickformat=tick_format, nticks=5),
        yaxis=dict(showgrid=True, gridcolor="rgba(20,20,31,0.05)", griddash="dot",
                   showline=False, tickfont=dict(size=9,color="#9499A8"), tickprefix="$", tickformat=".4f", side="right"),
        hoverlabel=dict(bgcolor="#F7F8FA", font_color="#14141F", bordercolor="#D6D9E0"),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False}, key=chart_key)

def speak_text(text: str) -> None:
    import json as _json, re as _re
    clean = text
    clean = _re.sub(r"^\|.*\|\s*$","",clean,flags=_re.MULTILINE)
    clean = _re.sub(r"^[\s|:-]+$","",clean,flags=_re.MULTILINE)
    clean = _re.sub(r"^#{1,6}\s*","",clean,flags=_re.MULTILINE)
    clean = _re.sub(r"^\s*[-*•]\s+","",clean,flags=_re.MULTILINE)
    clean = _re.sub(r"[*_`]","",clean)
    clean = _re.sub(r"\[([^\]]+)\]\([^)]+\)",r"\1",clean)
    clean = _re.sub(r"https?://\S+","",clean)
    clean = _re.sub(r"\s+"," ",clean).strip()
    safe  = _json.dumps(clean)
    components.html(
        "<script>(function(){"
        "try{"
        "const s=window.parent.speechSynthesis;"
        "const t=" + safe + ";"
        "const lang=navigator.language||'en-US';"
        "function pick(vv){"
        "const lp=lang.split('-')[0].toLowerCase();"
        "const pool=vv.filter(v=>v.lang.toLowerCase().startsWith(lp));"
        "const p=pool.length?pool:vv;"
        "for(const kw of['natural','neural','premium','enhanced','google','wavenet','studio']){"
        "const m=p.find(v=>v.name.toLowerCase().includes(kw));"
        "if(m)return m;}"
        "return p[0]||null;}"
        "function speak(){"
        "const vv=s.getVoices();"
        "const u=new SpeechSynthesisUtterance(t);"
        "const v=pick(vv);"
        "if(v){u.voice=v;u.lang=v.lang;}else{u.lang=lang;}"
        "u.rate=0.95;u.pitch=1.0;u.volume=1.0;"
        "s.cancel();s.speak(u);}"
        "if(s.getVoices().length===0){s.onvoiceschanged=speak;}else{speak();}"
        "}catch(e){}})()</script>",
        height=0,
    )


def get_followup_questions(question: str, answer: str) -> list:
    """Generate 3 follow-up questions using Gemini based on the Q&A."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return []
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.4,
            google_api_key=api_key,
        )
        prompt = (
            "Based on this question and answer about Pharos blockchain, "
            "generate exactly 3 short follow-up questions the user might want to ask next. "
            "Each question should be concise (max 8 words), directly related to the topic, "
            "and progressively deeper. Return ONLY the 3 questions, one per line, "
            "no numbers, no bullets, no extra text.\n\n"
            "Question: " + question + "\n\n"
            "Answer: " + answer[:800]
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        lines = [l.strip() for l in resp.content.strip().split("\n") if l.strip()]
        return lines[:3]
    except Exception:
        return []


def get_image_search_results(query: str) -> list:
    """
    Returns 3 relevant image URLs using Unsplash Source API.
    No API key needed — uses topic-based URL construction.
    Falls back to different seeds if one fails.
    """
    import hashlib
    # Clean query for URL — keep only alphanumeric and spaces
    clean = re.sub(r"[^a-zA-Z0-9 ]", "", query).strip()
    words = clean.split()[:4]  # take first 4 meaningful words
    topic = "+".join(words) if words else "blockchain"

    seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16) % 9000 + 1000

    images = []
    for i in range(3):
        # Unsplash Source — free, no API key, returns a real relevant image
        url = f"https://source.unsplash.com/400x220/?{topic},technology,finance&sig={seed + i * 97}"
        images.append({"url": url, "title": f"{query} — {i+1}"})
    return images


def render_qr_code(data: str, size: int = 168, key: str = "qr") -> None:
    """
    Render a QR code for `data` (display-only) using a client-side QR library
    loaded from a CDN. No Python dependency; degrades to a link if the script
    is unavailable. Used to make a generated payment-request link scannable.
    """
    safe = json.dumps(str(data))  # safely embed into JS as a quoted string
    _h = int(size) + 8
    html = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  *{margin:0;padding:0;box-sizing:border-box;}
  body{background:transparent;display:flex;justify-content:center;}
  #qr{display:flex;align-items:center;justify-content:center;}
  #qr img,#qr canvas{display:block;border-radius:6px;}
  #fb{font-family:'Inter',system-ui,sans-serif;font-size:11px;color:#68738C;
      text-align:center;padding:10px;}
</style></head><body>
<div id="qr"></div>
<script src="https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js"></script>
<script>
  (function(){
    var data = __DATA__;
    var el = document.getElementById('qr');
    function fallback(){ el.innerHTML = '<div id="fb">QR unavailable — use the copy link below.</div>'; }
    try{
      if (typeof QRCode === 'undefined'){ fallback(); return; }
      new QRCode(el, { text: data, width: __SZ__, height: __SZ__,
        colorDark:'#0B1020', colorLight:'#FFFFFF',
        correctLevel: QRCode.CorrectLevel.M });
    }catch(e){ fallback(); }
  })();
</script></body></html>"""
    html = html.replace("__DATA__", safe).replace("__SZ__", str(int(size)))
    components.html(html, height=_h, scrolling=False)


def render_copy_share_download(text: str, btn_key: str) -> None:
    """
    Renders Copy (shows pre-selected textarea), Share on X, and Download buttons.
    Copy shows a pre-selected textarea — user just presses Ctrl+C.
    Guaranteed to work in every browser inside Streamlit iframes.
    """
    import json as _j, base64 as _b64

    safe_text  = _j.dumps(text)
    tweet_text = _j.dumps(
        "From OctoBot on Pharos: " + text[:220] + "... @pharos_network #Pharos #BuildOnPharos"
    )
    b64_text = _b64.b64encode(text.encode()).decode()

    btn_style = (
        "display:inline-flex;align-items:center;gap:5px;"
        "font-size:11px;font-weight:600;"
        "padding:5px 12px;border-radius:8px;"
        "border:1px solid #D0D3E0;background:#FFFFFF;"
        "color:#0C0C1A;cursor:pointer;"
        "font-family:'DM Sans',sans-serif;"
        "text-decoration:none;white-space:nowrap;"
    )

    components.html(
        f"""
        <div style="font-family:'DM Sans',sans-serif;">

          <!-- action row -->
          <div style="display:flex;gap:6px;flex-wrap:wrap;padding:2px 0;margin-top:4px;">

            <!-- COPY button — shows a pre-selected textarea on click -->
            <button id="copybtn{btn_key}" style="{btn_style}"
              onclick="(function(){{
                var box = document.getElementById('copybox{btn_key}');
                if(box.style.display === 'none'){{
                  box.style.display = 'block';
                  box.select();
                  box.setSelectionRange(0, 99999);
                  var copied = false;
                  try{{
                    copied = document.execCommand('copy');
                  }}catch(e){{}}
                  if(copied){{
                    document.getElementById('copybtn{btn_key}').innerText = 'Copied!';
                    setTimeout(function(){{
                      document.getElementById('copybtn{btn_key}').innerText = 'Copy Answer';
                      box.style.display = 'none';
                    }}, 1500);
                  }} else {{
                    document.getElementById('copybtn{btn_key}').innerText = 'Press Ctrl+C';
                  }}
                }} else {{
                  box.style.display = 'none';
                  document.getElementById('copybtn{btn_key}').innerText = 'Copy Answer';
                }}
              }})()">
              Copy Answer
            </button>

            <!-- SHARE ON X -->
            <a href="#" style="{btn_style}"
              onclick="this.href='https://x.com/intent/tweet?text='+encodeURIComponent({tweet_text});return true;"
              target="_blank">
              Share on X
            </a>

            <!-- DOWNLOAD -->
            <a href="data:text/plain;base64,{b64_text}"
              download="octobot_answer.txt"
              style="{btn_style}">
              Download .txt
            </a>

          </div>

          <!-- pre-selected copy textarea (hidden until Copy clicked) -->
          <textarea id="copybox{btn_key}"
            style="display:none;width:100%;height:80px;margin-top:6px;
                   font-size:12px;font-family:'DM Sans',sans-serif;
                   border:1.5px solid #1A1AFF;border-radius:8px;padding:8px;
                   color:#0C0C1A;background:#F4F5FF;resize:none;"
            readonly>{text.replace('<', '&lt;').replace('>', '&gt;')}</textarea>

        </div>
        """,
        height=70,
    )


def render_source_sidebar(sources: list, key: str) -> None:
    """
    Renders an animated slide-in sources sidebar using components.html.
    Triggered by clicking a Sources button.
    """
    if not sources:
        return

    sources_html = "".join([
        f'<div class="source-item">'
        f'<div class="source-item-title">{esc(s["title"])}</div>'
        f'<a class="source-item-url" href="{esc_url(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["url"])}</a>'
        f'</div>'
        for s in sources
    ])

    components.html(
        """
        <style>
        #ssb-""" + key + """{
            position:fixed;top:0;right:-340px;height:100vh;width:320px;
            background:#F4F5F8;border-left:1px solid #D0D3E0;
            box-shadow:-8px 0 40px rgba(20,20,60,0.15);
            z-index:9998;overflow-y:auto;padding:1.2rem;
            transition:right 0.3s cubic-bezier(0.4,0,0.2,1);
            font-family:'DM Sans',sans-serif;
        }
        #ssb-""" + key + """.open{right:0!important;}
        .ssh{display:flex;align-items:center;justify-content:space-between;
            margin-bottom:1rem;padding-bottom:0.7rem;border-bottom:1px solid #D0D3E0;}
        .sst{font-family:Syne,sans-serif;font-size:14px;font-weight:700;color:#0C0C1A;}
        .ssc{cursor:pointer;font-size:18px;color:#7A7F96;width:26px;height:26px;
            display:flex;align-items:center;justify-content:center;
            border-radius:6px;background:#ECEEF4;border:none;}
        .si{background:#ECEEF4;border:1px solid #D0D3E0;border-left:3px solid #1A1AFF;
            border-radius:0 8px 8px 0;padding:0.6rem 0.8rem;margin-bottom:0.5rem;}
        .sit{font-size:12px;font-weight:600;color:#0C0C1A;margin-bottom:3px;}
        .siu{font-size:10px;color:#1A1AFF;word-break:break-all;text-decoration:none;}
        .siu:hover{text-decoration:underline;}
        #open-""" + key + """{
            display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;
            padding:5px 12px;border-radius:8px;border:1px solid #D0D3E0;background:#FFFFFF;
            color:#0C0C1A;cursor:pointer;font-family:'DM Sans',sans-serif;
        }
        </style>
        <button id="open-""" + key + """"
            onclick="(function(){
                var p=document.getElementById('ssb-""" + key + """');
                p.classList.toggle('open');
            })()">
            📚 Sources (""" + str(len(sources)) + """)
        </button>
        <div id="ssb-""" + key + """">
          <div class="ssh">
            <div class="sst">📚 Sources</div>
            <button class="ssc" onclick="document.getElementById('ssb-""" + key + """').classList.remove('open')">✕</button>
          </div>
          """ + sources_html + """
        </div>
        """,
        height=46,
    )


def render_followup_pills(questions: list, key: str) -> None:
    """Render clickable follow-up question pills that set pending_q."""
    if not questions:
        return
    pills_html = "".join([
        f'<span class="followup-pill" '
        f'onclick="(function(){{window.parent.postMessage({{type:\'streamlit:setComponentValue\',value:\'{q}\'}},\'*\')}})()">'
        f'↪ {q}</span>'
        for q in questions
    ])
    st.markdown(
        '<div class="followup-row">'
        '<div class="followup-label">Follow-up questions</div>'
        '<div class="followup-pills">' + pills_html + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def build_path_generator(goal: str, bot) -> str:
    """
    Generates a structured Pharos build roadmap for the given goal.
    Uses the existing RAG bot first, falls back to Gemini directly.
    Returns a dict with keys: steps, docs, actions.
    """
    BUILD_GOALS = {
        "Agent":          ("AI Agent",          "building an AI Agent or Skill on Pharos"),
        "dApp":           ("dApp",               "building a decentralised application on Pharos"),
        "Learning":       ("Learning Pharos",    "learning and understanding the Pharos ecosystem"),
        "Infrastructure": ("Infrastructure",     "building core infrastructure or tooling on Pharos"),
    }
    label, context = BUILD_GOALS.get(goal, ("Builder", "building on Pharos"))

    # Try RAG first
    rag_q = f"How do I start {context}? What are the steps, documentation, and resources?"
    try:
        rag_answer, _ = bot.ask(rag_q)
        has_rag = "I could not find" not in rag_answer
    except Exception:
        rag_answer = ""
        has_rag = False

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return rag_answer or "Could not generate roadmap — GEMINI_API_KEY missing."

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash", temperature=0.3,
        google_api_key=api_key,
    )
    context_block = ("\n\nContext from Pharos documentation:\n" + rag_answer[:1200]) if has_rag else ""
    prompt = (
        f"You are an expert Pharos blockchain developer guide. "
        f"Generate a concise, structured build roadmap for someone who wants to: {context}.\n"
        f"Return EXACTLY this JSON format (no other text):\n"
        f'{{"goal":"{label}",'
        f'"steps":[{{"num":1,"title":"Step title","desc":"1-2 sentence description"}},...],'
        f'"docs":[{{"title":"Doc name","url":"https://docs.pharos.xyz/..."}}],'
        f'"actions":[{{"label":"Action name","url":"https://..."}}]}}\n'
        f"Steps: 4-5 steps. Docs: 2-3 relevant links. Actions: 2-3 next steps."
        f"{context_block}"
    )
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw  = resp.content.strip()
        raw  = re.sub(r"^```(?:json)?\n?", "", raw, flags=re.IGNORECASE)
        raw  = re.sub(r"\n?```$", "", raw)
        return json.loads(raw)
    except Exception:
        return rag_answer or "Could not generate roadmap at this time."


def render_thinking_orb(state: str = "idle") -> None:
    """
    Renders the AI thinking orb via components.html.
    state: 'idle' | 'thinking' | 'done'
    """
    label = (
        "OctoBot is thinking..." if state == "thinking" else
        "Response ready ✓"       if state == "done"     else
        "OctoBot ready"
    )
    spin_style = (
        "animation:orb-think 0.8s ease-in-out infinite!important;"
        "box-shadow:0 0 24px rgba(26,26,255,0.5)!important;"
        if state == "thinking" else
        "animation:orb-settle 0.5s ease both!important;"
        if state == "done" else
        ""
    )
    components.html(
        f"""
        <style>
        body{{margin:0;padding:0;background:transparent;overflow:hidden;}}
        .ow{{display:flex;align-items:center;gap:10px;padding:6px 2px;}}
        .orb{{
            width:38px;height:38px;border-radius:50%;position:relative;flex-shrink:0;
            background:radial-gradient(circle at 35% 30%,#8BAAFF 0%,#1A1AFF 55%,#050525 100%);
            box-shadow:0 0 18px rgba(26,26,255,0.35);
            animation:orb-breathe 3.6s ease-in-out infinite;
            will-change:transform;
            {spin_style}
        }}
        .orb::after{{
            content:'';position:absolute;inset:3px;border-radius:50%;
            background:radial-gradient(circle at 30% 25%,rgba(255,255,255,0.38),transparent 58%);
        }}
        .orb-ring{{
            position:absolute;inset:-5px;border-radius:50%;
            border:1px solid rgba(26,26,255,0.22);
            animation:orb-ring 2.8s ease-in-out infinite;
            will-change:transform,opacity;
        }}
        /* orb-breathe now animates only `transform` (GPU-composited)
           instead of also animating `box-shadow` every frame — the
           shadow stays fixed at its resting value and only the orb's
           scale pulses, which still reads as "breathing" but is far
           cheaper since box-shadow recalculation/repaint no longer
           happens 60 times a second while a chat response is loading. */
        @keyframes orb-breathe{{
            0%,100%{{transform:scale(1);}}
            50%{{transform:scale(1.06);}}
        }}
        @keyframes orb-think{{
            0%{{transform:scale(0.94) rotate(0deg);}}
            50%{{transform:scale(1.1) rotate(180deg);}}
            100%{{transform:scale(0.94) rotate(360deg);}}
        }}
        @keyframes orb-settle{{
            0%{{transform:scale(1.12);}}
            100%{{transform:scale(1);}}
        }}
        @keyframes orb-ring{{
            0%,100%{{transform:scale(1);opacity:0.5;}}
            50%{{transform:scale(1.18);opacity:0.1;}}
        }}
        .ol{{font-size:12px;color:#5B5F6E;font-family:'DM Sans',sans-serif;
            font-weight:{"600" if state=="thinking" else "400"};}}
        </style>
        <div class="ow">
          <div class="orb"><div class="orb-ring"></div></div>
          <span class="ol">{label}</span>
        </div>
        """,
        height=52,
    )


def render_interactive_logo(logo_b64: str) -> None:
    """
    Neural Pulse Animation System.
    - Canvas-based: particles, aura, pulse waves, breathing glow
    - Hover: stronger glow
    - Click: opens assistant bubble
    - All motion is Apple/Linear quality — subtle, premium, 60fps
    - Zero CSS conflicts with Streamlit layout
    """
    img_src = logo_b64 if logo_b64 else ""

    components.html(
        """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
body{background:transparent;overflow:hidden;font-family:'DM Sans',sans-serif;}
.wrap{
    display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    width:100%;height:200px;position:relative;
}
canvas{
    position:absolute;top:0;left:0;
    width:100%;height:100%;
    pointer-events:none;
}
.logo-btn{
    position:relative;z-index:10;
    width:80px;height:80px;border-radius:50%;
    cursor:pointer;
    display:flex;align-items:center;justify-content:center;
    transition:transform 0.4s cubic-bezier(0.4,0,0.2,1);
}
.logo-btn:hover{transform:scale(1.06);}
.logo-img{
    width:80px;height:80px;border-radius:50%;
    display:block;
    transition:filter 0.4s cubic-bezier(0.4,0,0.2,1);
    filter:drop-shadow(0 2px 14px rgba(26,26,255,0.35));
}
.logo-btn:hover .logo-img{
    filter:drop-shadow(0 4px 24px rgba(26,26,255,0.65));
}
.logo-emoji{
    width:80px;height:80px;border-radius:50%;
    background:#1A1AFF;
    display:flex;align-items:center;justify-content:center;
    font-size:32px;line-height:1;
    filter:drop-shadow(0 2px 14px rgba(26,26,255,0.35));
    transition:filter 0.4s cubic-bezier(0.4,0,0.2,1);
}
.logo-btn:hover .logo-emoji{
    filter:drop-shadow(0 4px 24px rgba(26,26,255,0.65));
}
/* Assistant bubble */
.bubble{
    position:absolute;
    top:50%;
    left:calc(50% + 70px);
    transform:translateY(-50%) translateX(-8px) scale(0.92);
    background:#fff;border:1.5px solid #C8D0FF;
    border-radius:14px;
    box-shadow:0 8px 32px rgba(26,26,255,0.14);
    padding:12px 14px;width:210px;z-index:200;
    opacity:0;pointer-events:none;
    transition:opacity 0.22s cubic-bezier(0.4,0,0.2,1),
                transform 0.22s cubic-bezier(0.4,0,0.2,1);
}
.bubble.vis{
    opacity:1;pointer-events:all;
    transform:translateY(-50%) translateX(0) scale(1);
}
.bubble::before{
    content:'';position:absolute;top:50%;left:-6px;
    width:12px;height:12px;background:#fff;
    border-left:1.5px solid #C8D0FF;border-bottom:1.5px solid #C8D0FF;
    transform:translateY(-50%) rotate(45deg);
}
.bubble-q{font-size:12px;color:#0C0C1A;font-weight:500;line-height:1.5;margin-bottom:8px;}
.bubble-cta{
    display:flex;align-items:center;justify-content:center;gap:4px;
    font-size:11px;font-weight:700;color:#fff;background:#1A1AFF;
    border-radius:8px;padding:6px 12px;cursor:pointer;border:none;
    width:100%;font-family:'DM Sans',sans-serif;
}
</style>
</head>
<body>
<div class="wrap" id="wrap">
  <canvas id="np"></canvas>
  <div class="logo-btn" id="logoBtn" onclick="toggleBubble()">
    """ + (
        f'<img class="logo-img" src="{img_src}" alt="Pharos" />'
        if img_src else
        '<div class="logo-emoji">🐙</div>'
    ) + """
  </div>
  <div class="bubble" id="bubble">
    <div class="bubble-q">👋 Hi! I'm OctoBot.<br>Ask me anything about Pharos.</div>
    </div>
</div>

<script>
(function(){
  const canvas = document.getElementById('np');
  const ctx    = canvas.getContext('2d');
  const wrap   = document.getElementById('wrap');
  const btn    = document.getElementById('logoBtn');

  // ── Canvas sizing ───────────────────────────
  function resize(){
    canvas.width  = wrap.offsetWidth;
    canvas.height = wrap.offsetHeight;
  }
  resize();
  window.addEventListener('resize', resize);

  // ── State ───────────────────────────────────
  let cx = 0, cy = 0;            // logo center
  let hovered   = false;
  let t         = 0;             // frame counter
  let pulseWaves= [];            // active pulse waves
  let lastPulse = 0;             // timestamp of last pulse

  // getCenter() previously called getBoundingClientRect() twice on
  // EVERY animation frame (120 layout reads/second) — this forces the
  // browser to flush pending layout and recalculate geometry every
  // single tick, which is real layout-thrashing overhead for a value
  // that essentially never changes during normal use (the logo's
  // position relative to its own wrapper is stable unless the window
  // resizes). Now computed once up front, cached, and only
  // recalculated on resize or a slow 1s safety-net interval (in case
  // Streamlit reflows the surrounding layout without a window resize
  // event, e.g. during a page navigation).
  let cachedCenter = { x: 0, y: 0 };
  function recomputeCenter(){
    const r = btn.getBoundingClientRect();
    const w = wrap.getBoundingClientRect();
    cachedCenter = {
      x: r.left - w.left + r.width  * 0.5,
      y: r.top  - w.top  + r.height * 0.5,
    };
  }
  function getCenter(){
    return cachedCenter;
  }
  recomputeCenter();
  window.addEventListener('resize', recomputeCenter);
  setInterval(recomputeCenter, 1000);

  btn.addEventListener('mouseenter', ()=>{ hovered=true;  emitPulse(); });
  btn.addEventListener('mouseleave', ()=>{ hovered=false; });

  // ── Particles ──────────────────────────────
  const N = 12;
  const particles = Array.from({length:N}, (_,i)=>{
    const angle  = (i/N)*Math.PI*2;
    const radius = 52 + Math.random()*28;
    return {
      angle,
      baseRadius: radius,
      r:          radius,
      speed:      0.0006 + Math.random()*0.0008,   // very slow organic drift
      dr:         (Math.random()-0.5)*0.04,         // radius oscillation speed
      pr:         0,                                 // phase for radius osc
      prS:        0.008 + Math.random()*0.006,
      size:       1.2 + Math.random()*1.4,
      opacity:    0.25 + Math.random()*0.35,
      opSpeed:    0.004 + Math.random()*0.004,
      opPhase:    Math.random()*Math.PI*2,
    };
  });

  // ── Pulse wave emitter ─────────────────────
  function emitPulse(){
    pulseWaves.push({ r:44, opacity:0.55, max:190 });
  }

  // ── Main draw loop ─────────────────────────
  // rAF handle + visibility state so the loop fully stops when the tab
  // is hidden (no wasted CPU/GPU, and — crucially — no backlog of
  // catch-up frames firing all at once on refocus, which is a classic
  // source of a visible stutter burst). `t` is advanced by real
  // elapsed frames rather than a raw ++ so the animation phase never
  // jumps after a pause, keeping motion perfectly continuous.
  let rafId   = 0;
  let running = false;
  let lastTs  = 0;

  function draw(ts){
    rafId = requestAnimationFrame(draw);

    // Advance the frame counter by elapsed real time normalised to a
    // 60fps baseline. On a steady 60Hz display this is ~1 per frame
    // (identical to the previous behaviour); on higher-refresh or
    // uneven frames it keeps the visual speed constant instead of
    // running faster/stuttering. Clamped so a long pause can't produce
    // a giant jump.
    if (lastTs){
      const dt = ts - lastTs;
      t += Math.min(dt / 16.6667, 4);
    } else {
      t += 1;
    }
    lastTs = ts;

    ctx.clearRect(0,0,canvas.width,canvas.height);

    const c = getCenter();
    cx = c.x; cy = c.y;

    // ─ 1. Ambient aura ─
    const auraSize  = hovered ? 110 : 90;
    const auraAlpha = hovered ? 0.13 : 0.08;
    const auraGrad  = ctx.createRadialGradient(cx,cy,20, cx,cy,auraSize);
    auraGrad.addColorStop(0, `rgba(26,26,255,${auraAlpha})`);
    auraGrad.addColorStop(0.5,`rgba(26,26,255,${auraAlpha*0.4})`);
    auraGrad.addColorStop(1, 'rgba(26,26,255,0)');
    ctx.fillStyle = auraGrad;
    ctx.beginPath();
    ctx.arc(cx,cy,auraSize,0,Math.PI*2);
    ctx.fill();

    // ─ 2. Breathing ring ─
    const breathe  = Math.sin(t*0.018)*0.5+0.5;  // 0→1 slow cycle
    const ringR    = 50 + breathe*8;
    const ringAlpha= hovered ? 0.22 : 0.10 + breathe*0.07;
    ctx.beginPath();
    ctx.arc(cx,cy,ringR,0,Math.PI*2);
    ctx.strokeStyle = `rgba(26,26,255,${ringAlpha})`;
    ctx.lineWidth   = hovered ? 1.5 : 1;
    ctx.stroke();

    // ─ 3. Pulse waves (auto every 7s + hover) ─
    const now = performance.now();
    if(now - lastPulse > 7000){ emitPulse(); lastPulse=now; }

    pulseWaves = pulseWaves.filter(w=>{
      const progress = (w.r - 44) / (w.max - 44);
      w.opacity = 0.55 * (1 - progress) * (1 - progress);
      ctx.beginPath();
      ctx.arc(cx,cy,w.r,0,Math.PI*2);
      ctx.strokeStyle = `rgba(26,26,255,${w.opacity})`;
      ctx.lineWidth   = 1.2 * (1 - progress*0.5);
      ctx.stroke();
      w.r += 1.1 + progress*1.8;  // accelerates as it expands
      return w.r < w.max;
    });

    // ─ 4. Particles ─
    particles.forEach(p=>{
      p.angle  += p.speed;
      p.pr     += p.prS;
      p.r       = p.baseRadius + Math.sin(p.pr)*10;
      const px  = cx + Math.cos(p.angle)*p.r;
      const py  = cy + Math.sin(p.angle)*p.r;
      const op  = p.opacity * (0.5 + 0.5*Math.sin(t*p.opSpeed + p.opPhase))
                  * (hovered ? 1.4 : 1.0);
      const sz  = p.size * (0.8 + 0.4*Math.sin(p.pr*0.7));

      // Particle glow
      const pg = ctx.createRadialGradient(px,py,0, px,py,sz*3);
      pg.addColorStop(0, `rgba(26,26,255,${Math.min(op,0.85)})`);
      pg.addColorStop(1, 'rgba(26,26,255,0)');
      ctx.fillStyle = pg;
      ctx.beginPath();
      ctx.arc(px,py,sz*3,0,Math.PI*2);
      ctx.fill();

      // Particle core
      ctx.fillStyle = `rgba(100,130,255,${Math.min(op*1.8,1)})`;
      ctx.beginPath();
      ctx.arc(px,py,sz,0,Math.PI*2);
      ctx.fill();
    });

    // ─ 5. Logo inner glow ring ─
    const innerAlpha = hovered ? 0.35 : 0.15 + breathe*0.1;
    const ig = ctx.createRadialGradient(cx,cy,34, cx,cy,48);
    ig.addColorStop(0, 'rgba(26,26,255,0)');
    ig.addColorStop(0.7, `rgba(26,26,255,${innerAlpha*0.4})`);
    ig.addColorStop(1, `rgba(26,26,255,${innerAlpha})`);
    ctx.fillStyle = ig;
    ctx.beginPath();
    ctx.arc(cx,cy,48,0,Math.PI*2);
    ctx.fill();
  }

  // Start after a short delay so DOM is ready
  function startLoop(){
    if (running) return;
    running = true;
    lastTs  = 0;                 // reset delta baseline after any pause
    rafId   = requestAnimationFrame(draw);
  }
  function stopLoop(){
    running = false;
    if (rafId){ cancelAnimationFrame(rafId); rafId = 0; }
  }
  setTimeout(()=>{ lastPulse=performance.now(); startLoop(); }, 100);

  // Fully pause the ambient animation while the tab is backgrounded and
  // resume cleanly when it returns — no CPU spent off-screen, no
  // stutter burst on refocus.
  document.addEventListener('visibilitychange', function(){
    if (document.hidden){ stopLoop(); }
    else { lastPulse = performance.now(); startLoop(); }
  });

  // ── Bubble logic ─────────────────────────────
  window.toggleBubble = function(){
    document.getElementById('bubble').classList.toggle('vis');
  };
  window.goChat = function(){
    var navigated = false;

    // Primary approach: directly manipulate the REAL top-level page's
    // URL bar via history API, then dispatch a popstate-like reload.
    // This works even in cases where browsers silently block iframe-
    // initiated full navigation (location.href / location.assign),
    // because pushState + a manual reload of window.parent's own
    // document is treated as same-origin same-document navigation,
    // not a cross-frame redirect.
    try{
      var pdoc = window.parent.document;
      var purl = new URL(window.parent.location.href);
      purl.searchParams.set('goto','chat');
      window.parent.history.pushState({}, '', purl.toString());
      window.parent.location.reload();
      navigated = true;
    }catch(e){}

    if(!navigated){
      try{
        var url = new URL(window.top.location.href);
        url.searchParams.set('goto','chat');
        window.top.location.assign(url.toString());
        navigated = true;
      }catch(e2){}
    }

    if(!navigated){
      try{
        var url3 = new URL(window.parent.location.href);
        url3.searchParams.set('goto','chat');
        window.parent.location.assign(url3.toString());
        navigated = true;
      }catch(e3){}
    }

    if(!navigated){
      document.getElementById('bubble').classList.remove('vis');
    }
  };
  document.addEventListener('click',function(e){
    var b=document.getElementById('logoBtn');
    var p=document.getElementById('bubble');
    if(b&&p&&!b.contains(e.target)) p.classList.remove('vis');
  });

})();
</script>
</body>
</html>
        """,
        height=200,
        scrolling=False,
    )


# ─────────────────────────────────────────────
# MEMORY LEDGER — On-chain wallet intelligence
# Read-only. No transactions. No funds. No gas.
# ─────────────────────────────────────────────
PHAROS_CHAIN_ID_HEX = "0x688"      # 1672 decimal — confirmed via ChainList
PHAROS_CHAIN_ID_DEC = 1672
PHAROS_RPC_URL       = "https://rpc.pharos.xyz"
PHAROS_EXPLORER_URL  = "https://pharosscan.xyz"

# Pharos Testnet constants
PHAROS_TESTNET_CHAIN_ID_HEX = "0xa8231"  # 688689 decimal — Pharos Atlantic Testnet
PHAROS_TESTNET_CHAIN_ID_DEC = 688689
PHAROS_TESTNET_RPC_URL       = "https://atlantic.dplabs-internal.com"
PHAROS_TESTNET_EXPLORER_URL  = "https://atlantic.pharosscan.xyz"

# Allowlist of RPC endpoints the server is permitted to call. Prevents an
# attacker-supplied URL from redirecting outbound requests to internal hosts (SSRF).
ALLOWED_RPCS = {
    PHAROS_RPC_URL,
    "https://pharos.drpc.org",
    PHAROS_TESTNET_RPC_URL,
}


def render_wallet_connect_widget() -> None:
    """
    No-signature wallet connection: user simply pastes their wallet address.
    No browser extension required, no signing, no gas, read-only.
    Kept for API compatibility — actual UI rendered inline on Memory Ledger page.
    """
    pass
def _render_wallet_connect_widget_UNUSED():
    """UNUSED — retained only to prevent accidental re-introduction of removed code."""



def fetch_pharos_onchain_data(address: str, rpc_override: str = None) -> dict:
    """
    Reads PUBLIC on-chain data for a wallet via standard read-only JSON-RPC calls.
    No signature, no transaction, no funds ever touched.
    Accepts an optional rpc_override to query testnet or any custom RPC.
    Tries multiple known-good Pharos RPC endpoints in order until one responds.
    Returns dict with balance, tx count, and recent activity summary.
    """
    result = {
        "address":     address,
        "balance_pros": None,
        "tx_count":     None,
        "is_contract":  False,
        "available":    False,
        "error":        None,
    }

    if not valid_addr(address):
        result["error"] = "Invalid address"
        return result
    if rpc_override and rpc_override not in ALLOWED_RPCS:
        rpc_override = None

    rpc_candidates = [rpc_override] if rpc_override else [PHAROS_RPC_URL, "https://pharos.drpc.org"]
    headers = {"Content-Type": "application/json"}
    last_error = None

    for rpc_url in rpc_candidates:
        try:
            # 1) Native PROS balance — read-only, costs nothing
            bal_payload = {
                "jsonrpc": "2.0", "id": 1, "method": "eth_getBalance",
                "params": [address, "latest"],
            }
            r1 = requests.post(rpc_url, json=bal_payload, headers=headers, timeout=8)
            r1.raise_for_status()
            bal_hex = r1.json().get("result")
            if bal_hex:
                result["balance_pros"] = int(bal_hex, 16) / 1e18

            # 2) Transaction count — proxy for on-chain activity level
            count_payload = {
                "jsonrpc": "2.0", "id": 2, "method": "eth_getTransactionCount",
                "params": [address, "latest"],
            }
            r2 = requests.post(rpc_url, json=count_payload, headers=headers, timeout=8)
            r2.raise_for_status()
            count_hex = r2.json().get("result")
            if count_hex:
                result["tx_count"] = int(count_hex, 16)

            # 3) Check if address is a contract (bytecode present)
            code_payload = {
                "jsonrpc": "2.0", "id": 3, "method": "eth_getCode",
                "params": [address, "latest"],
            }
            r3 = requests.post(rpc_url, json=code_payload, headers=headers, timeout=8)
            r3.raise_for_status()
            code_hex = r3.json().get("result", "0x")
            result["is_contract"] = code_hex not in ("0x", "0x0", None)

            result["available"] = True
            result["error"] = None
            return result  # success — stop trying other endpoints

        except Exception as e:
            last_error = str(e)
            continue  # try next RPC candidate

    result["error"] = last_error
    return result


def _rpc(method: str, params: list, rpc_url: str = None, timeout: int = 8):
    """Single read-only JSON-RPC call with endpoint failover."""
    candidates = [rpc_url] if rpc_url else [PHAROS_RPC_URL, "https://pharos.drpc.org"]
    last = None
    for url in candidates:
        try:
            r = requests.post(
                url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                headers={"Content-Type": "application/json"}, timeout=timeout,
            )
            r.raise_for_status()
            body = r.json()
            if "error" in body:
                last = str(body["error"].get("message", "RPC error"))
                continue
            return body.get("result")
        except Exception as e:
            last = str(e)
            continue
    raise RuntimeError(last or "RPC unreachable")


def fetch_token_balances(address: str) -> dict:
    """Real ERC-20 + native balances for a wallet on Pharos mainnet.

    Uses the canonical MultiCall3 (documented at docs.pharos.xyz) to read
    every token balance in ONE eth_call, then falls back to individual
    eth_call reads if multicall is unavailable. Token addresses come from
    the official Pharos Token Registry only.
    """
    out = {"native": None, "tokens": [], "available": False, "error": None}
    if not valid_addr(address):
        out["error"] = "Invalid address"
        return out

    addr_arg = address.lower().replace("0x", "").rjust(64, "0")
    # balanceOf(address) selector
    call_data = "0x70a08231" + addr_arg

    try:
        bal_hex = _rpc("eth_getBalance", [address, "latest"])
        out["native"] = int(bal_hex, 16) / 1e18 if bal_hex else 0.0
    except Exception as e:
        out["error"] = str(e)
        return out

    # ── Try MultiCall3.aggregate3 — one round-trip for all tokens ──
    def _enc_multicall():
        # aggregate3((address target,bool allowFailure,bytes callData)[])
        sel = "0x82ad56cb"
        n = len(PHAROS_TOKENS)
        head = "0000000000000000000000000000000000000000000000000000000000000020"
        head += hex(n)[2:].rjust(64, "0")
        # Each tuple is dynamic → offsets table, then bodies
        bodies, offsets, cursor = [], [], n * 32
        inner = call_data[2:]
        body_len = len(inner) // 2
        for _sym, taddr, _d, _l in PHAROS_TOKENS:
            b = taddr.lower().replace("0x", "").rjust(64, "0")      # target
            b += "0".rjust(63, "0") + "0"                            # allowFailure=false
            b += hex(96)[2:].rjust(64, "0")                          # bytes offset
            b += hex(body_len)[2:].rjust(64, "0")                    # bytes length
            b += inner.ljust(((len(inner) + 63) // 64) * 64, "0")    # padded data
            offsets.append(cursor)
            cursor += len(b) // 2
            bodies.append(b)
        table = "".join(hex(o)[2:].rjust(64, "0") for o in offsets)
        return sel + head + table + "".join(bodies)

    rows, ok = [], False
    try:
        res = _rpc("eth_call", [{"to": MULTICALL3_ADDR, "data": _enc_multicall()}, "latest"])
        if res and res != "0x":
            raw = res[2:]
            cnt = int(raw[64:128], 16)
            if cnt == len(PHAROS_TOKENS):
                base = 128
                offs = [int(raw[base + i * 64: base + (i + 1) * 64], 16) for i in range(cnt)]
                for i, (sym, taddr, dec, label) in enumerate(PHAROS_TOKENS):
                    st_ = base + offs[i] * 2
                    success = int(raw[st_: st_ + 64], 16) == 1
                    dlen = int(raw[st_ + 128: st_ + 192], 16)
                    val = int(raw[st_ + 192: st_ + 192 + 64], 16) if (success and dlen >= 32) else 0
                    rows.append({"sym": sym, "addr": taddr, "label": label,
                                 "bal": val / (10 ** dec)})
                ok = True
    except Exception:
        ok = False

    # ── Fallback: read each token individually ──
    if not ok:
        rows = []
        for sym, taddr, dec, label in PHAROS_TOKENS:
            try:
                res = _rpc("eth_call", [{"to": taddr, "data": call_data}, "latest"])
                val = int(res, 16) if res and res != "0x" else 0
            except Exception:
                val = 0
            rows.append({"sym": sym, "addr": taddr, "label": label, "bal": val / (10 ** dec)})

    out["tokens"] = rows
    out["available"] = True
    return out


def fetch_tx_receipt(tx_hash: str) -> dict:
    """Poll a transaction receipt. Returns status once mined."""
    out = {"mined": False, "status": None, "block": None, "error": None}
    if not valid_txhash(tx_hash):
        out["error"] = "Invalid transaction hash"
        return out
    try:
        r = _rpc("eth_getTransactionReceipt", [tx_hash])
        if not r:
            return out  # still pending
        out["mined"] = True
        out["status"] = "success" if r.get("status") == "0x1" else "failed"
        out["block"] = int(r["blockNumber"], 16) if r.get("blockNumber") else None
    except Exception as e:
        out["error"] = str(e)
    return out


def fetch_pharos_transaction(tx_hash: str) -> dict:
    """
    Reads PUBLIC transaction data via standard read-only JSON-RPC calls.
    Same safety profile as fetch_pharos_onchain_data: no signature, no
    transaction sent, no funds ever touched — purely reads what is
    already permanently recorded on-chain for anyone to see.
    Tries the same RPC candidates in order until one responds.
    """
    result = {
        "hash":          tx_hash,
        "from_addr":     None,
        "to_addr":       None,
        "value_pros":    None,
        "gas_used":      None,
        "gas_price_gwei":None,
        "status":        None,   # "success" | "failed" | None (pending/unknown)
        "block_number":  None,
        "is_contract_call": False,
        "input_data":    None,
        "available":     False,
        "error":         None,
    }

    if not valid_txhash(tx_hash):
        result["error"] = "Invalid transaction hash"
        return result

    rpc_candidates = [PHAROS_RPC_URL, "https://pharos.drpc.org"]
    headers = {"Content-Type": "application/json"}
    last_error = None

    for rpc_url in rpc_candidates:
        try:
            # 1) Transaction details — sender, recipient, value, input data
            tx_payload = {
                "jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionByHash",
                "params": [tx_hash],
            }
            r1 = requests.post(rpc_url, json=tx_payload, headers=headers, timeout=8)
            r1.raise_for_status()
            tx = r1.json().get("result")

            if not tx:
                # Valid RPC response but transaction not found — could be
                # a wrong hash, or on a different chain. Not an error,
                # just nothing to show.
                result["available"] = True
                result["error"] = "Transaction not found on Pharos — check the hash and try again."
                return result

            result["from_addr"] = tx.get("from")
            result["to_addr"]   = tx.get("to")
            if tx.get("value"):
                result["value_pros"] = int(tx["value"], 16) / 1e18
            if tx.get("gasPrice"):
                result["gas_price_gwei"] = int(tx["gasPrice"], 16) / 1e9
            if tx.get("blockNumber"):
                result["block_number"] = int(tx["blockNumber"], 16)
            input_data = tx.get("input", "0x")
            result["input_data"] = input_data
            # Any input data beyond "0x" means this called a contract
            # method rather than a plain value transfer.
            result["is_contract_call"] = input_data not in ("0x", "0x0", None) and len(input_data) > 2

            # 2) Receipt — confirms success/failure and actual gas used
            receipt_payload = {
                "jsonrpc": "2.0", "id": 2, "method": "eth_getTransactionReceipt",
                "params": [tx_hash],
            }
            r2 = requests.post(rpc_url, json=receipt_payload, headers=headers, timeout=8)
            r2.raise_for_status()
            receipt = r2.json().get("result")
            if receipt:
                status_hex = receipt.get("status")
                if status_hex is not None:
                    result["status"] = "success" if status_hex == "0x1" else "failed"
                if receipt.get("gasUsed"):
                    result["gas_used"] = int(receipt["gasUsed"], 16)
            else:
                result["status"] = None  # pending — not yet mined

            result["available"] = True
            result["error"] = None
            return result

        except Exception as e:
            last_error = str(e)
            continue

    result["error"] = last_error
    return result


# ═════════════════════════════════════════════════════════════
# x402 — Pay-per-call AI (HTTP 402 "Payment Required" for OctoBot)
# ─────────────────────────────────────────────────────────────
# Faithful model of the x402 flow Pharos Research built:
#   1. Client requests a PREMIUM resource (a deep OctoBot answer).
#   2. Server replies 402 Payment Required + payment details (this is the
#      "challenge": pay-to address, amount, resource id, nonce).
#   3. Client pays the micro-amount on-chain (Pharos testnet/mainnet).
#   4. Client returns the tx hash as proof; server VERIFIES it on-chain
#      (recipient + amount + success) using the existing read-only RPC.
#   5. Server settles the request and returns the premium answer.
#
# Free answering is completely unaffected — this path only runs when the
# user explicitly opts into a premium (x402) call. All verification is
# read-only; the app never holds keys or moves funds itself.
# ═════════════════════════════════════════════════════════════

# Where micro-payments are sent for the demo. Override via env if you want
# to point at your own receiving address. This is a PUBLIC pay-to address;
# no private key lives in the app.
X402_PAYTO_ADDRESS = os.getenv(
    "X402_PAYTO_ADDRESS",
    "0x000000000000000000000000000000000000dEaD",  # placeholder demo sink
)
X402_PRICE_PROS   = 0.05      # price per premium call, in native units
X402_TOLERANCE    = 0.10      # accept payments within 10% under (gas/rounding)

def x402_get_payto() -> str:
    """Resolve the active pay-to address: a UI-set address (validated) takes
    precedence, otherwise the env/default constant. Always returns a string."""
    try:
        import streamlit as _st
        ui_addr = _st.session_state.get("x402_payto", "")
        v = valid_addr(ui_addr)
        if v:
            return v
    except Exception:
        pass
    return X402_PAYTO_ADDRESS

def x402_make_challenge(question: str) -> dict:
    """Build the 402 'Payment Required' challenge for a premium question.
    Deterministic resource id + nonce so the same paid tx maps to one answer.
    """
    nonce = hashlib.sha256(
        (question + str(int(time.time() // 3600))).encode("utf-8")
    ).hexdigest()[:16]
    resource_id = "octobot/premium/" + hashlib.sha256(
        question.encode("utf-8")
    ).hexdigest()[:12]
    return {
        "status":      402,
        "resource":    resource_id,
        "pay_to":      x402_get_payto(),
        "amount_pros": X402_PRICE_PROS,
        "nonce":       nonce,
        "scheme":      "exact",
        "network":     "pharos",
        "question":    question,
    }

def x402_payment_uri(challenge: dict, chain_id_dec: int) -> str:
    """EIP-681 ethereum: URI so a wallet can fulfil the 402 by scanning a QR.
    Encodes recipient, value (wei), and chainId. Display-only; the user's
    wallet performs the actual signing/sending.
    """
    try:
        wei = int(round(float(challenge["amount_pros"]) * 1e18))
    except Exception:
        wei = 0
    pay_to = challenge.get("pay_to", "")
    return "ethereum:" + pay_to + "@" + str(chain_id_dec) + "?value=" + str(wei)

def x402_verify_payment(tx_hash: str, challenge: dict) -> dict:
    """Verify an on-chain payment settles the 402 challenge.
    Reuses fetch_pharos_transaction (read-only). Confirms:
      • tx exists and succeeded
      • recipient matches the required pay-to address
      • value paid >= required amount (within tolerance)
    Returns {ok, reason, tx} — never raises.
    """
    out = {"ok": False, "reason": None, "tx": None}

    th = valid_txhash(tx_hash)
    if not th:
        out["reason"] = "That doesn't look like a valid Pharos transaction hash."
        return out

    tx = fetch_pharos_transaction(th)
    out["tx"] = tx

    if not tx.get("available") or tx.get("error"):
        out["reason"] = tx.get("error") or "Could not read that transaction yet — it may still be pending."
        return out
    if tx.get("status") == "failed":
        out["reason"] = "That transaction failed on-chain, so the payment didn't settle."
        return out
    if tx.get("status") is None:
        out["reason"] = "That transaction is still pending — wait for it to confirm, then try again."
        return out

    want_to = (challenge.get("pay_to") or "").lower()
    got_to  = (tx.get("to_addr") or "").lower()
    if want_to and got_to and want_to != got_to:
        out["reason"] = "That payment went to a different address than the one required."
        return out

    need = float(challenge.get("amount_pros", 0)) * (1.0 - X402_TOLERANCE)
    paid = tx.get("value_pros")
    if paid is None or paid < need:
        out["reason"] = (
            "The amount paid (" + (("%.4f" % paid) if paid is not None else "0")
            + " PROS) is less than the required " + ("%.4f" % float(challenge.get("amount_pros", 0))) + " PROS."
        )
        return out

    out["ok"] = True
    return out

def x402_generate_premium_answer(question: str, bot, sel_lang: str = "English") -> str:
    """Generate the ENHANCED (premium) answer that the paid call unlocks.
    Uses docs context from the bot, then asks Gemini for a deeper, structured
    response. Falls back to the standard bot answer if Gemini is unavailable
    so a paid call never returns nothing.
    """
    # Pull docs grounding from the existing RAG bot.
    try:
        base_answer, _ = bot.ask(question)
    except Exception:
        base_answer = ""

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return base_answer or "Premium answer unavailable (no model configured)."

    lang_instruction = (
        ("CRITICAL: respond entirely in " + sel_lang + ". ")
        if sel_lang and sel_lang != "English" else "Respond in English. "
    )
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0.5,
            google_api_key=api_key,
        )
        prompt = (
            "You are OctoBot Premium, an expert analyst on the Pharos blockchain. "
            "A user has paid a micro-payment (x402) to unlock a deeper, higher-effort answer. "
            "Give a thorough, well-structured response: lead with a direct answer, then add "
            "expert context, concrete next steps, and any relevant Pharos-specific detail "
            "(SPNs, restaking, RWA/RealFi, PROS, x402). Keep PROS, SPN, RWA, EVM in English.\n"
            + lang_instruction +
            "\nGrounding notes from Pharos docs (may be empty):\n" + (base_answer or "(none)") +
            "\n\nUser question: " + question
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        return resp.content or base_answer or "Premium answer unavailable."
    except Exception:
        return base_answer or "Premium answer unavailable right now."


def x402_render_pending_gate() -> bool:
    """Render the 402 payment gate from session_state (NOT from the transient
    `question` variable). This fixes the bug where pasting a tx hash and clicking
    Verify did nothing: the old gate lived inside `if question:`, so the rerun a
    button click triggers — where chat_input is empty — skipped the whole block
    and the button handler never ran. By rendering from st.session_state.x402_challenge,
    the gate (and its buttons) persist across reruns. Returns True if a gate is shown.
    """
    import streamlit as st
    _x402_ch = st.session_state.get("x402_challenge")
    if not _x402_ch:
        return False
    # Already paid? clear and let normal generation proceed.
    if _x402_ch.get("resource") in st.session_state.get("x402_unlocked", {}):
        st.session_state.x402_challenge = None
        return False

    _is_testnet = st.session_state.get("pay_network", "mainnet") == "testnet"
    _chain_dec  = PHAROS_TESTNET_CHAIN_ID_DEC if _is_testnet else PHAROS_CHAIN_ID_DEC
    _explorer   = PHAROS_TESTNET_EXPLORER_URL if _is_testnet else PHAROS_EXPLORER_URL
    _net_label  = "Pharos Atlantic (testnet)" if _is_testnet else "Pharos Mainnet"
    _uri        = x402_payment_uri(_x402_ch, _chain_dec)
    _question   = _x402_ch.get("question", "")
    _k          = _x402_ch.get("nonce", "x")

    with st.chat_message("assistant", avatar="🐙"):
        st.markdown(
            '<div style="background:linear-gradient(135deg,#0A0A28,#1414E8);'
            'border-radius:16px;padding:1.1rem 1.3rem;color:#fff;margin-bottom:0.6rem;">'
            '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">'
            '<span style="font-family:DM Mono,monospace;font-size:11px;font-weight:700;'
            'background:rgba(255,255,255,0.16);border-radius:6px;padding:2px 8px;">HTTP 402</span>'
            '<span style="font-size:13px;font-weight:800;">Payment Required</span></div>'
            '<div style="font-size:12.5px;color:rgba(255,255,255,0.78);line-height:1.55;">'
            'This is a <b>premium (x402)</b> OctoBot call. Settle a small on-chain micro-payment '
            'to unlock a deeper, expert answer. Your wallet does the signing — OctoBot only '
            'verifies the payment on-chain.</div>'
            '<div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:0.7rem;font-size:12px;">'
            '<div><div style="color:rgba(255,255,255,0.55);font-size:10px;text-transform:uppercase;'
            'letter-spacing:0.05em;">Amount</div><div style="font-weight:800;">'
            + ("%.2f" % _x402_ch["amount_pros"]) + ' PROS</div></div>'
            '<div><div style="color:rgba(255,255,255,0.55);font-size:10px;text-transform:uppercase;'
            'letter-spacing:0.05em;">Network</div><div style="font-weight:700;">' + esc(_net_label) + '</div></div>'
            '<div style="min-width:0;"><div style="color:rgba(255,255,255,0.55);font-size:10px;'
            'text-transform:uppercase;letter-spacing:0.05em;">Pay&nbsp;to</div>'
            '<div style="font-family:DM Mono,monospace;font-size:11px;word-break:break-all;">'
            + esc(_x402_ch["pay_to"]) + '</div></div>'
            '<div style="min-width:0;"><div style="color:rgba(255,255,255,0.55);font-size:10px;'
            'text-transform:uppercase;letter-spacing:0.05em;">Resource</div>'
            '<div style="font-family:DM Mono,monospace;font-size:11px;word-break:break-all;">'
            + esc(_x402_ch["resource"]) + '</div></div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        _qcol, _vcol = st.columns([1, 1.3], gap="large")
        with _qcol:
            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#0C0C1A;margin-bottom:4px;">'
                '📲 Scan to pay (EIP-681)</div>', unsafe_allow_html=True)
            render_qr_code(_uri, size=150, key="x402_qr_" + _k)
            st.markdown(
                '<div style="font-size:10px;color:#7A7F96;word-break:break-all;margin-top:4px;">'
                + esc(_uri) + '</div>', unsafe_allow_html=True)

        with _vcol:
            st.markdown(
                '<div style="font-size:11px;font-weight:700;color:#0C0C1A;margin-bottom:4px;">'
                '✅ Settle the 402 challenge</div>', unsafe_allow_html=True)
            st.markdown(
                '<div style="font-size:11.5px;color:#42475A;line-height:1.55;margin-bottom:6px;">'
                'Pay from your wallet, then paste the transaction hash. OctoBot verifies it '
                'on-chain (recipient + amount + success) before unlocking.</div>',
                unsafe_allow_html=True)
            _txh = st.text_input(
                "Transaction hash", key="x402_txh_" + _k,
                placeholder="0x… your payment tx hash",
                label_visibility="collapsed",
            )
            _bcol1, _bcol2 = st.columns(2)
            with _bcol1:
                if st.button("🔓 Verify & unlock", key="x402_verify_" + _k,
                             use_container_width=True):
                    # Read the hash live from the widget's own session_state store
                    # so we never rely on a stale local variable.
                    _hash_now = st.session_state.get("x402_txh_" + _k, _txh) or _txh
                    with st.spinner("Verifying payment on-chain…"):
                        _res = x402_verify_payment(_hash_now, _x402_ch)
                    if _res["ok"]:
                        st.session_state.x402_unlocked[_x402_ch["resource"]] = (_hash_now or "").strip()
                        st.session_state.x402_receipts.append({
                            "amount": "%.2f" % _x402_ch["amount_pros"],
                            "tx":     (_hash_now or "").strip(),
                            "resource": _x402_ch["resource"],
                        })
                        st.session_state.x402_challenge = None
                        st.session_state["pending_q"] = _question
                        st.rerun()
                    else:
                        st.session_state["x402_last_error"] = str(_res.get("reason", "unknown error"))
                        st.rerun()
            with _bcol2:
                if st.button("🧪 Simulate (demo)", key="x402_sim_" + _k,
                             use_container_width=True,
                             help="Demo only — marks the call as paid WITHOUT a real on-chain payment. "
                                  "Use to preview the unlocked answer flow."):
                    st.session_state.x402_unlocked[_x402_ch["resource"]] = "SIMULATED"
                    st.session_state.x402_receipts.append({
                        "amount": "%.2f" % _x402_ch["amount_pros"],
                        "tx":     "SIMULATED (demo)",
                        "resource": _x402_ch["resource"],
                    })
                    st.session_state.x402_challenge = None
                    st.session_state["pending_q"] = _question
                    st.rerun()

            _err = st.session_state.pop("x402_last_error", None)
            if _err:
                st.error("Payment not verified: " + _err)

            if _explorer:
                st.markdown(
                    '<a href="' + esc_url(_explorer) + '" target="_blank" rel="noopener noreferrer" '
                    'style="font-size:11px;color:#1A1AFF;text-decoration:none;font-weight:600;">'
                    'Open Pharos explorer ↗</a>', unsafe_allow_html=True)

            if st.button("✕ Cancel premium call", key="x402_cancel_" + _k):
                st.session_state.x402_challenge = None
                st.rerun()

    return True


def explain_transaction(tx_data: dict) -> dict:
    """
    Uses Gemini to turn raw transaction fields into a plain-language
    explanation. Falls back to a deterministic explanation (still using
    the REAL transaction numbers) if Gemini is unavailable — same
    fallback pattern as synthesize_wallet_profile.
    """
    api_key = os.getenv("GEMINI_API_KEY")

    def deterministic_explanation():
        """Builds an explanation straight from real transaction fields — no AI needed."""
        status = tx_data.get("status")
        status_label = (
            "completed successfully" if status == "success" else
            "failed" if status == "failed" else
            "is still pending / status unknown"
        )
        value = tx_data.get("value_pros")
        kind = "a smart contract interaction" if tx_data.get("is_contract_call") else "a simple PROS transfer"

        summary_parts = [f"This transaction {status_label} and was {kind}."]
        if value is not None and value > 0:
            summary_parts.append(f"It moved {value:.6f} PROS.")
        elif not tx_data.get("is_contract_call"):
            summary_parts.append("No PROS value was attached to it.")
        if tx_data.get("gas_used"):
            summary_parts.append(f"It consumed {tx_data['gas_used']:,} gas to execute.")

        return {
            "summary": " ".join(summary_parts),
            "category": "Contract Call" if tx_data.get("is_contract_call") else "Transfer",
            "plain_steps": [
                f"Sent from {tx_data.get('from_addr','unknown')[:10]}…",
                f"Received by {tx_data.get('to_addr','unknown')[:10] if tx_data.get('to_addr') else 'a new contract'}…",
                f"Status: {status_label}",
            ],
        }

    if not api_key or not tx_data.get("available") or tx_data.get("error"):
        return deterministic_explanation()

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
            "it likely happened (e.g. a token swap, a transfer, a contract "
            "deployment, an approval, etc). Then classify it into one short "
            "category label (2-3 words, e.g. 'Token Transfer', 'Contract Call', "
            "'Token Swap', 'NFT Mint').\n\n"
            f"From: {tx_data.get('from_addr')}\n"
            f"To: {tx_data.get('to_addr')}\n"
            f"Value: {tx_data.get('value_pros')} PROS\n"
            f"Status: {tx_data.get('status')}\n"
            f"Is contract call: {tx_data.get('is_contract_call')}\n"
            f"Gas used: {tx_data.get('gas_used')}\n\n"
            "Return ONLY valid JSON in this exact format, no markdown fences:\n"
            '{"summary": "...", "category": "...", '
            '"plain_steps": ["step 1", "step 2", "step 3"]}'
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw  = resp.content.strip()
        raw  = re.sub(r"^```(?:json)?\n?", "", raw, flags=re.IGNORECASE)
        raw  = re.sub(r"\n?```$", "", raw)
        parsed = json.loads(raw)
        if not all(k in parsed for k in ("summary", "category", "plain_steps")):
            return deterministic_explanation()
        return parsed
    except Exception:
        return deterministic_explanation()


def synthesize_wallet_profile(onchain_data: dict) -> dict:
    """
    Uses Gemini to turn raw on-chain numbers into a readable intelligence
    profile. Falls back to a deterministic profile (still using the REAL
    on-chain numbers) if Gemini is unavailable or returns bad output.
    """
    api_key  = os.getenv("GEMINI_API_KEY")
    addr     = onchain_data.get("address", "")
    bal      = onchain_data.get("balance_pros")
    tx_count = onchain_data.get("tx_count")
    is_contract = onchain_data.get("is_contract")

    def deterministic_profile():
        """Builds a profile straight from real on-chain numbers — no AI needed."""
        n = tx_count or 0
        if n == 0:
            tx_label, risk = "New Wallet", "Unknown"
        elif n <= 20:
            tx_label, risk = "Early Explorer", "Conservative"
        elif n <= 150:
            tx_label, risk = "Active Trader", "Moderate"
        else:
            tx_label, risk = "Power User", "Active"

        bal_str = f"{bal:.4f}" if bal is not None else "an unknown amount of"
        summary = (
            f"This wallet has made {n} transaction{'s' if n != 1 else ''} on Pharos "
            f"with a current balance of {bal_str} PROS."
            if bal is not None or tx_count is not None
            else "Wallet connected. Limited on-chain signal available yet — "
                 "interact with Pharos testnet/mainnet to build your profile."
        )
        return {
            "summary": summary,
            "tags":    [tx_label, "Pharos Native", "On-chain Verified"],
            "risk":    risk,
            "insight": (
                "Explore the Ecosystem page to find dApps matching your activity."
                if n > 0 else
                "Once you've made a few transactions on Pharos, OctoBot can "
                "infer your builder type, risk profile, and likely interests."
            ),
        }

    # No on-chain data at all (RPC unreachable) — nothing to synthesize from.
    if not onchain_data.get("available"):
        return {
            "summary":  "Wallet connected. Limited on-chain signal available yet — "
                        "interact with Pharos testnet/mainnet to build your profile.",
            "tags":     ["New Wallet"],
            "risk":     "Unknown",
            "insight":  "Once you've made a few transactions on Pharos, OctoBot can "
                        "infer your builder type, risk profile, and likely interests.",
        }

    # No Gemini key — still build an accurate profile from real numbers.
    if not api_key:
        return deterministic_profile()

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
            f"Wallet: {addr}\n"
            f"PROS Balance: {bal if bal is not None else 'unknown'}\n"
            f"Transaction count: {tx_count if tx_count is not None else 'unknown'}\n"
            f"Is contract address: {is_contract}\n\n"
            "Return ONLY valid JSON in this exact format, no markdown fences:\n"
            '{"summary": "...", "tags": ["tag1","tag2","tag3"], "risk": "...", '
            '"insight": "one actionable suggestion for what to do next on Pharos"}'
        )
        resp = llm.invoke([HumanMessage(content=prompt)])
        raw  = resp.content.strip()
        raw  = re.sub(r"^```(?:json)?\n?", "", raw, flags=re.IGNORECASE)
        raw  = re.sub(r"\n?```$", "", raw)
        parsed = json.loads(raw)
        # Sanity check the response actually has the fields we need.
        if not all(k in parsed for k in ("summary", "tags", "risk", "insight")):
            return deterministic_profile()
        return parsed
    except Exception:
        return deterministic_profile()


# ─────────────────────────────────────────────
# OCTOBOT INITIALISATION — non-blocking, timeout-guarded
#
# Root cause of the "Loading Knowledge Base…" hang: OctoBot() builds /
# opens the vectorstore and initialises the LLM client synchronously on
# the Streamlit script thread. Any slow or stalled step inside it
# (embedding model download, vectorstore open, network call without a
# timeout) blocked the rerun forever, so the loading screen never
# resolved — no exception was raised, so the except-branch never fired.
#
# Fix: construct OctoBot on a daemon worker thread guarded by a hard
# timeout. The UI thread merely polls a shared, process-wide holder, so
# it stays responsive, the loading state always terminates (success,
# error, or timeout), and repeated reruns / multiple sessions share one
# initialisation (single-flight lock — no duplicate builds, no races).
# ─────────────────────────────────────────────
OCTOBOT_INIT_TIMEOUT = 90  # seconds before we surface a timeout error

_octobot_lock = threading.Lock()

# ─────────────────────────────────────────────
# IN-APP DEFI ASSISTANT — feature guide
#
# The RAG index knows the Pharos *docs*. It does not know THIS app's
# UI. So when someone asks "how do I stake?" they should get the real
# workflow for the screens in front of them, not a docs paraphrase.
#
# Each entry describes a feature as it is ACTUALLY implemented here —
# including honest notes where something routes out to an official
# protocol. Keep this in sync with the DeFi page when features change.
# ─────────────────────────────────────────────
APP_FEATURES = {
    "connect_wallet": {
        "title": "Connect your wallet",
        "purpose": "Your wallet is the single sign-in for everything on-chain here — "
                   "balances, wallet score, history and payments all key off it.",
        "steps": [
            "Click **Connect Wallet** at the top-right of any page.",
            "Pick your wallet in the popup (MetaMask, OKX, Rabby, Coinbase — any EVM wallet).",
            "Approve the connection request in the wallet.",
            "Check the pill shows a green dot and **Pharos**. Amber means you're on the wrong chain.",
            "If it's amber, click **Switch** — the app switches you to Pharos Pacific Mainnet "
            "(chain 1672), and offers to add the network if your wallet doesn't have it.",
        ],
        "prereq": ["An EVM wallet extension installed", "No signature or gas needed just to connect"],
        "warn": "Connecting only shares your public address. It never moves funds and never "
                "asks for a signature. Never share your seed phrase — nothing here will ask for it.",
        "next": "Open **DeFi → Portfolio** to see your live balances.",
    },
    "portfolio": {
        "title": "View your portfolio",
        "purpose": "See your real PROS and token balances, read live from Pharos mainnet.",
        "steps": [
            "Connect your wallet (top-right).",
            "Go to **DeFi → Portfolio**.",
            "Balances load automatically from chain — native PROS plus the registry tokens "
            "(WPROS, USDC, WETH, LINK).",
            "Click **↻ Refresh balances** for a fresh read.",
            "Click **View wallet on PharosScan** for the full explorer view.",
        ],
        "prereq": ["Wallet connected", "Wallet on Pharos Pacific Mainnet (chain 1672)"],
        "warn": "Balances are read-only — nothing is cached on a server and nothing is signed.",
        "next": "Try **DeFi → Wallet Score** for an on-chain reputation breakdown.",
    },
    "swap": {
        "title": "Swap tokens",
        "purpose": "Trade PROS and other Pharos tokens on FaroSwap, the native AMM+PMM DEX.",
        "steps": [
            "Connect your wallet and make sure you're on Pharos.",
            "Go to **DeFi → Swap**.",
            "Click **Open FaroSwap** — it opens with the same wallet you connected here.",
            "On FaroSwap: pick your input/output tokens and amount.",
            "Approve the token spend if prompted (first time per token), then confirm the swap.",
        ],
        "prereq": ["Wallet connected", "PROS for gas", "A balance of the token you're selling"],
        "warn": "Swaps execute on FaroSwap, not in this app — this hub doesn't hold a verified "
                "FaroSwap mainnet router address, and routing your funds through an unverified "
                "contract would be unsafe. Check the rate and slippage on FaroSwap before confirming; "
                "swaps are irreversible.",
        "next": "Check **DeFi → Portfolio** to confirm your new balances.",
    },
    "bridge": {
        "title": "Bridge assets to Pharos",
        "purpose": "Move tokens between Pharos and other chains.",
        "steps": [
            "Connect your wallet.",
            "Go to **DeFi → Bridge**.",
            "Click **Open Jumper (LI.FI)** — it aggregates the supported routes into Pharos.",
            "Choose source chain, destination (Pharos), token and amount.",
            "Approve if prompted, then confirm. Wait for finality on both chains.",
        ],
        "prereq": ["Wallet connected", "Gas on the SOURCE chain", "Funds to bridge"],
        "warn": "Bridging is irreversible and takes minutes, not seconds — don't close the wallet "
                "mid-flow. Always verify the destination chain is Pharos before confirming. "
                "USDC uses Circle CCTP v2 (native burn-and-mint); other assets route via CCIP/LayerZero.",
        "next": "Once funds land, check **DeFi → Portfolio**.",
    },
    "staking": {
        "title": "Stake PROS",
        "purpose": "Staking PROS helps secure Pharos and earns protocol rewards.",
        "steps": [
            "Go to **DeFi → Staking** to check the current status.",
        ],
        "prereq": ["Wallet connected"],
        "warn": "Native PROS staking is NOT live in this app yet — Pharos hasn't published an "
                "official staking/stPROS contract address, and stPROS native yield is publicly "
                "described as not yet live. This app deliberately shows no APR rather than an "
                "invented one, and won't route your PROS to an unverified contract. "
                "Be sceptical of any site offering PROS staking today.",
        "next": "Follow @pharos_network or the Pharos Discord for the staking launch.",
    },
    "wallet_score": {
        "title": "Check your wallet score",
        "purpose": "A transparent 0–100 reputation score from your real on-chain activity.",
        "steps": [
            "Connect your wallet.",
            "Go to **DeFi → Wallet Score**.",
            "Read the score, tier, and the Activity / Holdings / Engagement breakdown bars.",
        ],
        "prereq": ["Wallet connected", "Wallet on Pharos"],
        "warn": "Scoring is deterministic and uses only public on-chain data — no signature needed.",
        "next": "See **DeFi → History** for your transaction footprint.",
    },
    "history": {
        "title": "View transaction history",
        "purpose": "See your on-chain footprint on Pharos.",
        "steps": [
            "Connect your wallet.",
            "Go to **DeFi → History** for your transaction count and balance.",
            "Click **Full history on PharosScan** for an itemised list.",
        ],
        "prereq": ["Wallet connected"],
        "warn": "Pharos RPC exposes account state, not an indexed list — PharosScan does the indexing.",
        "next": "Look up any specific hash in **DeFi → Explorer**.",
    },
    "rwa_market": {
        "title": "Track the RWA market",
        "purpose": "Live prices for leading real-world-asset tokens, next to $PROS.",
        "steps": [
            "Go to **DeFi → RWA Market** — no wallet needed.",
            "Review live prices and 24h changes.",
            "Click **🔄 Refresh market data** for the latest.",
        ],
        "prereq": ["None — this is public market data"],
        "warn": "Market data is informational, not investment advice. Crypto prices are volatile.",
        "next": "Try **Market Pulse** for AI sentiment analysis.",
    },
    "explorer": {
        "title": "Explore transactions and addresses",
        "purpose": "Inspect any Pharos transaction or address in plain language.",
        "steps": [
            "Go to **DeFi → Explorer** — no wallet needed.",
            "Paste a transaction hash (0x + 64 chars) or address (0x + 40 chars).",
            "Click **Inspect** for status, value, block and type.",
        ],
        "prereq": ["A valid hash or address"],
        "warn": "Read-only — this only reads what is already public on-chain.",
        "next": "Use **Memory Ledger** for an AI profile of any wallet.",
    },
    "pay": {
        "title": "Send PROS",
        "purpose": "Send PROS to any address using plain English.",
        "steps": [
            "Connect your wallet.",
            "Go to the **Pay** page.",
            'Type what you want, e.g. "Send 5 PROS to 0x1234…".',
            "Review the parsed recipient, amount and network carefully.",
            "Confirm — your wallet signs the transaction; the app never holds your keys.",
        ],
        "prereq": ["Wallet connected", "Wallet on Pharos", "Enough PROS for the amount + gas"],
        "warn": "Transfers are irreversible. Always double-check the recipient address — the first "
                "and last four characters are not enough, check the middle too. Gas is paid in PROS.",
        "next": "Track it in **DeFi → History** or on PharosScan.",
    },
    "campaigns": {
        "title": "Join a campaign",
        "purpose": "Live opportunities across the Pharos ecosystem.",
        "steps": [
            "Go to the **Campaigns** page.",
            "Browse the live campaigns and read the tag/summary.",
            "Click **Join** on one — it opens the official campaign site.",
            "Connect the same wallet there and follow their steps.",
        ],
        "prereq": ["Usually a wallet", "Some campaigns need PROS for gas"],
        "warn": "Only use links from this page or official Pharos channels — campaign phishing "
                "is common. Never sign a transaction you don't understand.",
        "next": "Check **Updates** for newly announced campaigns.",
    },
}

_FEATURE_KEYWORDS = [
    ("connect_wallet", ("connect wallet", "connect my wallet", "link wallet", "metamask",
                        "wallet connect", "sign in", "log in", "switch network",
                        "wrong network", "add pharos", "chain 1672", "disconnect")),
    ("portfolio",  ("portfolio", "my balance", "balances", "holdings", "my tokens", "how much do i have")),
    ("swap",       ("swap", "swapping", "trade token", "trading token", "exchange token",
                    "faroswap", "dex")),
    ("bridge",     ("bridge", "bridging", "cross-chain", "cross chain", "transfer from ethereum",
                    "jumper", "li.fi", "lifi", "cctp", "ccip", "layerzero")),
    ("staking",    ("stake", "staking", "unstake", "unstaking", "stpros", "apr", "apy",
                    "yield", "rewards")),
    ("wallet_score", ("wallet score", "my score", "reputation", "wallet analysis", "analyse my wallet")),
    ("history",    ("transaction history", "my transactions", "tx history", "past transactions")),
    ("rwa_market", ("rwa market", "rwa price", "market dashboard", "ondo", "paxg")),
    ("explorer",   ("explorer", "look up transaction", "check transaction", "inspect address",
                    "tx hash", "transaction hash")),
    ("pay",        ("send pros", "pay ", "payment", "transfer pros", "send tokens", "send money")),
    ("campaigns",  ("campaign", "quest", "airdrop", "expedition", "join event")),
]

_HOWTO_HINTS = ("how do i", "how to", "how can i", "walk me through", "steps to", "guide me",
                "show me how", "where do i", "where can i", "help me", "teach me", "can i")

def detect_app_feature(q: str):
    """Route a question to an in-app feature guide, or None for docs RAG.

    Deliberately conservative: it only fires when the question is about
    DOING something in this app. Conceptual questions ("what is a bridge?")
    fall through to the docs index, which answers them better.
    """
    ql = (q or "").lower().strip()
    if not ql:
        return None
    hit = None
    for key, words in _FEATURE_KEYWORDS:
        if any(w in ql for w in words):
            hit = key
            break
    if not hit:
        return None
    # "How do I X" / "where is X" → definitely a how-to.
    if any(h in ql for h in _HOWTO_HINTS):
        return hit
    # Bare feature mentions ("staking?", "connect wallet") are how-tos too.
    if len(ql.split()) <= 6:
        return hit
    # Conceptual phrasing → let the docs answer.
    if ql.startswith(("what is", "what are", "why ", "explain ")):
        return None
    return hit

def render_feature_guide(key: str) -> str:
    """Markdown answer for an in-app feature, grounded in the real UI."""
    f = APP_FEATURES.get(key)
    if not f:
        return ""
    out = ["### " + f["title"], "", f["purpose"], ""]
    if f.get("prereq"):
        out.append("**Before you start**")
        out += ["- " + p for p in f["prereq"]]
        out.append("")
    out.append("**Steps**")
    out += [f"{i}. {s}" for i, s in enumerate(f["steps"], 1)]
    out.append("")
    if f.get("warn"):
        out += ["> ⚠️ **Important:** " + f["warn"], ""]
    if f.get("next"):
        out.append("**Next:** " + f["next"])
    return "\n".join(out)


@st.cache_resource(show_spinner=False)
def _octobot_holder() -> dict:
    """Process-wide shared state for the OctoBot instance.

    'ready' lets the UI thread BLOCK on initialisation instead of
    spin-rerunning the whole script, which was the real cause of the
    long "Loading Knowledge Base" hang.
    """
    return {"bot": None, "error": None, "done": False,
            "started": False, "started_at": None,
            "ready": threading.Event()}

def _octobot_worker(holder: dict) -> None:
    try:
        from octobot import OctoBot
        bot = OctoBot()
        # Touch the vectorstore once here so a broken/missing index
        # fails fast with a clear message instead of failing later.
        try:
            holder["chunk_count"] = bot.vectorstore._collection.count()
        except Exception:
            holder["chunk_count"] = None
        holder["bot"] = bot
    except Exception as e:
        holder["error"] = str(e) or e.__class__.__name__
    finally:
        holder["done"] = True
        try:
            holder["ready"].set()
        except Exception:
            pass

def _octobot_reset() -> None:
    """Allow a clean retry after a failure/timeout."""
    try:
        _octobot_holder.clear()
    except Exception:
        pass

def load_octobot(start: bool = True) -> dict:
    """Kick off (once) and report OctoBot initialisation state.
    Returns the shared holder: {bot, error, done, started_at, ...}."""
    holder = _octobot_holder()
    if start:
        with _octobot_lock:
            if not holder["started"]:
                holder["started"] = True
                holder["started_at"] = time.time()
                threading.Thread(
                    target=_octobot_worker, args=(holder,), daemon=True,
                    name="octobot-init",
                ).start()
    # Hard timeout: never allow an infinite loading state.
    if (holder["started"] and not holder["done"]
            and holder["started_at"]
            and time.time() - holder["started_at"] > OCTOBOT_INIT_TIMEOUT):
        holder["error"] = (
            f"Knowledge base initialisation timed out after {OCTOBOT_INIT_TIMEOUT}s. "
            "Check network access for the embedding model, and that the "
            "vectorstore exists (run `python build_vectorstore.py`)."
        )
        holder["done"] = True
        try:
            holder["ready"].set()
        except Exception:
            pass
    return holder


def octobot_wait(seconds: float = 8.0) -> dict:
    """Block this script run (not the whole server) until OctoBot is
    ready, or `seconds` elapse. Streamlit runs each session's script on
    its own thread, so waiting here keeps THIS tab's loading screen up
    while other sessions stay responsive — and, crucially, does not
    re-execute the entire page every 350ms the way the old poll loop
    did. That rerun storm was competing with the init worker for CPU
    and made loading take far longer than the work itself.
    """
    holder = load_octobot()
    if not holder["done"]:
        remaining = OCTOBOT_INIT_TIMEOUT
        if holder.get("started_at"):
            remaining = OCTOBOT_INIT_TIMEOUT - (time.time() - holder["started_at"])
        try:
            holder["ready"].wait(timeout=max(0.0, min(seconds, remaining)))
        except Exception:
            time.sleep(min(seconds, 1.0))
        # Re-evaluate so the hard timeout is applied on this pass too.
        holder = load_octobot()
    return holder

# ─────────────────────────────────────────────
# MARKET & COMMUNITY PULSE — helpers
# Additive feature: live market data (CoinMarketCap when a key is
# configured, CoinGecko as the automatic fallback), AI community
# sentiment + discussion summary + trending topics (Gemini, with a
# deterministic fallback built from the REAL market numbers — same
# philosophy as explain_transaction / synthesize_wallet_profile).
# ─────────────────────────────────────────────
PULSE_CACHE = 300
PULSE_AI_CACHE = 600

def fetch_market_pulse() -> dict:
    """Live PROS market snapshot. CoinMarketCap first (if CMC_API_KEY /
    COINMARKETCAP_API_KEY is set), CoinGecko otherwise. Cached 5 min."""
    now = time.time()
    cached = st.session_state.get("pulse_market_cache", {})
    if cached.get("data") and now - cached.get("fetched_at", 0) < PULSE_CACHE:
        return cached["data"]

    data = {"available": False, "source": ""}

    cmc_key = os.getenv("CMC_API_KEY") or os.getenv("COINMARKETCAP_API_KEY")
    if cmc_key:
        try:
            r = requests.get(
                "https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest",
                params={"slug": "pharos-network", "convert": "USD"},
                headers={"X-CMC_PRO_API_KEY": cmc_key, "Accept": "application/json"},
                timeout=6,
            )
            if r.status_code == 200:
                raw = r.json().get("data", {})
                coin = next(iter(raw.values()), None)
                if isinstance(coin, list):
                    coin = coin[0] if coin else None
                if coin:
                    q = coin.get("quote", {}).get("USD", {})
                    data = {
                        "available": True, "source": "CoinMarketCap",
                        "price":  q.get("price"),
                        "chg24":  q.get("percent_change_24h"),
                        "chg7d":  q.get("percent_change_7d"),
                        "chg30d": q.get("percent_change_30d"),
                        "mcap":   q.get("market_cap"),
                        "vol24":  q.get("volume_24h"),
                        "rank":   coin.get("cmc_rank"),
                        "supply": coin.get("circulating_supply"),
                        "ath": None, "ath_chg": None,
                    }
        except Exception:
            pass

    if not data.get("available"):
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/coins/" + COINGECKO_ASSET_ID,
                params={
                    "localization": "false", "tickers": "false",
                    "market_data": "true", "community_data": "false",
                    "developer_data": "false", "sparkline": "false",
                },
                headers={"Accept": "application/json"}, timeout=6,
            )
            if r.status_code == 200:
                md = r.json().get("market_data", {})
                data = {
                    "available": True, "source": "CoinGecko",
                    "price":  (md.get("current_price") or {}).get("usd"),
                    "chg24":  md.get("price_change_percentage_24h"),
                    "chg7d":  md.get("price_change_percentage_7d"),
                    "chg30d": md.get("price_change_percentage_30d"),
                    "mcap":   (md.get("market_cap") or {}).get("usd"),
                    "vol24":  (md.get("total_volume") or {}).get("usd"),
                    "rank":   md.get("market_cap_rank") or r.json().get("market_cap_rank"),
                    "supply": md.get("circulating_supply"),
                    "ath":    (md.get("ath") or {}).get("usd"),
                    "ath_chg": (md.get("ath_change_percentage") or {}).get("usd"),
                }
        except Exception:
            pass

    if data.get("available"):
        st.session_state["pulse_market_cache"] = {"data": data, "fetched_at": now}
    return data if data.get("available") else (cached.get("data") or data)


def compute_community_pulse(market: dict, news: list) -> dict:
    """Sentiment (Bullish/Neutral/Bearish + 0-100 score), an AI summary of
    recent discussion, and trending topics. Gemini-refined when available,
    ALWAYS falls back to a deterministic read of the real market numbers."""
    now = time.time()
    cached = st.session_state.get("pulse_ai_cache", {})
    if cached.get("data") and now - cached.get("fetched_at", 0) < PULSE_AI_CACHE:
        return cached["data"]

    chg24 = (market or {}).get("chg24") or 0.0
    chg7d = (market or {}).get("chg7d") or 0.0
    price = (market or {}).get("price")

    def deterministic_pulse():
        score = max(2, min(98, round(50 + chg24 * 3.0 + chg7d * 1.2)))
        label = "Bullish" if score >= 60 else ("Bearish" if score <= 40 else "Neutral")
        d24 = ("up " if chg24 >= 0 else "down ") + f"{abs(chg24):.2f}% over 24h"
        d7  = ("up " if chg7d >= 0 else "down ") + f"{abs(chg7d):.2f}% on the week"
        px  = f"${price:,.4f}" if price else "its current level"
        summary = (
            "Community discussion is tracking price action closely: $PROS is trading at "
            + px + ", " + d24 + " and " + d7 + ". "
            + ("Momentum is constructive and conversations lean toward accumulation, SPN restaking "
               "yields and new campaign rewards." if label == "Bullish" else
               ("Sentiment is cautious — traders are watching support levels while builders keep "
                "shipping on SPNs and RWA integrations." if label == "Bearish" else
                "The tone is balanced — traders are range-watching while attention rotates toward "
                "SPNs, x402 payments and active campaigns."))
        )
        topics = ["$PROS price action", "SPNs & restaking", "RWA / RealFi", "x402 payments", "Active campaigns"]
        for art in (news or [])[:3]:
            t = (art.get("title") or "").strip()
            if t and len(t) < 46 and t not in topics:
                topics.insert(2, t)
        return {"label": label, "score": score, "summary": summary, "topics": topics[:6], "ai": False}

    result = deterministic_pulse()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            titles = "; ".join([(a.get("title") or "")[:90] for a in (news or [])[:6]]) or "(none)"
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.4, google_api_key=api_key)
            prompt = (
                "You are a crypto community analyst for the Pharos Network ($PROS). "
                "Given the live data below, respond with ONLY a JSON object (no markdown, no backticks) "
                'shaped exactly like {"label":"Bullish|Neutral|Bearish","score":0-100,'
                '"summary":"2-3 sentence summary of recent community discussion, grounded in the data",'
                '"topics":["5 short trending topic strings"]}.\n'
                f"Price: {price} USD; 24h change: {chg24:.2f}%; 7d change: {chg7d:.2f}%. "
                "Recent headlines: " + titles
            )
            resp = llm.invoke([HumanMessage(content=prompt)])
            raw = (resp.content or "").strip()
            raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()
            parsed = json.loads(raw)
            label = str(parsed.get("label", "")).title()
            score = int(parsed.get("score", result["score"]))
            if label in ("Bullish", "Neutral", "Bearish") and 0 <= score <= 100:
                topics = [str(t)[:60] for t in (parsed.get("topics") or []) if str(t).strip()][:6]
                result = {
                    "label": label, "score": score,
                    "summary": str(parsed.get("summary", ""))[:600] or result["summary"],
                    "topics": topics or result["topics"],
                    "ai": True,
                }
        except Exception:
            pass

    st.session_state["pulse_ai_cache"] = {"data": result, "fetched_at": now}
    return result


def render_sentiment_orb() -> None:
    """Floating, glossy 3D crystal-orb shortcut on the Home page that
    opens the Market & Community Pulse page. GSAP-animated (cdnjs):
    slow float, pulsing live glow, orbiting up-arrow, hover parallax
    tilt + 1.08x scale, click ripple, then a fluid page transition via
    the parent-document __pnavGo helper (falls back to a direct click
    on the hidden nav_pulse button). Honors prefers-reduced-motion."""
    components.html(
        """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@400;500&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;}
html,body{background:transparent;overflow:hidden;}
.stage{
    width:100%;height:108px;
    display:flex;align-items:flex-start;justify-content:center;
    padding:6px 0 0 0;
    perspective:600px;-webkit-tap-highlight-color:transparent;
    user-select:none;
}
.col{
    display:flex;flex-direction:column;align-items:center;
    width:108px;cursor:pointer;
}
.orb3d{position:relative;width:48px;height:48px;transform-style:preserve-3d;will-change:transform;}
/* pulsing outer glow — signals live updates */
.glowring{
    position:absolute;inset:-10px;border-radius:50%;
    background:radial-gradient(circle,
        rgba(26,26,255,0.45) 0%,
        rgba(107,140,255,0.26) 42%,
        rgba(107,140,255,0) 72%);
    will-change:transform,opacity;pointer-events:none;
}
/* the glossy crystal orb */
.orb{
    position:absolute;inset:5px;border-radius:50%;
    background:
        radial-gradient(circle at 32% 26%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0) 26%),
        radial-gradient(circle at 66% 78%, rgba(107,140,255,0.85) 0%, rgba(107,140,255,0) 46%),
        conic-gradient(from 210deg,
            rgba(255,255,255,0.16) 0deg, rgba(255,255,255,0) 55deg,
            rgba(255,255,255,0.10) 130deg, rgba(255,255,255,0) 200deg,
            rgba(255,255,255,0.14) 300deg, rgba(255,255,255,0) 360deg),
        radial-gradient(circle at 50% 46%, #6B8CFF 0%, #2D2DE0 52%, #0C0CB4 100%);
    box-shadow:
        0 8px 20px rgba(26,26,255,0.34),
        inset 0 -7px 13px rgba(6,6,90,0.55),
        inset 0 5px 9px rgba(255,255,255,0.35),
        inset 0 0 0 1px rgba(255,255,255,0.18);
    will-change:transform;
}
/* crisp specular highlight — the "glass" read */
.spec{
    position:absolute;left:34%;top:16%;width:34%;height:22%;
    border-radius:50%;
    background:linear-gradient(180deg,rgba(255,255,255,0.9),rgba(255,255,255,0));
    filter:blur(1.5px);transform:rotate(-18deg);pointer-events:none;
}
/* soft contact shadow under the floating orb */
.shadow{
    position:absolute;left:50%;bottom:-7px;width:30px;height:6px;
    transform:translateX(-50%);border-radius:50%;
    background:radial-gradient(ellipse,rgba(12,12,60,0.28) 0%,rgba(12,12,60,0) 70%);
    will-change:transform,opacity;pointer-events:none;
}
/* orbiting up-arrow — market movement */
.orbit{position:absolute;inset:-2px;will-change:transform;pointer-events:none;}
.arrowchip{
    position:absolute;top:-2px;left:50%;margin-left:-7px;
    width:14px;height:14px;border-radius:50%;
    background:linear-gradient(160deg,#2BE080,#0FA860);
    box-shadow:0 3px 10px rgba(20,190,110,0.45),inset 0 1px 0 rgba(255,255,255,0.4);
    display:flex;align-items:center;justify-content:center;
    will-change:transform;
}
.arrowchip svg{width:8px;height:8px;display:block;}
/* ripple on click */
.ripple{
    position:absolute;inset:5px;border-radius:50%;
    border:2px solid rgba(107,140,255,0.9);
    opacity:0;transform:scale(1);pointer-events:none;will-change:transform,opacity;
}
/* label */
.label{
    margin-top:9px;font-family:'Syne',sans-serif;
    font-size:9px;font-weight:800;letter-spacing:0.03em;white-space:nowrap;
    color:#0C0C1A;opacity:1;
    display:flex;align-items:center;gap:5px;
    background:rgba(255,255,255,0.92);
    border:1px solid #E2E4EE;border-radius:8px;
    padding:3px 8px;
    box-shadow:0 2px 8px rgba(20,20,60,0.10);
    transition:letter-spacing 220ms cubic-bezier(0.4,0,0.2,1),box-shadow 220ms ease;
}
.label .live{
    width:4px;height:4px;border-radius:50%;background:#1FA855;
    box-shadow:0 0 5px #1FA855;
}
.col:hover .label{letter-spacing:0.06em;box-shadow:0 4px 14px rgba(26,26,255,0.22);}
.sub{
    margin-top:3px;font-family:'DM Sans',sans-serif;font-size:8px;font-weight:600;
    color:#3D4358;white-space:nowrap;
    background:rgba(255,255,255,0.75);border-radius:6px;padding:1px 6px;
}
@media (prefers-reduced-motion: reduce){
    .glowring{opacity:0.5;}
}
</style>
</head>
<body>
<div class="stage">
 <div class="col" id="stage" role="button" aria-label="Check Sentiment — open Market and Community Pulse" title="Market &amp; Community Pulse">
  <div class="orb3d" id="orb3d">
    <div class="glowring" id="glow"></div>
    <div class="orb" id="orb"><div class="spec"></div></div>
    <div class="ripple" id="ripple"></div>
    <div class="orbit" id="orbit">
      <div class="arrowchip" id="chip">
        <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 19V5"></path><path d="M5.5 11.5 12 5l6.5 6.5"></path>
        </svg>
      </div>
    </div>
    <div class="shadow" id="shadow"></div>
  </div>
  <div class="label"><span class="live"></span>Check Sentiment</div>
  <div class="sub">Market &amp; Community Pulse</div>
 </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js"></script>
<script>
(function(){
  /* Pin this component to the extreme top-left corner of the viewport
     (fixed, out of the page flow) by styling its own iframe container
     from the inside — inline styles, no selector guessing, so the
     Home hero and cards keep their original positions. */
  window.__isOrb = true;   /* identity flag: lets the parent-side cleaner
                              verify that a pinned container still hosts
                              THIS orb (Streamlit recycles DOM nodes across
                              pages, so pins must be validated, not trusted) */
  try{
    var fe = window.frameElement;
    if (fe){
      fe.style.width = '112px';
      fe.style.height = '112px';
      var holder = (fe.closest && fe.closest('[data-testid="stElementContainer"]')) || fe.parentElement;
      if (holder){
        holder.setAttribute('data-orb-holder', '1');
        holder.style.position = 'fixed';
        holder.style.width  = '112px';
        holder.style.height = '112px';
        holder.style.zIndex = '901';
        holder.style.margin = '0';
        holder.style.padding = '0';
        var pw = window.parent;
        var mq = (pw && pw.matchMedia) ? pw.matchMedia('(max-width: 900px)') : null;
        var place = function(){
          if (mq && mq.matches){
            holder.style.top = 'auto'; holder.style.bottom = '12px'; holder.style.left = '0px';
          } else {
            holder.style.bottom = 'auto'; holder.style.top = '94px'; holder.style.left = '0px';
          }
        };
        place();
        if (mq && mq.addEventListener) mq.addEventListener('change', place);
      }
    }
  }catch(e){}

  var stage  = document.getElementById('stage');
  var orb3d  = document.getElementById('orb3d');
  var glow   = document.getElementById('glow');
  var orbit  = document.getElementById('orbit');
  var chip   = document.getElementById('chip');
  var shadow = document.getElementById('shadow');
  var ripple = document.getElementById('ripple');
  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var floatTl = null, rotX = null, rotY = null;

  if (window.gsap && !reduced){
    /* slow vertical float (intensified on hover) */
    floatTl = gsap.to(orb3d, {y:-4, duration:2.6, ease:'sine.inOut', yoyo:true, repeat:-1});
    /* pulsing live glow */
    gsap.to(glow, {scale:1.16, opacity:0.55, duration:1.9, ease:'sine.inOut', yoyo:true, repeat:-1});
    /* shadow breathes opposite the float */
    gsap.to(shadow, {scale:0.82, opacity:0.6, duration:2.6, ease:'sine.inOut', yoyo:true, repeat:-1});
    /* up-arrow orbits the orb; chip counter-rotates so the arrow stays upright */
    gsap.to(orbit, {rotation:360, duration:7, ease:'none', repeat:-1});
    gsap.to(chip,  {rotation:-360, duration:7, ease:'none', repeat:-1});
    /* hover parallax tilt (snappy, 60fps quickTo) */
    rotX = gsap.quickTo(orb3d, 'rotationX', {duration:0.4, ease:'power2.out'});
    rotY = gsap.quickTo(orb3d, 'rotationY', {duration:0.4, ease:'power2.out'});
  }

  stage.addEventListener('mousemove', function(e){
    if (!rotX) return;
    var r = orb3d.getBoundingClientRect();
    var nx = ((e.clientX - r.left) / r.width  - 0.5) * 2;
    var ny = ((e.clientY - r.top ) / r.height - 0.5) * 2;
    rotX(-ny * 10); rotY(nx * 10);
  });
  stage.addEventListener('mouseenter', function(){
    if (!window.gsap || reduced) return;
    gsap.to(orb3d, {scale:1.08, duration:0.32, ease:'back.out(2)'});
    gsap.to(glow,  {opacity:1, duration:0.3, ease:'power2.out'});
    if (floatTl) floatTl.timeScale(1.7);
  });
  stage.addEventListener('mouseleave', function(){
    if (!window.gsap || reduced){ return; }
    gsap.to(orb3d, {scale:1, rotationX:0, rotationY:0, duration:0.45, ease:'power3.out'});
    gsap.to(glow,  {opacity:0.8, duration:0.5, ease:'power2.out'});
    if (floatTl) floatTl.timeScale(1);
  });

  function navigate(){
    var done = false;
    try{
      if (window.parent && typeof window.parent.__pnavGo === 'function'){
        window.parent.__pnavGo('pulse'); done = true;
      }
    }catch(e){}
    if (!done){
      try{
        var btn = window.parent.document.querySelector('[class*="st-key-nav_pulse"] button');
        if (btn) btn.click();
      }catch(e2){}
    }
  }
  stage.addEventListener('click', function(){
    if (window.gsap && !reduced){
      gsap.fromTo(ripple, {scale:1, opacity:0.9},
        {scale:2.1, opacity:0, duration:0.55, ease:'power2.out'});
      gsap.to(orb3d, {scale:0.94, duration:0.09, ease:'power2.in', yoyo:true, repeat:1});
      setTimeout(navigate, 180);
    } else {
      navigate();
    }
  });
})();
</script>
</body>
</html>
        """,
        height=112,
        scrolling=False,
    )


# ─────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800'
    '&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400'
    '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# CSS — unified across all pages
# ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
    /* Brand */
    --blue:      #1A1AFF;
    --blue2:     #2D2DE0;
    --light:     #6B8CFF;

    /* Effects */
    --glow:      rgba(26,26,255,0.22);
    --subtle:    rgba(26,26,255,0.10);

    /* Background — cool slate blue-gray, cinematic depth */
    --bg:        #9DAABF;
    --bg1:       #A8B6CC;
    --bg2:       #97A5BB;

    /* Glass — slightly more opaque for better contrast */
    --glass:     rgba(248,251,255,0.80);

    /* Borders — more visible against darker bg */
    --border:    #A4B0C8;
    --border2:   #97A5BE;

    /* Text — unchanged, already optimal */
    --t1:        #0B1020;
    --t2:        #39445D;
    --t3:        #68738C;

    /* Status */
    --green:     #1FA855;
    --red:       #E5484D;

    /* Fonts */
    --fd:        'Syne', sans-serif;
    --fb:        'DM Sans', sans-serif;

    /* Radius */
    --rad:       12px;
    --rad-lg:    18px;

    /* Shadows — slightly deeper for more card lift */
    --shadow:        0 8px 28px rgba(14,22,52,0.12);
    --shadow-md:     0 16px 44px rgba(14,22,52,0.16);
    --shadow-blue:   0 10px 36px rgba(26,26,255,0.20);
}
            /* Design*/
body {
    background:
        radial-gradient(circle at 15% 20%, rgba(26,26,255,.16), transparent 35%),
        radial-gradient(circle at 85% 30%, rgba(80,110,220,.12), transparent 40%),
        radial-gradient(circle at 50% 100%, rgba(200,215,255,.18), transparent 50%),
        linear-gradient(180deg, var(--bg1), var(--bg), var(--bg2));
}
html,body,[class*="css"]{font-family:var(--fb)!important;background-color:#9DAABF!important;color:var(--t1)!important;font-size:14px!important;}

/* ══════════════════════════════════════════════════════════
   DARK MODE — data-theme="dark" on <html>, toggled from the nav.
   Re-points design tokens + re-skins hard-coded light surfaces.
   ══════════════════════════════════════════════════════════ */
html[data-theme="dark"]{
    --bg:      #0B0E1A;
    --bg1:     #10131F;
    --bg2:     #080A14;
    --glass:   rgba(24,28,44,0.72);
    --border:  #262B3E;
    --border2: #2E3448;
    --t1:      #EDEFF7;
    --t2:      #AEB4C8;
    --t3:      #7B8199;
    --shadow:      0 8px 28px rgba(0,0,0,0.45);
    --shadow-md:   0 16px 44px rgba(0,0,0,0.55);
    --shadow-blue: 0 10px 36px rgba(60,80,255,0.30);
}
html[data-theme="dark"] body{
    background:
        radial-gradient(circle at 15% 20%, rgba(60,80,255,.16), transparent 38%),
        radial-gradient(circle at 85% 30%, rgba(60,90,200,.12), transparent 42%),
        radial-gradient(circle at 50% 100%, rgba(30,40,90,.30), transparent 55%),
        linear-gradient(180deg, #10131F, #0B0E1A, #070912) !important;
    background-color:#0B0E1A !important;
}
html[data-theme="dark"] .stApp{ background-color:#0B0E1A !important; }
html[data-theme="dark"], html[data-theme="dark"] body,
html[data-theme="dark"] [class*="css"]{ background-color:#0B0E1A !important; color:var(--t1)!important; }

/* Nav pill */
html[data-theme="dark"] .pnav{
    background:rgba(18,21,34,0.94);
    border-color:#262B3E;
    box-shadow:0 2px 18px rgba(0,0,0,0.5);
}
html[data-theme="dark"] .pnav-ver{background:#181C2C;border-color:#2A3044;color:#C4C9DC;}
html[data-theme="dark"] .pnav-item{color:#C4C9DC;}
html[data-theme="dark"] .pnav-item:hover,html[data-theme="dark"] .pnav-item.on{color:#FFFFFF;}
html[data-theme="dark"] .pnav-search{background:#12151F;border-color:#252A3B;color:#8A90A6;}
html[data-theme="dark"] .pnav-search:hover{background:#181C2A;border-color:#333A50;}
html[data-theme="dark"] .pnav-kbd{background:#1B1F30;border-color:#2C3247;color:#AEB4C8;}
html[data-theme="dark"] .pnav-icirc{background:#1B1F2E;border-color:#2E3448;color:#F2F4FB;}
html[data-theme="dark"] .pnav-icirc svg{color:#F2F4FB;fill:#F2F4FB;}
html[data-theme="dark"] .pnav-icirc:hover{background:#242A3C;border-color:#454E68;color:#FFFFFF;}
html[data-theme="dark"] .pnav-icirc:hover svg{color:#FFFFFF;fill:#FFFFFF;}
html[data-theme="dark"] .pnav-dd{background:#141826;border-color:#262B3E;box-shadow:0 14px 40px rgba(0,0,0,0.6);}
html[data-theme="dark"] .pnav-dd-item{color:#C4C9DC;}
html[data-theme="dark"] .pnav-dd-item:hover{background:#1C2132;color:#FFFFFF;}
html[data-theme="dark"] .pnav-dd-item.on{background:rgba(60,80,255,0.18);color:#9FB0FF;}
html[data-theme="dark"] .pnav-caret{border-color:#8A90A6;}

/* Sidebar */
html[data-theme="dark"] section[data-testid="stSidebar"]{
    background:#0C0F1A !important;border-right:1px solid #1E2333 !important;
}
html[data-theme="dark"] section[data-testid="stSidebar"]{
    background:#0C0F1A !important;border-right:1px solid #1E2333 !important;
}
html[data-theme="dark"] [data-testid="stSidebar"]{
    background:#0C0F1A !important;border-right:1px solid #1E2333 !important;
}
/* Override the sidebar's hard-coded light !important text colours */
html[data-theme="dark"] [data-testid="stSidebar"] label,
html[data-theme="dark"] [data-testid="stSidebar"] p,
html[data-theme="dark"] [data-testid="stSidebar"] div,
html[data-theme="dark"] [data-testid="stSidebar"] span,
html[data-theme="dark"] [data-testid="stSidebar"] h1,
html[data-theme="dark"] [data-testid="stSidebar"] h2,
html[data-theme="dark"] [data-testid="stSidebar"] h3{
    color:#DDE0EE !important;
}
/* Sidebar buttons → dark surface, readable text */
html[data-theme="dark"] [data-testid="stSidebar"] .stButton>button{
    color:#DDE0EE !important;
    background:#161A28 !important;
    border:1px solid #2A3044 !important;
}
html[data-theme="dark"] [data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(90,110,255,0.14) !important;
    border-color:#5A6EFF !important;color:#9FB0FF !important;
}
html[data-theme="dark"] [data-testid="stSidebar"] .stButton>button *{color:inherit !important;}
/* Sidebar dividers/rules blend into the dark panel */
html[data-theme="dark"] [data-testid="stSidebar"] hr{border-color:#1E2333 !important;}
/* Uppercase section captions ("CONVERSATION", "SETTINGS", etc.) */
html[data-theme="dark"] [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *{color:#C4C9DC !important;}

/* Generic light surfaces → dark glass. Global (not markdown-scoped) so
   every inline white/near-white card is re-skinned wherever it lives. */
html[data-theme="dark"] [style*="background:#FFFFFF"],
html[data-theme="dark"] [style*="background: #FFFFFF"],
html[data-theme="dark"] [style*="background:#fff"],
html[data-theme="dark"] [style*="background: #fff"],
html[data-theme="dark"] [style*="background:#FFF"],
html[data-theme="dark"] [style*="background:#F4F5F8"],
html[data-theme="dark"] [style*="background:#F7F8FA"],
html[data-theme="dark"] [style*="background:#F8FAFF"],
html[data-theme="dark"] [style*="background:#FAFBFF"]{
    background:#141826 !important;
    border-color:#262B3E !important;
}
/* Any element inside a dark-skinned card that still has near-black text
   flips to light — but only these dark inks, never coloured accents.
   .camp-title/.camp-desc use --t1/--t2 which are already re-pointed. */
html[data-theme="dark"] .camp-title,
html[data-theme="dark"] .cex-name,
html[data-theme="dark"] .dapp-name,
html[data-theme="dark"] .news-title,
html[data-theme="dark"] .news-title a{ color:#EDEFF7 !important; }
html[data-theme="dark"] .camp-desc,
html[data-theme="dark"] .dapp-desc{ color:#AEB4C8 !important; }

/* Streamlit-native widget text: toggle/checkbox labels, captions,
   alerts, expander headers, strong/em inside markdown. These inherit
   colour rather than carrying an inline style, so target them directly. */
html[data-theme="dark"] [data-testid="stMarkdownContainer"] strong,
html[data-theme="dark"] [data-testid="stMarkdownContainer"] em,
html[data-theme="dark"] [data-testid="stMarkdownContainer"] a,
html[data-theme="dark"] [data-testid="stWidgetLabel"] *,
html[data-theme="dark"] [data-testid="stToggle"] label,
html[data-theme="dark"] [data-testid="stCheckbox"] label,
html[data-theme="dark"] [data-baseweb="checkbox"] *,
html[data-theme="dark"] [data-testid="stCaptionContainer"],
html[data-theme="dark"] [data-testid="stCaptionContainer"] *,
html[data-theme="dark"] .stRadio label,
html[data-theme="dark"] .stSelectbox label,
html[data-theme="dark"] summary,
html[data-theme="dark"] [data-testid="stExpander"] summary *{
    color:#DDE0EE !important;
}
/* Keep hyperlink accents visibly blue (not washed to grey) */
html[data-theme="dark"] [data-testid="stMarkdownContainer"] a[href]{
    color:#8FA6FF !important;
}
/* Alerts (st.warning/info/error) — readable text on their tinted bg */
html[data-theme="dark"] [data-testid="stAlert"],
html[data-theme="dark"] [data-testid="stAlert"] *,
html[data-theme="dark"] [data-testid="stNotification"] *{
    color:#F2F4FB !important;
}
html[data-theme="dark"] .notice{ color:#F2F4FB !important; }
/* Compact chat control panel — dark skin */


/* Remaining light card / panel backgrounds → dark glass */
html[data-theme="dark"] [style*="background:#F9FAFC"],
html[data-theme="dark"] [style*="background:#F5F6FA"],
html[data-theme="dark"] [style*="background:#EEF0F5"],
html[data-theme="dark"] [style*="background:#E8EBF2"],
html[data-theme="dark"] [style*="background:#ECEEF4"],
html[data-theme="dark"] [style*="background:#F0F2F8"],
html[data-theme="dark"] [style*="background:rgba(255,255,255"]{
    background:#141826 !important;
    border-color:#262B3E !important;
}
/* Dark input fields on the payment/wallet panels */
html[data-theme="dark"] [style*="background:#1A1F30"]{ color:#DDE0EE !important; }

html[data-theme="dark"] .glass-card,html[data-theme="dark"] .welcome-card,
html[data-theme="dark"] .camp-card,html[data-theme="dark"] .cex-card,
html[data-theme="dark"] .dapp-card,html[data-theme="dark"] .news-card,
html[data-theme="dark"] .build-path-card,html[data-theme="dark"] .chat-showcase{
    background:#141826 !important;border-color:#262B3E !important;
}

/* Campaign / Update / Ecosystem cards are <a class="hover-lift"> anchors
   with inline white backgrounds. Force those dark + their text light. */
html[data-theme="dark"] a.hover-lift[style*="background:#FFFFFF"],
html[data-theme="dark"] a.hover-lift{
    background:#141826 !important;border-color:#262B3E !important;
}
html[data-theme="dark"] .camp-title,
html[data-theme="dark"] .news-title,
html[data-theme="dark"] .news-title a,
html[data-theme="dark"] .dapp-name,
html[data-theme="dark"] .cex-name{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
html[data-theme="dark"] .camp-desc,
html[data-theme="dark"] .dapp-desc,
html[data-theme="dark"] .cex-sub,
html[data-theme="dark"] .news-desc{
    color:#AEB4C8 !important;-webkit-text-fill-color:#AEB4C8 !important;
}
/* Camp tag pills readable on dark */
html[data-theme="dark"] .camp-tag{
    background:rgba(90,110,255,0.14) !important;
    border-color:rgba(90,110,255,0.30) !important;
    color:#9FB0FF !important;
}
/* Campaign timeline / info cards (inline #FFFFFF divs on these pages) */
html[data-theme="dark"] [style*="background:#FFFFFF;border:1px solid #E3E5EA"]{
    background:#141826 !important;border-color:#262B3E !important;
}
/* Divider lines used in timelines */
html[data-theme="dark"] [style*="background:#E3E5EA"]{ background:#2A3044 !important; }
html[data-theme="dark"] .hover-lift:hover{
    box-shadow:0 18px 44px rgba(0,0,0,0.55),0 0 0 1.5px rgba(90,110,255,0.35)!important;
    border-color:rgba(90,110,255,0.4)!important;
}

/* ── Ecosystem DApp cards — theme-aware (light + dark) ── */
.eco-card{
    background:#FFFFFF;border:1px solid #ECEEF4;border-radius:16px;
    padding:1.2rem 1.3rem;display:flex;flex-direction:column;align-items:center;gap:0;
    text-align:center;text-decoration:none;box-shadow:0 1px 4px rgba(20,20,60,0.05);
    transition:transform 200ms cubic-bezier(0.34,1.4,0.64,1),box-shadow 200ms ease,border-color 180ms ease;
    cursor:pointer;
}
.eco-name{
    font-family:Syne,sans-serif;font-size:15px;font-weight:700;
    color:#0C0C1A;margin-bottom:0.4rem;line-height:1.2;
}
.eco-desc{
    font-size:12px;color:#5B5F6E;line-height:1.6;margin-bottom:0.75rem;flex:1;
}
.eco-tag{
    display:inline-block;font-size:11px;font-weight:500;color:#42475A;
    background:#F2F3F8;border:1px solid #E3E5EA;border-radius:6px;padding:3px 9px;
}
html[data-theme="dark"] .eco-card{
    background:#141826 !important;border-color:#262B3E !important;
    box-shadow:0 2px 10px rgba(0,0,0,0.35);
}
html[data-theme="dark"] .eco-name{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
html[data-theme="dark"] .eco-desc{
    color:#AEB4C8 !important;-webkit-text-fill-color:#AEB4C8 !important;
}
html[data-theme="dark"] .eco-tag{
    background:rgba(90,110,255,0.14) !important;
    border-color:rgba(90,110,255,0.30) !important;
    color:#9FB0FF !important;
}
/* Home hero live-price value — readable in both themes */
.hero-price-val{ color:#14141F; }
html[data-theme="dark"] .hero-price-val{ color:#EDEFF7 !important; }

/* ── Memory Ledger body cards — reinforce dark skinning for the inline
   #FFFFFF cards that carry explicit light borders (the global #FFFFFF
   rule skins the fill; these lock the borders + white quote panels). ── */
html[data-theme="dark"] [style*="border:1.5px solid #E3E5EA"]{
    background:#141826 !important;border-color:#262B3E !important;
}
html[data-theme="dark"] [style*="border:1px solid #E3E5EA"]{
    border-color:#262B3E !important;
}
html[data-theme="dark"] [style*="background:rgba(255,255,255,0.7)"]{
    background:rgba(255,255,255,0.06) !important;
}

/* Inputs / textareas / Streamlit buttons */
html[data-theme="dark"] input,html[data-theme="dark"] textarea,
html[data-theme="dark"] [data-baseweb="input"],html[data-theme="dark"] [data-baseweb="textarea"]{
    background:#12151F !important;color:#EDEFF7 !important;border-color:#262B3E !important;
}
html[data-theme="dark"] [data-testid="stChatInput"]{background:#12151F !important;border-color:#262B3E !important;}
html[data-theme="dark"] .stButton>button{
    background:#161A28 !important;color:#DDE0EE !important;border:1px solid #2A3044 !important;
}
html[data-theme="dark"] .stButton>button:hover{
    background:#1D2233 !important;border-color:#3A4260 !important;color:#FFFFFF !important;
}
/* Keep the aura canvas dots readable on dark */
html[data-theme="dark"] #aura-3d-canvas{mix-blend-mode:lighten;}

/* ══════════════════════════════════════════════════════════
   DARK MODE · automatic text-contrast adjust
   Near-black inline text (the app hard-codes #0C0C1A / #000 /
   #0B1020 / #1A1F30 in hundreds of inline styles) is flipped to a
   light ink in dark mode. Colored accents are left alone. Secondary
   greys are lifted so they stay readable. Reverses automatically in
   light mode (these rules simply don't apply). */
html[data-theme="dark"] [style*="color:#0C0C1A"],
html[data-theme="dark"] [style*="color: #0C0C1A"],
html[data-theme="dark"] [style*="color:#000000"],
html[data-theme="dark"] [style*="color: #000000"],
html[data-theme="dark"] [style*="color:#000;"],
html[data-theme="dark"] [style*="color:#000 "],
html[data-theme="dark"] [style*="color:#0B1020"],
html[data-theme="dark"] [style*="color: #0B1020"],
html[data-theme="dark"] [style*="color:#1A1F30"],
html[data-theme="dark"] [style*="color: #1A1F30"],
html[data-theme="dark"] [style*="color:#0c0c1a"],
html[data-theme="dark"] [style*="color:#14141F"],
html[data-theme="dark"] [style*="color: #14141F"],
html[data-theme="dark"] [style*="color:#14181F"],
html[data-theme="dark"] [style*="color:#1A1F30"],
html[data-theme="dark"] [style*="color:#17181C"],
html[data-theme="dark"] [style*="color:#2B3656"],
html[data-theme="dark"] [style*="color:#2C3247"],
html[data-theme="dark"] [style*="color:#262B3E"],
html[data-theme="dark"] [style*="color:#0B0E1A"],
html[data-theme="dark"] [style*="color:#1C1C28"],
html[data-theme="dark"] [style*="color:#111"]{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
/* Secondary / muted greys → lighter greys for readability */
html[data-theme="dark"] [style*="color:#39445D"],
html[data-theme="dark"] [style*="color:#42475A"],
html[data-theme="dark"] [style*="color:#3D4358"],
html[data-theme="dark"] [style*="color:#5B5F6E"],
html[data-theme="dark"] [style*="color:#68738C"],
html[data-theme="dark"] [style*="color:#4A4F60"],
html[data-theme="dark"] [style*="color:#52525B"],
html[data-theme="dark"] [style*="color:#7A7F96"],
html[data-theme="dark"] [style*="color:#9499A8"],
html[data-theme="dark"] [style*="color:#9AA0AE"],
html[data-theme="dark"] [style*="color:#6B7280"],
html[data-theme="dark"] [style*="color:#7C8BB8"],
html[data-theme="dark"] [style*="color:#3F3F46"],
html[data-theme="dark"] [style*="color:#5B5F6E"],
html[data-theme="dark"] [style*="color:#B0B4C4"],
html[data-theme="dark"] [style*="color:#8A90A6"]{
    color:#AEB4C8 !important;
}
/* Base Streamlit text nodes + headings that inherit --t1 */
html[data-theme="dark"] [data-testid="stMarkdownContainer"],
html[data-theme="dark"] [data-testid="stMarkdownContainer"] p,
html[data-theme="dark"] [data-testid="stMarkdownContainer"] li,
html[data-theme="dark"] h1,html[data-theme="dark"] h2,
html[data-theme="dark"] h3,html[data-theme="dark"] h4,
html[data-theme="dark"] label,html[data-theme="dark"] p{
    color:#EDEFF7;
}
/* Light-grey chip/pill backgrounds that used dark text → dark chips */
html[data-theme="dark"] [style*="background:#F2F3F8"],
html[data-theme="dark"] [style*="background:#F4F4F6"],
html[data-theme="dark"] [style*="background:#F4F5F9"],
html[data-theme="dark"] [style*="background:#EEF0FF"],
html[data-theme="dark"] [style*="background:#F6F8FF"],
html[data-theme="dark"] [style*="background:#EAEEFF"]{
    background:#1B2030 !important;border-color:#2A3044 !important;
}


.stApp{
    background-color: #B8C4D8!important;
    position:relative;
}
/* Wave texture moved to its own ::before layer so the drift animation
   can use `transform` (GPU-composited) instead of animating
   `background-position` directly on .stApp (CPU-only — forces a full
   repaint of the entire app's root background on every single frame,
   made worse by background-attachment:fixed). Visual result is
   identical; this only changes HOW the motion is computed. */
.stApp::before{
    content:'';
    position:fixed;
    inset:-60px;
    z-index:-1;
    pointer-events:none;
    will-change:transform;
    background-image:
        /* Ambient light source — top right, brighter for more depth */
        radial-gradient(ellipse 70% 55% at 78% 8%,  rgba(210,222,255,0.70) 0%, transparent 60%),
        /* Secondary light — bottom left */
        radial-gradient(ellipse 60% 50% at 12% 88%, rgba(185,205,255,0.42) 0%, transparent 50%),
        /* Mid tone depth */
        radial-gradient(ellipse 80% 60% at 50% 50%, rgba(170,190,235,0.18) 0%, transparent 60%),
        /* Cinematic radial vignette — subtle center-to-edge darkening */
        radial-gradient(ellipse 100% 80% at 50% 0%, rgba(255,255,255,0.10) 0%, transparent 70%),
        /* Wave band 1 — diagonal flow */
        repeating-linear-gradient(
            -28deg,
            transparent 0px,
            transparent 38px,
            rgba(140,165,210,0.12) 38px,
            rgba(140,165,210,0.12) 40px,
            transparent 40px,
            transparent 78px
        ),
        /* Wave band 2 — counter diagonal */
        repeating-linear-gradient(
            62deg,
            transparent 0px,
            transparent 55px,
            rgba(120,150,200,0.08) 55px,
            rgba(120,150,200,0.08) 57px,
            transparent 57px,
            transparent 114px
        ),
        /* Wave band 3 — shallow angle */
        repeating-linear-gradient(
            -12deg,
            transparent 0px,
            transparent 80px,
            rgba(150,175,220,0.07) 80px,
            rgba(150,175,220,0.07) 82px,
            transparent 82px,
            transparent 160px
        );
    animation: wave-shift 12s cubic-bezier(0.4,0,0.2,1) infinite;
}

 /* Snappy global baseline — overrides Streamlit's slower defaults */
*, *::before, *::after {
    transition-duration: 140ms !important;
    transition-timing-function: cubic-bezier(0.22,1,0.36,1) !important;
}
button, a, .stButton>button, [data-testid="stTextInput"] input,
.cex-card, .dapp-card, .camp-card, .news-card {
    transition-timing-function: cubic-bezier(0.4,0,0.2,1) !important;
}
/* The aura + dots background layers use `animation`, not `transition` —
   transition-duration has no effect on them either way, so the rule
   above is harmless to them. The earlier stutter was actually caused
   by the will-change catch-all further down this file; fixed there. */

/* Wave motion — was animating background-position (CPU repaint every
   frame); now animates transform on the dedicated .stApp::before
   layer instead, which the browser can composite on the GPU and skip
   re-painting entirely. The translate distances are scaled down
   slightly (transform moves the WHOLE layer, not individual gradient
   positions) to preserve the same subtle, slow drifting feel. */
@keyframes wave-shift {
    0%   { transform:translate(0px,0px) scale(1); }
    25%  { transform:translate(6px,3px) scale(1.006); }
    50%  { transform:translate(11px,6px) scale(1.012); }
    75%  { transform:translate(7px,4px) scale(1.007); }
    100% { transform:translate(0px,0px) scale(1); }
}

/* ═══════════════════════════════════════════════════════════
   GLOBAL BRAIN-AURA AMBIENT BACKGROUND — applies on every page
   Layered on top of the existing wave background above:
     1. Three large, slow-drifting aura glows (the "thinking" feel)
     2. A field of small moving dots (the "alive / neural" feel)
   Both sit at z-index:0 behind all real content (z-index:1) and
   use pointer-events:none so nothing is ever unclickable.
═══════════════════════════════════════════════════════════ */
@keyframes auraDrift1{
    0%{ transform:translate(0,0) scale(1); }
    25%{ transform:translate(40px,-44px) scale(1.12); }
    50%{ transform:translate(70px,-52px) scale(1.22); }
    75%{ transform:translate(34px,-22px) scale(1.10); }
    100%{ transform:translate(0,0) scale(1); }
}
@keyframes auraDrift2{
    0%{ transform:translate(0,0) scale(1); }
    25%{ transform:translate(-46px,38px) scale(1.09); }
    50%{ transform:translate(-82px,64px) scale(1.18); }
    75%{ transform:translate(-40px,30px) scale(1.08); }
    100%{ transform:translate(0,0) scale(1); }
}
@keyframes auraDrift3{
    0%{ transform:translate(0,0) scale(1); }
    25%{ transform:translate(32px,30px) scale(1.14); }
    50%{ transform:translate(54px,50px) scale(1.26); }
    75%{ transform:translate(28px,26px) scale(1.12); }
    100%{ transform:translate(0,0) scale(1); }
}
/* dotsFloat — was animating background-position across 4 layered dot
   patterns simultaneously (CPU repaint every frame). Converted to a
   single transform:translateY drift on the whole pseudo-element,
   which the GPU composites for free. The -300px top inset gives the
   pattern enough overscan room to drift without showing a seam at
   the edge, same purpose the background-position offset served. */
@keyframes dotsFloat{
    0%{ transform:translateY(0); }
    100%{ transform:translateY(-600px); }
}

[data-testid="stAppViewContainer"]{ position:relative; }

/* Layer 1 — four large soft glows, slowly drifting (whole-app aura) —
   this is now the DOMINANT visual layer.
   Previously ran 4 simultaneous `transform` animations on this single
   element (auraDrift1/2/3 plus a 4th reusing auraDrift2 in reverse) —
   since `transform` only ever resolves to one final matrix per frame,
   the browser had to interpolate and combine 4 keyframe curves every
   tick for a result barely different from 3. Dropped the redundant
   4th animation; visual richness is unchanged because all 4 gradient
   blobs still drift together as one composited layer. */
[data-testid="stAppViewContainer"]::before{
    content:'';
    position:fixed;
    inset:0;
    z-index:0;
    pointer-events:none;
    will-change:transform;
    background:
        radial-gradient(circle 620px at 14% 10%, rgba(10,10,100,0.55) 0%, transparent 72%),
        radial-gradient(circle 560px at 88% 22%, rgba(12,12,120,0.48) 0%, transparent 72%),
        radial-gradient(circle 640px at 46% 90%, rgba(8,8,90,0.44) 0%, transparent 72%),
        radial-gradient(circle 480px at 70% 60%, rgba(14,14,110,0.36) 0%, transparent 70%);
    animation:
        auraDrift1 9s ease-in-out infinite,
        auraDrift2 11s ease-in-out infinite,
        auraDrift3 13s ease-in-out infinite;
}

/* Layer 2 — sparse field of soft dots, now a subtle accent rather than
   the dominant effect. Fewer dots, more spacing, lower opacity, larger
   soft glow per dot so they read as gentle floating particles instead
   of a busy grid. */
[data-testid="stAppViewContainer"]::after{
    content:'';
    position:fixed;
    inset:-300px 0 0 0;
    z-index:0;
    pointer-events:none;
    will-change:transform;
    opacity:0.5;
    background-image:
        radial-gradient(circle 2px, rgba(8,8,80,0.8) 0%, transparent 100%),
        radial-gradient(circle 1.6px, rgba(10,10,100,0.75) 0%, transparent 100%),
        radial-gradient(circle 1.8px, rgba(6,6,70,0.7) 0%, transparent 100%),
        radial-gradient(circle 1.5px, rgba(12,12,90,0.8) 0%, transparent 100%);
    background-size:
        480px 480px, 560px 560px, 620px 620px, 700px 700px;
    background-position:
        40px 60px, 280px 180px, 140px 380px, 460px 80px;
    animation: dotsFloat 34s linear infinite;
}

/* Keep every real Streamlit block above both background layers */
[data-testid="stAppViewContainer"] > .main,
[data-testid="stHeader"],
section[data-testid="stSidebar"]{
    position:relative;
    z-index:1;
}

#MainMenu,footer,header,.stDeployButton{display:none!important;}

/* Hide the zero-height wrapper that holds hidden nav fallback buttons */
div[style*="height:0"][style*="overflow:hidden"][style*="visibility:hidden"]{
    display:none!important;
    height:0!important;
    overflow:hidden!important;
    margin:0!important;
    padding:0!important;
    position:absolute!important;
}
[data-testid="stSidebar"]{
    background:#F2F3F8!important;
    border-right:1px solid #D0D3E0!important;
    min-width:240px!important;
    max-width:260px!important;
}
[data-testid="stSidebar"] .stButton>button{
    font-size:13px!important;font-weight:600!important;
    color:#0C0C1A!important;text-align:left!important;
    border:1px solid #D0D3E0!important;
    background:#EAECF4!important;
}
[data-testid="stSidebar"] .stButton>button:hover{
    background:rgba(26,26,255,0.08)!important;
    border-color:#1A1AFF!important;color:#1A1AFF!important;
}
[data-testid="stSidebar"] label{
    font-size:13px!important;font-weight:600!important;color:#0C0C1A!important;
}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] div{
    color:#0C0C1A!important;
}
[data-testid="collapsedControl"]{display:none!important;}

/* Force Streamlit main block to allow true centering.
   NOTE: this container (stMainBlockContainer) is what actually holds
   page content — the nav clearance MUST live here, not on the outer
   wrapper, or the floating nav overlaps the first rows (chat language
   pills, New Conversation, etc.). */
[data-testid="stMainBlockContainer"] {
    max-width: 1200px !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 0 !important;
    margin: 0 auto !important;
}
section[data-testid="stMain"] > div {
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 0 !important;
    margin-top: 0 !important;
}
/* Center markdown blocks that contain hero */
[data-testid="stMarkdownContainer"] {
    width: 100%;
}

/* ── TOP NAV ─── */
.octo-nav{
    display:flex;align-items:center;gap:0;
    background:rgba(240,243,250,0.92);
    border:1px solid #D8DCE8;
    border-radius:16px;
    padding:0 2rem;
    height:60px;
    margin:14px auto 0 auto;
    max-width:1180px;
    position:sticky;top:14px;z-index:100;
    box-shadow:0 2px 10px rgba(20,20,60,0.10),0 1px 2px rgba(20,20,60,0.06);
    backdrop-filter:blur(16px) saturate(160%);
    -webkit-backdrop-filter:blur(16px) saturate(160%);
    transition:box-shadow 280ms cubic-bezier(0.4,0,0.2,1);
}
.octo-nav-logo{
    display:flex;align-items:center;gap:8px;
    font-family:var(--fd);font-size:16px;font-weight:700;color:var(--t1);
    text-decoration:none;margin-right:2rem;flex-shrink:0;
}
.octo-nav-logo img{width:26px;height:26px;border-radius:50%;}
.octo-nav-logo .orbit-wrap{
    position:relative;width:26px;height:26px;flex-shrink:0;
}
.octo-nav-logo .orbit-ring{
    position:absolute;inset:-5px;border-radius:50%;
    border:1.5px solid rgba(26,26,255,0.35);
    animation:orbit-spin 8s linear infinite;
}
.octo-nav-logo .orbit-dot{
    position:absolute;width:5px;height:5px;border-radius:50%;
    background:var(--blue);top:-2px;left:50%;transform:translateX(-50%);
}
@keyframes orbit-spin{from{transform:rotate(0deg);}to{transform:rotate(360deg);}}
.nav-links{display:flex;align-items:center;gap:2px;flex:1;}
.nav-ml{margin-left:auto;display:flex;align-items:center;gap:6px;}


/* Nav buttons */
.nav-wrap .stButton>button{
    background:#0B1020!important;
    border:none!important;
    border-radius:6px!important;
    font-family:var(--fb)!important;
    font-size:11.5px!important;
    font-weight:600!important;
    color:#FFFFFF!important;
    letter-spacing:0.01em!important;
    padding:0.42rem 0.5rem!important;
    height:auto!important;
    min-width:0!important;
    white-space:nowrap!important;
    box-shadow:none!important;
    width:100%!important;
    text-align:center!important;
    transition:
        color 180ms cubic-bezier(0.4,0,0.2,1),
        background 180ms cubic-bezier(0.4,0,0.2,1)!important;
}
.nav-wrap .stButton>button:hover{
    color:#FFFFFF!important;
    background:#1414E8!important;
    box-shadow:none!important;
    transform:none!important;
}
.nav-wrap.active .stButton>button{
    color:#FFFFFF!important;
    font-weight:700!important;
    background:#1414E8!important;
    box-shadow:inset 0 -2px 0 0 #1414E8!important;
}

/* CTA link button */
.nav-cta .stLinkButton>a,
.nav-cta .stButton>button{
    background:linear-gradient(135deg,#1414E8,#0C0CE0)!important;
    color:#fff!important;
    border-radius:30px!important;
    font-size:12px!important;
    font-weight:700!important;
    padding:0.38rem 1rem!important;
    letter-spacing:0.01em!important;
    border:1px solid rgba(255,255,255,0.25)!important;
    box-shadow:0 4px 14px rgba(26,26,255,0.30),inset 0 1px 0 rgba(255,255,255,0.25)!important;
    transition:
        transform 160ms cubic-bezier(0.34,1.5,0.64,1),
        box-shadow 160ms ease!important;
}
.nav-cta .stLinkButton>a:hover,
.nav-cta .stButton>button:hover{
    transform:translateY(-2px) scale(1.03)!important;
    box-shadow:0 8px 24px rgba(26,26,255,0.40),inset 0 1px 0 rgba(255,255,255,0.30)!important;
}


/* ── HERO ─── */
.hero{
    padding:3rem 0 2rem 0;
    text-align:center;
    position:relative;
    display:flex;
    flex-direction:column;
    align-items:center;
    justify-content:center;
    width:100%;
}
.hero-logo-wrap{
    position:relative;
    width:200px;height:200px;
    display:inline-flex;align-items:center;justify-content:center;
    margin-bottom:0.7rem;
}
.hero-logo-wrap img,.hero-logo-wrap .fi{
    width:80px;height:80px;border-radius:50%;
    position:relative;z-index:3;
    will-change:transform;
}
.hero-logo-wrap .fi{font-size:36px;line-height:80px;}
/* hero-ring and hero-orbit removed — replaced by Neural Pulse canvas */
.hero-eyebrow{
    display:inline-flex;align-items:center;gap:9px;
    font-size:14px;font-weight:700;letter-spacing:0.02em;
    color:#FFFFFF;background:#0C0C1A;border:none;
    border-radius:30px;padding:7px 16px;margin-bottom:0.1rem;margin-top:2rem;
    align-self:center;
    box-shadow:0 4px 14px rgba(12,12,26,0.18);
}
.hero-eyebrow .live-dot{
    width:5px;height:5px;border-radius:50%;background:var(--green);
    box-shadow:0 0 5px var(--green);animation:blink 2s ease-in-out infinite;
}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.hero-title{
    font-family:var(--fd);font-size:2.95rem;font-weight:600;
    color:var(--t1);letter-spacing:-0.015em;line-height:1.18;
    margin:0 auto 0.9rem auto;
    text-align:center;
    width:100%;
}
.hero-title span{background:linear-gradient(90deg,#1A1AFF,#6B6BFF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hero-sub{
    font-size:1.05rem;color:var(--t2);line-height:1.65;font-weight:400;
    max-width:560px;margin:0 auto 2.1rem auto;
    text-align:center;letter-spacing:-0.005em;
}
.hero-actions{display:flex;align-items:center;justify-content:center;gap:12px;flex-wrap:wrap;}
.hbtn{
    display:inline-flex;align-items:center;gap:7px;
    font-family:var(--fb);font-size:13.5px;font-weight:600;
    padding:0.72rem 1.5rem;border-radius:12px;
    text-decoration:none;cursor:pointer;border:none;
    transition:transform 200ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 200ms cubic-bezier(0.4,0,0.2,1),
               background 200ms ease,border-color 200ms ease,color 200ms ease;
}
.hbtn-primary{background:var(--blue);color:#fff;box-shadow:0 6px 20px rgba(26,26,255,0.28);}
.hbtn-primary:hover{background:var(--blue2);color:#fff;text-decoration:none;transform:translateY(-2px);box-shadow:0 10px 28px rgba(26,26,255,0.36);}
.hbtn-ghost{background:rgba(255,255,255,0.85);color:var(--t1);border:1px solid rgba(20,20,60,0.1);box-shadow:0 2px 10px rgba(20,20,60,0.05);}
.hbtn-ghost:hover{border-color:var(--blue);color:var(--blue);background:#fff;transform:translateY(-2px);box-shadow:0 8px 22px rgba(26,26,255,0.14);}

/* ── DOCS BADGE BANNER ── */
.docs-banner{
    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
    background:var(--t1);border-radius:14px;padding:0.8rem 1.3rem;margin-bottom:1.2rem;
    box-shadow:0 8px 24px rgba(12,12,26,0.18);
}
.docs-banner-left{display:flex;align-items:center;gap:8px;}
.docs-banner-icon{font-size:14px;color:#fff;}
.docs-banner-text{font-size:12.5px;color:rgba(255,255,255,0.7);}
.docs-banner-text strong{color:#fff;font-weight:600;}
.docs-banner-link{
    display:inline-flex;align-items:center;gap:4px;
    font-size:11.5px;font-weight:600;letter-spacing:0.05em;
    background:var(--blue);color:#fff;border-radius:20px;
    padding:5px 14px;text-decoration:none;white-space:nowrap;
    transition:transform 180ms cubic-bezier(0.34,1.4,0.64,1),background 180ms ease;
}
.docs-banner-link:hover{background:var(--blue2);color:#fff;transform:translateY(-1px);}

/* ── NAV QUICK PILLS ── */
.quick-nav{
    display:flex;gap:6px;flex-wrap:wrap;margin-bottom:1rem;
}
.qpill{
    display:inline-flex;align-items:center;gap:5px;
    font-size:12px;font-weight:500;
    background:rgba(255,255,255,0.85);border:1px solid rgba(20,20,60,0.08);
    border-radius:20px;padding:5px 13px;
    text-decoration:none;color:var(--t2);
    transition:all 180ms cubic-bezier(0.4,0,0.2,1);cursor:pointer;
}
.qpill:hover{border-color:var(--blue);color:var(--blue);background:#fff;transform:translateY(-1px);box-shadow:0 4px 12px rgba(26,26,255,0.1);}
.qpill .dot{width:5px;height:5px;border-radius:50%;background:var(--green);flex-shrink:0;}

/* ── SECTION HEADER (Campaigns / Updates) ── */
.section-dark{
    background:#1414E8;
    background-image:radial-gradient(circle, rgba(255,255,255,0.12) 1px, transparent 1px);
    background-size:14px 14px;
    border-radius:20px;padding:2.6rem 2.2rem 2.2rem 2.2rem;
    margin-bottom:1.4rem;text-align:left;position:relative;overflow:hidden;
}
.section-dark::before{
    content:'';position:absolute;inset:0;
    background:radial-gradient(ellipse 70% 60% at 20% -10%,rgba(255,255,255,0.10) 0%,transparent 60%);
    pointer-events:none;
}
.section-eyebrow{
    display:inline-flex;align-items:center;gap:6px;
    font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;
    color:rgba(255,255,255,0.65);margin-bottom:0.7rem;
}
.section-eyebrow .drop{font-size:12px;}
.section-h{
    font-family:var(--fb);font-size:2.1rem;font-weight:500;
    color:#FFFFFF;letter-spacing:-0.015em;margin:0 0 0.3rem 0;
}
.section-sub{font-size:0.92rem;color:#FFFFFF;font-weight:500;line-height:1.5;}
.section-sub a{color:#FFFFFF;text-decoration:underline;}

/* ── CAMPAIGN CARDS — top media block + bottom text, ref-3 style ── */
.camp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-bottom:1.4rem;}
.camp-card{
    background:rgba(255,255,255,0.97);border:1px solid rgba(20,20,60,0.10);
    border-radius:18px;padding:1.5rem 1.6rem;
    transition:transform 240ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 240ms cubic-bezier(0.4,0,0.2,1),
               border-color 200ms ease;
    box-shadow:0 3px 14px rgba(20,20,60,0.10);
    display:flex;flex-direction:column;gap:10px;
}
.camp-card:hover{border-color:rgba(26,26,255,0.25);box-shadow:0 16px 44px rgba(26,26,255,0.14);transform:translateY(-5px);}
.camp-tag{
    display:inline-flex;align-items:center;gap:4px;
    font-size:9.5px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
    background:rgba(26,26,255,0.07);border:1px solid rgba(26,26,255,0.18);
    color:var(--blue);border-radius:20px;padding:3px 9px;align-self:flex-start;
}
.camp-title{font-family:var(--fd);font-size:16px;font-weight:700;color:var(--t1);line-height:1.3;letter-spacing:-0.01em;}
.camp-desc{font-size:12.5px;color:var(--t2);line-height:1.62;flex:1;}
.camp-link{
    display:inline-flex;align-items:center;gap:4px;
    font-size:11.5px;font-weight:600;color:var(--blue);
    text-decoration:none;align-self:flex-start;margin-top:2px;
    transition:gap 180ms ease;
}
.camp-link:hover{text-decoration:underline;gap:7px;}

/* ── NEWS CARDS ── */
/* ═══════════════════════════════════════════
   ACTIVE UPDATES — editorial news dashboard
   3-column layout: feature / compact stack / timeline
   Uses ONLY existing Pharos palette variables —
   no new colors introduced.
═══════════════════════════════════════════ */
.news-layout{
    display:grid;
    grid-template-columns:1.5fr 1.15fr 0.85fr;
    gap:18px;
    margin-bottom:1.3rem;
    align-items:start;
}

/* ── LEFT: large hero feature card ── */
.news-feature{
    background:rgba(255,255,255,0.97);
    border:1px solid rgba(20,20,60,0.10);
    border-radius:18px;
    overflow:hidden;
    box-shadow:0 3px 14px rgba(20,20,60,0.10);
    transition:transform 220ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 220ms cubic-bezier(0.4,0,0.2,1);
    display:flex;
    flex-direction:column;
    height:100%;
}
.news-feature:hover{
    transform:translateY(-4px);
    box-shadow:0 16px 38px rgba(26,26,255,0.12);
}
.news-feature-media{
    width:100%;
    aspect-ratio:16/9;
    background:var(--bg2,#F7F8FA);
    display:flex;
    align-items:center;
    justify-content:center;
    overflow:hidden;
    flex-shrink:0;
}
.news-feature-media img{
    width:100%;
    height:100%;
    object-fit:contain;   /* never crop/stretch the source logo */
}
.news-feature-body{
    padding:1.1rem 1.3rem 1.3rem 1.3rem;
    display:flex;
    flex-direction:column;
    gap:0.5rem;
    flex:1;
}
.news-feature-eyebrow{
    font-size:9.5px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
    color:var(--blue);
}
.news-feature-title{
    font-family:var(--fd,'Syne',sans-serif);
    font-size:1.45rem;
    font-weight:800;
    line-height:1.22;
    color:var(--t1);
    letter-spacing:-0.01em;
    margin:0;
}
.news-feature-desc{
    font-size:12.5px;
    color:var(--t2);
    line-height:1.6;
    margin:0;
}
.news-feature-meta{
    font-size:10px;color:var(--t3);
    margin-top:auto;
    padding-top:0.4rem;
}

/* ── CENTER: compact horizontal cards ── */
.news-column{
    display:flex;
    flex-direction:column;
    gap:12px;
}
.news-card{
    display:grid;
    grid-template-columns:84px 1fr;
    gap:12px;
    align-items:center;
    padding:0.8rem 0.9rem;
    background:rgba(255,255,255,0.92);
    border:1px solid rgba(20,20,60,0.07);
    border-radius:14px;
    min-height:96px;
    box-shadow:0 2px 8px rgba(20,20,60,0.04);
    transition:transform 200ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 200ms cubic-bezier(0.4,0,0.2,1);
}
.news-card:hover{
    transform:translateY(-3px);
    box-shadow:0 12px 28px rgba(26,26,255,0.1);
}
.news-card-media{
    width:84px;
    height:84px;
    border-radius:10px;
    background:var(--bg2,#F7F8FA);
    display:flex;
    align-items:center;
    justify-content:center;
    overflow:hidden;
    flex-shrink:0;
}
.news-card-media img{
    width:100%;
    height:100%;
    object-fit:contain;  /* logos stay fully visible, no clipping */
}
.news-card-body{
    display:flex;
    flex-direction:column;
    gap:4px;
    min-width:0;
}
.news-card-body h4{
    font-size:12.5px;
    font-weight:700;
    color:var(--t1);
    line-height:1.35;
    margin:0;
    display:-webkit-box;
    -webkit-line-clamp:2;
    -webkit-box-orient:vertical;
    overflow:hidden;
}
.news-card-body p{
    font-size:11px;
    color:var(--t2);
    line-height:1.5;
    margin:0;
    display:-webkit-box;
    -webkit-line-clamp:2;
    -webkit-box-orient:vertical;
    overflow:hidden;
}

/* ── RIGHT: compact timeline feed ── */
.news-timeline{
    background:rgba(255,255,255,0.92);
    border:1px solid rgba(20,20,60,0.07);
    border-radius:14px;
    padding:1rem 1.1rem;
    box-shadow:0 2px 8px rgba(20,20,60,0.04);
}
.news-timeline-label{
    font-size:9.5px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
    color:var(--t3);margin-bottom:0.7rem;
}
.news-event-list{
    padding-left:14px;
    border-left:1.5px solid rgba(26,26,255,0.16);
}
.news-event{
    position:relative;
    padding-bottom:1rem;
}
.news-event:last-child{padding-bottom:0;}
.news-event::before{
    content:"";
    position:absolute;
    left:-18.5px;
    top:4px;
    width:7px;
    height:7px;
    border-radius:50%;
    background:var(--blue);
    box-shadow:0 0 0 3px rgba(26,26,255,0.12);
}
.news-event small{
    display:block;
    font-size:9.5px;
    color:var(--t3);
    margin-bottom:2px;
}
.news-event-title{
    font-size:11.5px;
    font-weight:600;
    color:var(--t1);
    line-height:1.4;
}

/* ── Fallback path (CoinGecko unavailable) — reuses .news-card with
   inline flex layout, these classes support that simpler card style ── */
.news-source{font-size:9.5px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--t3);}
.news-title{font-size:13px;font-weight:600;color:var(--t1);line-height:1.4;}
.news-title a{color:var(--t1);text-decoration:none;}
.news-title a:hover{color:var(--blue);}
.news-desc{font-size:11.5px;color:var(--t2);line-height:1.55;}
.news-date{font-size:10px;color:var(--t3);}

/* ── TRADE CEX ── */
.cex-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:14px;margin-bottom:1.1rem;}
.cex-card{
    background:rgba(255,255,255,0.92);border:1px solid rgba(20,20,60,0.07);border-radius:16px;
    padding:1.1rem 1.1rem;text-align:center;
    box-shadow:0 2px 8px rgba(20,20,60,0.04);
    transition:transform 220ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 220ms cubic-bezier(0.4,0,0.2,1),
               border-color 200ms ease;
}
.cex-card:hover{border-color:rgba(26,26,255,0.25);box-shadow:0 14px 36px rgba(26,26,255,0.13);transform:translateY(-4px);}
.cex-name{font-family:var(--fd);font-size:16px;font-weight:700;color:var(--t1);margin-bottom:3px;}
.cex-pair{font-size:10px;color:var(--t3);letter-spacing:0.05em;margin-bottom:9px;}
.cex-btn{
    display:inline-block;font-size:11px;font-weight:600;
    background:var(--blue);color:#fff;border-radius:6px;
    padding:4px 14px;text-decoration:none;
    transition:background 0.12s ease;
}
.cex-btn:hover{background:var(--blue2);color:#fff;}

/* ── CHAT SHOWCASE ── */
.chat-showcase{
    background:var(--bg1);border:1px solid var(--border);
    border-radius:14px;overflow:hidden;margin-bottom:1rem;
    box-shadow:0 1px 6px rgba(20,20,31,0.05);
}
.chat-showcase-header{
    background:var(--t1);padding:0.7rem 1rem;
    display:flex;align-items:center;gap:8px;
}
.chat-showcase-title{font-family:var(--fd);font-size:13px;font-weight:700;color:#fff;}
.chat-showcase-sub{font-size:10px;color:rgba(255,255,255,0.5);}
.chat-demo-msg{padding:0.7rem 1rem;border-bottom:1px solid var(--border);}
.chat-demo-msg:last-child{border-bottom:none;}
.chat-demo-user{font-size:12px;color:var(--t2);text-align:right;}
.chat-demo-bot{font-size:12px;color:var(--t1);}
.chat-demo-q{
    display:inline-block;background:var(--subtle);
    border:1px solid rgba(26,26,255,0.12);border-radius:8px;
    padding:5px 10px;font-size:12px;color:var(--blue);margin-top:3px;
}
.chat-demo-a{
    display:inline-block;background:var(--bg2);
    border-radius:8px;padding:5px 10px;
    font-size:12px;color:var(--t1);margin-top:3px;line-height:1.5;
}

/* ── PRICE TICKER ── */
.price-ticker{
    display:flex;background:var(--bg1);border:1px solid var(--border);
    border-radius:10px;overflow:hidden;margin-bottom:0.75rem;
    box-shadow:0 1px 3px rgba(20,20,31,0.04);
}
.ticker-cell{flex:1;padding:0.8rem 1rem;border-right:1px solid var(--border);}
.ticker-cell:last-child{border-right:none;}
.ticker-label{font-size:10px;color:var(--t3);text-transform:uppercase;letter-spacing:0.07em;margin-bottom:2px;}
.ticker-value{font-family:var(--fd);font-size:18px;font-weight:700;color:var(--t1);}
.ticker-value.green{color:var(--green);}
.ticker-value.red{color:var(--red);}
.ticker-source{font-size:10px;color:var(--t3);padding:0.25rem 1rem;background:var(--bg);border-top:1px solid var(--border);}

/* ── STATS PILLS ── */
.stats-row{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:0.7rem;}
.stat-pill{
    display:flex;align-items:center;gap:6px;
    background:var(--bg1);border:1px solid var(--border);
    border-radius:20px;padding:5px 14px;font-size:13px;font-weight:500;color:var(--t2);
    box-shadow:0 2px 6px rgba(26,26,255,0.06);
}
.stat-pill-dot{width:5px;height:5px;border-radius:50%;background:var(--green);flex-shrink:0;box-shadow:0 0 4px var(--green);animation:blink 2.5s ease-in-out infinite;}
.stat-pill strong{color:var(--t1);font-weight:600;}

/* ── CHAT UI ELEMENTS ── */
[data-testid="stChatMessage"]{
    background:transparent!important;
    padding:0.5rem 0!important;
    color:var(--t1)!important;
}
[data-testid="stChatMessage"] p{
    font-size:14px!important;
    line-height:1.7!important;
    color:var(--t1)!important;
    font-weight:450!important;
}
[data-testid="stChatMessage"] li{
    font-size:14px!important;
    line-height:1.7!important;
    color:var(--t1)!important;
}
[data-testid="stChatMessage"] span{color:var(--t1)!important;}
[data-testid="stChatMessage"] strong{
    color:var(--blue)!important;
    font-weight:700!important;
}
[data-testid="stChatMessageAvatarUser"]{
    background:linear-gradient(135deg,#1A1AFF,#4F4FFF)!important;
    border:none!important;
    box-shadow:0 2px 8px rgba(26,26,255,0.3)!important;
}
[data-testid="stChatMessageAvatarAssistant"]{
    background:linear-gradient(135deg,#0C0C1A,#1A1A3A)!important;
    border:1px solid rgba(26,26,255,0.3)!important;
    box-shadow:0 2px 8px rgba(26,26,255,0.15)!important;
}
.stChatInput,[data-testid="stChatInput"],[data-testid="stChatInput"]>div,[data-testid="stBottomBlockContainer"],[data-testid="stBottom"],[data-testid="stBottom"]>div{background:var(--bg)!important;}
[data-testid="stChatInput"]{
    background:var(--bg1)!important;
    border:1.5px solid var(--border2)!important;
    border-radius:12px!important;
    box-shadow:0 2px 8px rgba(26,26,255,0.06)!important;
}
[data-testid="stChatInput"]:focus-within{
    border-color:var(--blue)!important;
    box-shadow:0 0 0 3px var(--glow),0 2px 8px rgba(26,26,255,0.1)!important;
}
[data-testid="stChatInput"] textarea,[data-testid="stChatInputTextArea"],textarea[data-testid="stChatInputTextArea"]{
    background:var(--bg1)!important;background-color:var(--bg1)!important;
    color:var(--t1)!important;-webkit-text-fill-color:var(--t1)!important;
    font-family:var(--fb)!important;font-size:14px!important;
    caret-color:var(--blue)!important;font-weight:500!important;
}
[data-testid="stChatInput"] textarea::placeholder,[data-testid="stChatInputTextArea"]::placeholder{
    color:var(--t3)!important;-webkit-text-fill-color:var(--t3)!important;
    font-size:13px!important;opacity:1!important;
}
[data-testid="stChatInput"] button{
    background:var(--blue)!important;border:none!important;
    border-radius:8px!important;
    box-shadow:0 2px 6px rgba(26,26,255,0.3)!important;
}
[data-testid="stChatInput"] button svg{fill:#fff!important;}

/* ── EXPANDER / SOURCE ── */
[data-testid="stExpander"]{background:var(--bg1)!important;border:1.5px solid var(--border)!important;border-radius:10px!important;margin-top:0.5rem!important;box-shadow:0 2px 8px rgba(26,26,255,0.05)!important;}
[data-testid="stExpander"] summary{font-size:12px!important;font-weight:600!important;color:var(--t2)!important;padding:0.5rem 0.8rem!important;letter-spacing:0.01em!important;}
[data-testid="stExpander"] summary:hover{color:var(--light)!important;}
.source-card{background:var(--bg1);border:1px solid var(--border);border-left:3px solid var(--blue);border-radius:4px 8px 8px 4px;padding:0.5rem 0.8rem;margin:0.3rem 0;box-shadow:0 1px 4px rgba(26,26,255,0.06);}
.source-card strong{display:block;font-size:12px;font-weight:700;color:var(--t1);margin-bottom:2px;}
.source-card a{font-size:11px!important;color:var(--blue)!important;text-decoration:none!important;word-break:break-all;font-weight:500!important;}
.source-card a:hover{text-decoration:underline!important;}

/* ── GENERAL BUTTONS ── */
.stButton>button{
    background:transparent!important;color:var(--t2)!important;
    border:1px solid var(--border)!important;border-radius:6px!important;
    font-family:var(--fb)!important;font-size:12px!important;
    padding:0.35rem 0.65rem!important;height:auto!important;
    text-align:left!important;line-height:1.4!important;
    transition:background 120ms ease,border-color 120ms ease,color 120ms ease!important;
}
.stButton>button:hover{background:var(--subtle)!important;border-color:var(--blue)!important;color:var(--t1)!important;}
.reset-btn>.stButton>button{background:rgba(26,26,255,0.1)!important;border-color:var(--blue2)!important;color:var(--blue)!important;font-size:12px!important;font-weight:600!important;text-align:center!important;}
.reset-btn>.stButton>button:hover{background:var(--blue)!important;color:#fff!important;}
[data-testid="stToggle"] label{font-size:13px!important;color:var(--t2)!important;}

/* ── CHART RANGE BUTTONS inside border container ── */
[data-testid="stVerticalBlockBorderWrapper"] .stButton>button{
    background:var(--bg2)!important;border:1px solid var(--border)!important;
    border-radius:14px!important;font-size:10px!important;
    padding:2px 6px!important;text-align:center!important;color:var(--t2)!important;
    min-height:0!important;line-height:1.6!important;
}
[data-testid="stVerticalBlockBorderWrapper"] .stButton>button:hover{
    background:var(--subtle)!important;border-color:var(--blue)!important;color:var(--blue)!important;
}
[data-testid="stVerticalBlockBorderWrapper"]>div>div[data-testid="stVerticalBlock"]{
    background:var(--bg1)!important;border:1px solid var(--border)!important;
    border-radius:10px!important;padding:0.65rem 0.85rem 0.3rem 0.85rem!important;
    margin-bottom:0.7rem!important;box-shadow:0 1px 3px rgba(20,20,31,0.04)!important;
}
.chart-card-label{font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--light);margin-bottom:0.25rem;}

/* ── LOADING SCREEN ── */
.octo-loading{display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:4rem 1rem;min-height:55vh;}
.octo-loading-wrap{position:relative;width:90px;height:90px;display:flex;align-items:center;justify-content:center;margin-bottom:1.3rem;}
.octo-loading-wrap img,.octo-loading-wrap .fi{width:50px;height:50px;border-radius:50%;position:relative;z-index:3;filter:drop-shadow(0 2px 10px rgba(26,26,255,0.3));}
.octo-loading-wrap .fi{font-size:34px;line-height:50px;}
.octo-lr{position:absolute;border-radius:50%;border:1.5px solid var(--blue);opacity:0;animation:lr-pulse 2.4s ease-out infinite;}
.octo-lr.r1{width:90px;height:90px;animation-delay:0s;}
.octo-lr.r2{width:90px;height:90px;animation-delay:0.8s;}
.octo-lr.r3{width:90px;height:90px;animation-delay:1.6s;}
@keyframes lr-pulse{0%{transform:scale(0.5);opacity:0.5;}100%{transform:scale(1.6);opacity:0;}}
.octo-loading-title{font-family:var(--fd);font-size:16px;font-weight:700;color:var(--t1);margin-bottom:0.3rem;}
.octo-loading-sub{font-size:11px;color:var(--t2);margin-bottom:1rem;}
.octo-loading-dots{display:flex;gap:5px;}
.octo-loading-dots span{width:5px;height:5px;border-radius:50%;background:var(--blue);animation:ld 1.2s ease-in-out infinite;}
.octo-loading-dots span:nth-child(2){animation-delay:0.15s;}
.octo-loading-dots span:nth-child(3){animation-delay:0.3s;}
@keyframes ld{0%,80%,100%{transform:scale(0.6);opacity:0.3;}40%{transform:scale(1);opacity:1;}}

/* ── SCROLLBAR ── */
::-webkit-scrollbar{width:4px;}
::-webkit-scrollbar-track{background:var(--bg);}
::-webkit-scrollbar-thumb{background:var(--border2);border-radius:4px;}
::-webkit-scrollbar-thumb:hover{background:var(--blue);}

/* ── WELCOME CARD (chat page) ── */
.welcome-card{background:linear-gradient(135deg,#F0F1F8 0%,#EAEDF8 100%);border:1px solid var(--border);border-left:4px solid var(--blue);border-radius:14px;padding:1.1rem 1.3rem;margin-bottom:1rem;box-shadow:0 4px 16px rgba(26,26,255,0.1);}
.welcome-card h3{font-family:var(--fd)!important;font-size:17px!important;font-weight:800!important;color:var(--t1)!important;margin:0 0 0.5rem 0!important;letter-spacing:-0.01em!important;}
.welcome-card p{font-size:13px!important;color:var(--t2)!important;line-height:1.65!important;margin:0!important;}
.tag-row{display:flex;flex-wrap:wrap;gap:4px;margin-top:0.6rem;}
.tag{background:var(--subtle);border:1px solid rgba(26,26,255,0.22);border-radius:20px;padding:3px 10px;font-size:11px;font-weight:500;color:var(--blue);}

/* ── MODE TOGGLE (docs / general) ── */
.mode-bar{display:flex;gap:6px;margin-bottom:0.8rem;align-items:center;}
.mode-label{font-size:11px;color:var(--t3);flex-shrink:0;}

/* ── GLASSMORPHISM CHAT CARD ── */
.glass-card{
    background:var(--glass);
    backdrop-filter:blur(16px);
    -webkit-backdrop-filter:blur(16px);
    border:1px solid rgba(255,255,255,0.6);
    border-radius:var(--rad-lg);
    box-shadow:var(--shadow-md);
    padding:1.2rem 1.4rem;
    margin-bottom:1rem;
    transition:box-shadow 0.2s ease;
}
.glass-card:hover{box-shadow:var(--shadow-blue);}

/* ── DAPP GRID ── */
.dapp-section-hdr{
    background:#1414E8;
    background-image:radial-gradient(circle, rgba(255,255,255,0.12) 1px, transparent 1px);
    background-size:14px 14px;
    border-radius:20px;padding:2.2rem 2.2rem 1.8rem 2.2rem;
    margin-bottom:1.2rem;text-align:left;position:relative;overflow:hidden;
}
.dapp-section-hdr::before{
    content:'';position:absolute;inset:0;
    background:radial-gradient(ellipse 70% 60% at 20% -10%,rgba(255,255,255,0.10) 0%,transparent 60%);
    pointer-events:none;
}
.dapp-grid{
    display:grid;
    grid-template-columns:repeat(2,1fr);
    gap:16px;margin-bottom:1.4rem;
}
.dapp-card{
    background:#FFFFFF;
    border:1px solid #ECEEF4;
    border-radius:18px;
    padding:1.4rem 1.5rem;
    box-shadow:0 2px 10px rgba(20,20,60,0.05);
    transition:transform 240ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 240ms cubic-bezier(0.4,0,0.2,1),
               border-color 200ms ease;
    cursor:pointer;
    display:flex;flex-direction:column;gap:0;
    text-decoration:none;
}
.dapp-card:hover{
    border-color:rgba(26,26,255,0.22);
    box-shadow:0 16px 42px rgba(26,26,255,0.13);
    transform:translateY(-5px);
    text-decoration:none;
}
.dapp-logo-wrap{
    width:52px;height:52px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    margin-bottom:0.85rem;overflow:hidden;
    background:var(--dapp-bg, #F0F4FF);
}
.dapp-logo-wrap img{width:52px;height:52px;border-radius:50%;object-fit:cover;}
.dapp-name{
    font-family:var(--fd);font-size:16px;font-weight:700;
    color:#0C0C1A;margin-bottom:0.45rem;line-height:1.2;
}
.dapp-desc{
    font-size:13px;color:#5B5F6E;line-height:1.6;
    flex:1;margin-bottom:0.85rem;
}
.dapp-tags{display:flex;flex-wrap:wrap;gap:5px;margin-top:auto;}
.dapp-tag{
    display:inline-block;
    font-size:11px;font-weight:500;color:#42475A;
    background:#F2F3F8;border:1px solid #E3E5EA;
    border-radius:6px;padding:3px 9px;
}

/* ── ACTION BUTTONS — WHITE / BLACK ── */
.action-row{display:flex;align-items:center;gap:6px;flex-wrap:wrap;
    margin-top:0.55rem;padding-top:0.45rem;border-top:1px solid var(--border);}
.abtn{
    display:inline-flex;align-items:center;gap:5px;
    font-size:11px;font-weight:600;letter-spacing:0.01em;
    padding:5px 12px;border-radius:8px;cursor:pointer;
    border:1px solid #D0D3E0;
    background:#FFFFFF;color:#0C0C1A;
    font-family:'DM Sans',sans-serif;
    transition:none!important;
    text-decoration:none;white-space:nowrap;
}
.abtn svg{width:12px;height:12px;flex-shrink:0;}

/* ── FOLLOW-UP QUESTIONS ── */
.followup-row{margin-top:0.7rem;padding-top:0.5rem;border-top:1px solid var(--border);}
.followup-label{font-size:10px;font-weight:600;color:var(--t3);letter-spacing:0.08em;
    text-transform:uppercase;margin-bottom:0.4rem;}
.followup-pills{display:flex;flex-wrap:wrap;gap:6px;}
.followup-pill{
    display:inline-flex;align-items:center;gap:4px;
    font-size:12px;font-weight:500;color:var(--blue);
    background:rgba(26,26,255,0.06);border:1px solid rgba(26,26,255,0.2);
    border-radius:20px;padding:4px 12px;cursor:pointer;
    transition:all 0.12s ease;white-space:nowrap;
}
.followup-pill:hover{background:var(--blue);color:#fff;}

/* ── Follow-up buttons (real, working Streamlit buttons) ── */
.followup-btn-row{ margin-top:-0.4rem; }
.followup-btn-row .stButton>button{
    display:inline-flex!important;align-items:center!important;
    font-size:11.5px!important;font-weight:500!important;color:var(--blue)!important;
    background:rgba(26,26,255,0.06)!important;border:1px solid rgba(26,26,255,0.2)!important;
    border-radius:20px!important;padding:6px 12px!important;
    transition:background 150ms ease,color 150ms ease,border-color 150ms ease!important;
    white-space:normal!important;
    text-align:center!important;height:auto!important;
}
.followup-btn-row .stButton>button:hover{
    background:var(--blue)!important;color:#fff!important;border-color:var(--blue)!important;
}

/* ── SOURCE SIDEBAR SLIDE ── */
.source-slide{
    position:fixed;top:0;right:0;height:100vh;width:320px;
    background:var(--bg1);border-left:1px solid var(--border);
    box-shadow:-8px 0 40px rgba(20,20,60,0.15);
    z-index:9998;overflow-y:auto;
    transform:translateX(100%);
    transition:transform 0.3s cubic-bezier(0.4,0,0.2,1);
    padding:1.2rem;
}
.source-slide.open{transform:translateX(0);}
.source-slide-hdr{
    display:flex;align-items:center;justify-content:space-between;
    margin-bottom:1rem;padding-bottom:0.7rem;
    border-bottom:1px solid var(--border);
}
.source-slide-title{font-family:var(--fd);font-size:14px;font-weight:700;color:var(--t1);}
.source-slide-close{cursor:pointer;font-size:18px;color:var(--t3);line-height:1;
    width:24px;height:24px;display:flex;align-items:center;justify-content:center;
    border-radius:6px;background:var(--bg2);}
.source-slide-close:hover{background:var(--border);}
.source-item{
    background:var(--bg2);border:1px solid var(--border);border-left:3px solid var(--blue);
    border-radius:0 8px 8px 0;padding:0.6rem 0.8rem;margin-bottom:0.5rem;
}
.source-item-title{font-size:12px;font-weight:600;color:var(--t1);margin-bottom:2px;}
.source-item-url{font-size:10px;color:var(--blue);word-break:break-all;text-decoration:none;}
.source-item-url:hover{text-decoration:underline;}

/* ── SHIMMER LOADING ── */
@keyframes shimmer{
    0%{background-position:-400px 0;}
    100%{background-position:400px 0;}
}
.shimmer{
    background:linear-gradient(90deg,var(--bg2) 25%,var(--bg1) 50%,var(--bg2) 75%);
    background-size:800px 100%;animation:shimmer 1.5s ease-in-out infinite;
    border-radius:8px;
}

/* ── HERO IMPROVEMENTS ── */
.hero{
    padding:2rem 0 1.5rem 0!important;
    margin-top: -7.65rem !important;
}
.hero-logo-wrap{margin-bottom:0.7rem!important;margin-top:-2rem!important;}
.hero-title{font-size:2.95rem!important;font-weight:600!important;letter-spacing:-0.015em!important;line-height:1.18!important;}
.hero-sub{font-size:1.02rem!important;margin-bottom:1.1rem!important;}

/* ── MICRO INTERACTIONS ──
   NOTE: .camp-card already has a specific-property transition defined
   earlier (transform/box-shadow/border-color) — this rule used to say
   `transition:all`, which silently overrode that good definition later
   in the cascade and made the browser watch every property for
   changes instead of just the three that actually animate. Narrowed
   to match. */
.camp-card,.cex-card,.dapp-card,.news-card{
    transition:transform 180ms cubic-bezier(0.4,0,0.2,1),
               box-shadow 180ms cubic-bezier(0.4,0,0.2,1),
               border-color 180ms cubic-bezier(0.4,0,0.2,1)!important;
}
.camp-card:hover,.cex-card:hover{
    transform:translateY(-2px)!important;
    box-shadow:var(--shadow-blue)!important;
}

/* ── SCROLL REVEAL (3D) ──
   Below-the-fold blocks enter with a subtle 3D tilt-up as you scroll.
   Classes are applied and removed by the bootstrap script; after the
   entrance finishes ALL classes and transforms are stripped, so no
   permanent transform lingers (permanent transforms would hijack any
   position:fixed descendant). */
.sr-pre{
    opacity:0 !important;
    transform:perspective(900px) translateY(26px) rotateX(7deg) scale(0.99) !important;
    will-change:opacity,transform;
}
.sr-in{
    opacity:1 !important;
    transform:perspective(900px) translateY(0) rotateX(0deg) scale(1) !important;
    transition:opacity 460ms cubic-bezier(0.22,0.9,0.3,1),
               transform 560ms cubic-bezier(0.22,0.9,0.3,1) !important;
}

/* ── HOVER-LIFT CARDS ──
   Campaign, Updates and Ecosystem cards previously used inline
   onmouseover/onmouseout handlers, which Streamlit's markdown renderer
   ignores — so only cards accidentally matched by href-based rules got
   a hover. This class gives every card the same reliable CSS hover. */
.hover-lift{
    transition:transform 220ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 220ms cubic-bezier(0.4,0,0.2,1),
               border-color 180ms ease!important;
    transform:translateZ(0);
}
.hover-lift:hover{
    transform:translateY(-6px)!important;
    box-shadow:0 18px 44px rgba(26,26,255,0.16),
               0 0 0 1.5px rgba(26,26,255,0.20)!important;
    border-color:rgba(26,26,255,0.28)!important;
}

/* ── SMOOTH PAGE REVEAL ── */
@keyframes fadeUp{
    from{opacity:0;transform:translateY(14px);}
    to{opacity:1;transform:translateY(0);}
}
.page-reveal{animation:fadeUp 0.35s ease both;}

/* ── DOWNLOAD BTN ── */
.dl-btn{
    display:inline-flex;align-items:center;gap:5px;
    font-size:11px;font-weight:600;
    padding:5px 12px;border-radius:8px;
    border:1px solid #D0D3E0;background:#FFFFFF;color:#0C0C1A;
    cursor:pointer;font-family:'DM Sans',sans-serif;text-decoration:none;
}

/* ═══════════════════════════════════════════
   FEATURE 1: THINKING ORB
═══════════════════════════════════════════ */
.orb-wrap{
    display:flex;justify-content:center;align-items:center;
    margin:0.5rem 0;
}
.orb{
    width:40px;height:49px;border-radius:50%;position:relative;
    background:radial-gradient(circle at 35% 35%, #6B8CFF, #1A1AFF 60%, #0A0A2E);
    box-shadow:0 0 20px rgba(26,26,255,0.25),0 0 40px rgba(26,26,255,0.1);
    animation:orb-breathe 3s ease-in-out infinite;
    cursor:pointer;flex-shrink:0;
}
.orb::before{
    content:'';position:absolute;inset:3px;border-radius:50%;
    background:radial-gradient(circle at 30% 25%,rgba(255,255,255,0.35),transparent 60%);
    pointer-events:none;
}
.orb::after{
    content:'';position:absolute;inset:-6px;border-radius:50%;
    border:1.5px solid rgba(26,26,255,0.2);
    animation:orb-ring 3s ease-in-out infinite;
}
.orb.orb-thinking{
    animation:orb-think 0.8s ease-in-out infinite!important;
    box-shadow:0 0 30px rgba(26,26,255,0.5),0 0 60px rgba(26,26,255,0.2)!important;
}
.orb.orb-done{
    animation:orb-settle 0.6s ease both!important;
}
@keyframes orb-breathe{
    0%,100%{transform:scale(1);box-shadow:0 0 20px rgba(26,26,255,0.25),0 0 40px rgba(26,26,255,0.1);}
    50%{transform:scale(1.06);box-shadow:0 0 28px rgba(26,26,255,0.4),0 0 56px rgba(26,26,255,0.15);}
}
@keyframes orb-think{
    0%{transform:scale(0.96) rotate(0deg);opacity:0.9;}
    50%{transform:scale(1.08) rotate(180deg);opacity:1;}
    100%{transform:scale(0.96) rotate(360deg);opacity:0.9;}
}
@keyframes orb-ring{
    0%,100%{transform:scale(1);opacity:0.5;}
    50%{transform:scale(1.15);opacity:0.15;}
}
@keyframes orb-settle{
    0%{transform:scale(1.12);box-shadow:0 0 40px rgba(26,26,255,0.6);}
    100%{transform:scale(1);box-shadow:0 0 20px rgba(26,26,255,0.25);}
}

/* ═══════════════════════════════════════════
   FEATURE 2: BUILD PATH CARD
═══════════════════════════════════════════ */
.build-path-card{
    background:#FFFFFF;border:1.5px solid #C8D0FF;
    border-radius:16px;padding:1.3rem 1.4rem;
    box-shadow:0 4px 20px rgba(26,26,255,0.09);
    margin-top:0.8rem;
}
.build-path-title{
    font-family:Syne,sans-serif;font-size:16px;font-weight:800;
    color:#0C0C1A;margin-bottom:0.3rem;
}
.build-path-goal{
    font-size:11px;font-weight:600;letter-spacing:0.09em;text-transform:uppercase;
    color:#1A1AFF;background:rgba(26,26,255,0.07);
    border:1px solid rgba(26,26,255,0.2);border-radius:20px;
    padding:2px 10px;display:inline-block;margin-bottom:0.8rem;
}
.build-path-step{
    display:flex;align-items:flex-start;gap:10px;
    padding:0.55rem 0;border-bottom:1px solid #ECEEF4;
}
.build-path-step:last-child{border-bottom:none;}
.build-step-num{
    width:22px;height:22px;border-radius:50%;
    background:#1A1AFF;color:#fff;
    font-size:11px;font-weight:700;
    display:flex;align-items:center;justify-content:center;flex-shrink:0;
    margin-top:1px;
}
.build-step-text{font-size:13px;color:#0C0C1A;line-height:1.5;}
.build-step-sub{font-size:11px;color:#7A7F96;margin-top:2px;}
.build-path-actions{
    display:flex;gap:8px;flex-wrap:wrap;margin-top:0.9rem;
    padding-top:0.7rem;border-top:1px solid #ECEEF4;
}
.build-action-btn{
    display:inline-flex;align-items:center;gap:5px;
    font-size:11px;font-weight:600;padding:5px 12px;
    border-radius:8px;border:1px solid #1A1AFF;
    background:#1A1AFF;color:#fff;text-decoration:none;
    font-family:'DM Sans',sans-serif;
}
.build-action-ghost{
    background:#FFFFFF!important;color:#1A1AFF!important;
}

/* ═══════════════════════════════════════════
   FEATURE 3: INTERACTIVE LOGO ASSISTANT
═══════════════════════════════════════════ */
.logo-btn{
    background:none;border:none;padding:0;cursor:pointer;
    display:inline-block;position:relative;
}
.logo-bubble{
    position:absolute;
    top:calc(100% + 8px);left:50%;transform:translateX(-50%) scale(0.92);
    background:#FFFFFF;border:1.5px solid #C8D0FF;
    border-radius:14px;box-shadow:0 8px 32px rgba(26,26,255,0.14);
    padding:0.8rem 1rem;width:220px;z-index:100;
    opacity:0;pointer-events:none;
    transition:all 0.2s cubic-bezier(0.4,0,0.2,1);
}
.logo-bubble.open{
    opacity:1;pointer-events:all;
    transform:translateX(-50%) scale(1) translateY(0);
}
.logo-bubble-text{
    font-size:12px;color:#0C0C1A;font-weight:500;
    line-height:1.5;margin-bottom:0.5rem;
    font-family:'DM Sans',sans-serif;
}
.logo-bubble-cta{
    font-size:11px;font-weight:700;color:#1A1AFF;
    cursor:pointer;background:none;border:none;padding:0;
    font-family:'DM Sans',sans-serif;
}

/* ═══════════════════════════════════════════
   HOME VISUAL DECORATIVE ELEMENTS
═══════════════════════════════════════════ */

/* Animated features marquee ticker */
.marquee-wrap{
    overflow:hidden;
    background:#FFFFFF;
    border:1px solid #E3E5EA;
    border-radius:12px;
    padding:0;
    margin:1.2rem 0 1rem 0;
    box-shadow:0 1px 4px rgba(20,20,60,0.04);
    position:relative;
}
.marquee-wrap::before,.marquee-wrap::after{
    content:'';position:absolute;top:0;bottom:0;width:48px;z-index:2;
}
.marquee-wrap::before{left:0;background:linear-gradient(90deg,#FFFFFF,transparent);}
.marquee-wrap::after{right:0;background:linear-gradient(270deg,#FFFFFF,transparent);}
.marquee-track{
    display:flex;align-items:center;
    animation:marquee-scroll 28s linear infinite;
    width:max-content;
    padding:0.55rem 0;
    will-change:transform;
}
.marquee-track:hover{animation-play-state:paused;}
.marquee-item{
    display:inline-flex;align-items:center;gap:7px;
    padding:0 2rem;white-space:nowrap;
    border-right:1px solid #E3E5EA;
}
.marquee-item:last-child{border-right:none;}
.marquee-icon{font-size:16px;line-height:1;}
.marquee-label{
    font-family:Syne,sans-serif;font-size:13px;font-weight:700;
    color:#0C0C1A;
}
.marquee-sub{
    font-size:11px;color:#7A7F96;
}
@keyframes marquee-scroll{
    0%{transform:translateX(0);}
    100%{transform:translateX(-50%);}
}

.home-stat-strip{
    display:flex;gap:0;background:#0C0C1A;border-radius:12px;
    overflow:hidden;margin:0.8rem 0;
}
.home-stat-item{
    flex:1;padding:0.75rem 0.5rem;text-align:center;
    border-right:1px solid rgba(255,255,255,0.08);
}
.home-stat-item:last-child{border-right:none;}
.home-stat-num{
    font-family:Syne,sans-serif;font-size:18px;font-weight:800;
    color:#FFFFFF;line-height:1;
}
.home-stat-lbl{
    font-size:9px;font-weight:600;letter-spacing:0.08em;
    text-transform:uppercase;color:rgba(255,255,255,0.4);
    margin-top:3px;
}

/* ════════════════════════════════════════════════════════════
   MICRO ANIMATIONS — Apple / Linear quality
   Rules:
   • No layout changes • No color changes • No repositioning
   • Only transform, opacity, box-shadow, filter, transition
   • All easing: cubic-bezier(0.4, 0, 0.2, 1) — Material/Apple standard
   • Max animation duration: 600ms for interactions, 4s for ambients
════════════════════════════════════════════════════════════ */

/* ── 1. PAGE LOAD — staged fade-up reveal ── */
@keyframes page-fadein{
    from{opacity:0;transform:translateY(12px);}
    to{opacity:1;transform:translateY(0);}
}
[data-testid="stMainBlockContainer"]{
    animation:page-fadein 0.22s cubic-bezier(0.4,0,0.2,1) both;
    contain:layout style;
}



/* ── 2. HERO — handled by Neural Pulse canvas component ── */
/* Hero title smooth fade */
.hero-title{
    animation:page-fadein 0.55s cubic-bezier(0.4,0,0.2,1) 0.1s both;
}
.hero-sub{
    animation:page-fadein 0.55s cubic-bezier(0.4,0,0.2,1) 0.18s both;
}
.hero-eyebrow{
    animation:page-fadein 0.5s cubic-bezier(0.4,0,0.2,1) 0.06s both;
}
.hero-actions{
    animation:page-fadein 0.55s cubic-bezier(0.4,0,0.2,1) 0.24s both;
}


/* ── 3. BUTTONS — elevation + compression ── */
.stButton > button,
.hbtn,
.abtn,
.build-action-btn,
.nav-cta .stButton > button{
    transition:
        transform 120ms cubic-bezier(0.4,0,0.2,1),
        box-shadow 120ms cubic-bezier(0.4,0,0.2,1),
        background 130ms cubic-bezier(0.4,0,0.2,1),
        border-color 130ms cubic-bezier(0.4,0,0.2,1)
    !important;
    will-change:auto;
    transform:translateZ(0);
}
.stButton > button:hover{
    transform:translateY(-2px)!important;
    box-shadow:0 4px 14px rgba(26,26,255,0.13)!important;
}
.stButton > button:active{
    transform:scale(0.97) translateY(0)!important;
    box-shadow:0 1px 4px rgba(26,26,255,0.08)!important;
    transition-duration:80ms!important;
}
.nav-cta .stButton > button:hover{
    transform:translateY(-2px)!important;
    box-shadow:0 6px 20px rgba(26,26,255,0.3)!important;
}
.nav-cta .stButton > button:active{
    transform:scale(0.96)!important;
}
.hbtn{
    transition:transform 140ms cubic-bezier(0.4,0,0.2,1),
               box-shadow 140ms cubic-bezier(0.4,0,0.2,1)!important;
}
.hbtn:hover{
    transform:translateY(-2px)!important;
    box-shadow:0 6px 20px rgba(26,26,255,0.18)!important;
}
.hbtn:active{transform:scale(0.97)!important;}


/* ── 4. CARDS — micro lift + depth shadow ── */
.camp-card,.cex-card,.dapp-card,.news-card,
.welcome-card,.build-path-card,.glass-card,
.chat-showcase{
    transition:
        transform 180ms cubic-bezier(0.34,1.4,0.64,1),
        box-shadow 180ms cubic-bezier(0.4,0,0.2,1),
        border-color 150ms cubic-bezier(0.4,0,0.2,1),
        background 150ms cubic-bezier(0.4,0,0.2,1)
    !important;
    will-change:auto;
    transform:translateZ(0);
}
.camp-card:hover,.cex-card:hover,.news-card:hover,
.chat-showcase:hover{
    transform:translateY(-6px) scale(1.012)!important;
    box-shadow:
        0 12px 40px rgba(26,26,255,0.14),
        0 4px 12px rgba(26,26,255,0.08),
        0 0 0 1px rgba(26,26,255,0.1)
    !important;
    border-color:rgba(26,26,255,0.3)!important;
    background:linear-gradient(135deg,#FFFFFF 0%,#F6F8FF 100%)!important;
}
 /* Campaign anchor cards — inline styled so target via child selectors */
[data-testid="stMarkdownContainer"] a[href*="dorahacks"],
[data-testid="stMarkdownContainer"] a[href*="notion"],
[data-testid="stMarkdownContainer"] a[href*="silken"],
[data-testid="stMarkdownContainer"] a[href*="pharos"] {
    transition:
        transform 180ms cubic-bezier(0.34,1.4,0.64,1),
        box-shadow 180ms cubic-bezier(0.4,0,0.2,1)
    !important;
    transform:translateZ(0);
}
[data-testid="stMarkdownContainer"] a[href*="dorahacks"]:hover,
[data-testid="stMarkdownContainer"] a[href*="notion"]:hover,
[data-testid="stMarkdownContainer"] a[href*="silken"]:hover,
[data-testid="stMarkdownContainer"] a[href*="pharos"]:hover {
    transform:translateY(-5px) scale(1.012)!important;
    box-shadow:
        0 12px 36px rgba(26,26,255,0.13),
        0 4px 12px rgba(26,26,255,0.07),
        0 0 0 1.5px rgba(26,26,255,0.25)
    !important;
}           
.dapp-card:hover{
    transform:translateY(-3px)!important;
    box-shadow:0 10px 32px rgba(26,26,255,0.12)!important;
}
/* Stat pills subtle pop */
.stat-pill{
    transition:transform 140ms cubic-bezier(0.4,0,0.2,1),
               box-shadow 140ms cubic-bezier(0.4,0,0.2,1)!important;
}
.stat-pill:hover{
    transform:translateY(-1px)!important;
    box-shadow:0 3px 10px rgba(26,26,255,0.1)!important;
}
 /* DApp cards — inline-style <a> tags with border-radius:16px */
[data-testid="stMarkdownContainer"] a[style*="border-radius:16px"]{
    transition:
        transform 200ms cubic-bezier(0.34,1.4,0.64,1),
        box-shadow 200ms cubic-bezier(0.4,0,0.2,1),
        border-color 180ms ease
    !important;
    transform:translateZ(0);
}
[data-testid="stMarkdownContainer"] a[style*="border-radius:16px"]:hover{
    transform:translateY(-5px) scale(1.010)!important;
    box-shadow:
        0 14px 40px rgba(26,26,255,0.13),
        0 4px 12px rgba(26,26,255,0.07),
        0 0 0 1.5px rgba(26,26,255,0.22)
    !important;
    border-color:rgba(26,26,255,0.28)!important;
}           


/* ── 5. CHAT — message reveal + input focus ── */
/* Each new chat message slides in */
[data-testid="stChatMessage"]{
    animation:chat-msg-in 0.22s cubic-bezier(0.4,0,0.2,1) both;
    contain:layout;
}
@keyframes chat-msg-in{
    from{opacity:0;transform:translateY(8px);}
    to{opacity:1;transform:translateY(0);}
}
/* Stagger user vs assistant messages */
[data-testid="stChatMessage"]:nth-child(odd){animation-delay:0ms;}
[data-testid="stChatMessage"]:nth-child(even){animation-delay:60ms;}

/* Chat input — smooth focus ring expand */
[data-testid="stChatInput"]{
    transition:
        box-shadow 220ms cubic-bezier(0.4,0,0.2,1),
        border-color 220ms cubic-bezier(0.4,0,0.2,1),
        transform 220ms cubic-bezier(0.4,0,0.2,1)
    !important;
}
[data-testid="stChatInput"]:focus-within{
    transform:translateY(-1px)!important;
    box-shadow:0 0 0 3px rgba(26,26,255,0.12),
               0 4px 16px rgba(26,26,255,0.08)!important;
}


/* ── 6. LOADING — premium shimmer skeleton ──
   Converted from animating `background-position` (CPU repaint every
   frame) to `transform:translateX` on an oversized background — same
   sweeping visual, GPU-composited instead. This runs on every
   st.spinner() call across the app (wallet fetch, tx fetch, news
   load, chat thinking), so it's one of the most frequently-active
   animations and benefits the most from being GPU-friendly. */
@keyframes shimmer-sweep{
    0%{transform:translateX(-35%);}
    100%{transform:translateX(35%);}
}
.shimmer,.stSpinner > div{
    background:linear-gradient(
        90deg,
        var(--bg2) 0%,
        var(--bg1) 40%,
        var(--bg2) 80%
    )!important;
    background-size:1200px 100%!important;
    animation:shimmer-sweep 1.6s ease-in-out infinite!important;
    border-radius:8px!important;
    will-change:transform;
}
/* Spinner text smooth fade */
[data-testid="stSpinner"] p{
    animation:page-fadein 0.3s ease both;
    font-size:13px!important;
    color:var(--t3)!important;
}


/* ── 7. EXPANDERS ── */
[data-testid="stExpander"]{
    transition:box-shadow 200ms cubic-bezier(0.4,0,0.2,1)!important;
}
[data-testid="stExpander"]:hover{
    box-shadow:0 4px 14px rgba(26,26,255,0.07)!important;
}
[data-testid="stExpander"] summary{
    transition:color 150ms ease!important;
}


/* ── 8. HOVER INTERACTIONS — every element responsive ── */
/* Nav buttons — handled above, ensure animation transitions are smooth */
.nav-wrap .stButton > button{
    background:#0B1020!important;
    color:#FFFFFF!important;
    transition:
        background 150ms cubic-bezier(0.4,0,0.2,1),
        color 150ms cubic-bezier(0.4,0,0.2,1),
        transform 140ms cubic-bezier(0.4,0,0.2,1),
        box-shadow 150ms cubic-bezier(0.4,0,0.2,1)
    !important;
}
.nav-wrap .stButton > button:hover{
    background:#1414E8!important;
    color:#FFFFFF!important;
    transform:translateY(-1px)!important;
}
.nav-wrap .stButton > button:active{
    transform:scale(0.97)!important;
}
.nav-wrap.active .stButton > button{
    background:#1414E8!important;
    color:#FFFFFF!important;
}
/* Toggle */
[data-testid="stToggle"]{
    transition:opacity 150ms ease!important;
}
[data-testid="stToggle"]:hover{
    opacity:0.85!important;
}
/* Links */
.camp-link,.source-item-url,.dapp-arrow,a{
    transition:opacity 150ms ease,color 150ms ease!important;
}
/* Marquee pause on hover already in marquee-track */


/* ── 9. BACKGROUND — animated wave lighting ── */
/* wave-shift keyframes defined in main CSS block above */

/* NOTE: the light-sweep effect that used to live here targeted
   [data-testid="stAppViewContainer"]::before — but that selector is
   already used by the aura glow layer earlier in this file, and a
   given pseudo-element can only resolve to ONE rule per cascade.
   The aura definition (being later... actually earlier — either way,
   only one wins) made this entire block dead weight: the browser
   still parsed and tracked an 18s animation with skew/opacity that
   never visually rendered, for zero benefit and nonzero cost. Removed
   entirely rather than fixed, since the aura layer already provides
   the ambient lighting feel for this app. */


/* ── 10. NAV / STATE CHANGES — crossfade ── */
/* Page content crossfade handled by the single page-fadein animation
   already applied to [data-testid="stMainBlockContainer"] itself
   (see section 1 above). A second, near-identical animation used to
   also run on every direct child div of that same container — meaning
   every Streamlit rerun fired two overlapping fade animations across
   dozens of nested nodes instead of one clean fade on the parent.
   Removed the redundant child-level rule; the parent fade alone
   already produces the full crossfade effect with a fraction of the
   paint work. */
/* Section dark cards animate in */
.section-dark{
    animation:page-fadein 0.4s cubic-bezier(0.4,0,0.2,1) both;
}
/* Follow-up pills */
.followup-pill{
    transition:
        background 150ms cubic-bezier(0.4,0,0.2,1),
        color 150ms cubic-bezier(0.4,0,0.2,1),
        transform 150ms cubic-bezier(0.4,0,0.2,1)
    !important;
}
.followup-pill:hover{
    transform:translateY(-1px)!important;
}
/* Docs banner link */
.docs-banner-link{
    transition:background 150ms ease,transform 140ms ease!important;
}
.docs-banner-link:hover{
    transform:translateY(-1px)!important;
}
/* DApp filter buttons */
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button{
    transition:
        background 140ms cubic-bezier(0.4,0,0.2,1),
        border-color 140ms cubic-bezier(0.4,0,0.2,1),
        transform 140ms cubic-bezier(0.4,0,0.2,1)
    !important;
}
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button:hover{
    transform:translateY(-1px)!important;
}
/* Link buttons */
.stLinkButton a{
    transition:transform 140ms cubic-bezier(0.4,0,0.2,1),
               box-shadow 140ms cubic-bezier(0.4,0,0.2,1)!important;
}
.stLinkButton a:hover{
    transform:translateY(-2px)!important;
    box-shadow:0 4px 14px rgba(26,26,255,0.14)!important;
}
/* Source sidebar slide */
.source-item{
    transition:transform 160ms cubic-bezier(0.4,0,0.2,1),
               box-shadow 160ms cubic-bezier(0.4,0,0.2,1)!important;
}
.source-item:hover{
    transform:translateX(2px)!important;
    box-shadow:0 2px 8px rgba(26,26,255,0.08)!important;
}
/* Sidebar example question buttons */
[data-testid="stSidebar"] .stButton > button{
    transition:
        background 130ms cubic-bezier(0.4,0,0.2,1),
        border-color 130ms cubic-bezier(0.4,0,0.2,1),
        transform 130ms cubic-bezier(0.4,0,0.2,1)
    !important;
}
[data-testid="stSidebar"] .stButton > button:hover{
    transform:translateX(2px)!important;
}
/* Smooth scrollbar */
html{scroll-behavior:smooth!important;}
*{-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
*,*::before,*::after{box-sizing:border-box;}
/* Reset will-change everywhere by default... */
*,*::before,*::after{will-change:auto;}
/* ...then re-promote ONLY the aura/dots background layers to their own
   GPU compositor layer. This rule must stay BELOW the catch-all above
   so it wins on source order — without it, the catch-all silently
   strips GPU promotion from these full-viewport animated layers,
   forcing the browser to repaint them constantly and causing the
   visible stutter across the whole app. */
[data-testid="stAppViewContainer"]::before{ will-change:transform; }
[data-testid="stAppViewContainer"]::after{ will-change:transform; }
.stApp::before{ will-change:transform; }

/* Respect the OS-level "reduce motion" accessibility setting — pauses
   only the continuous ambient background animations (wave/aura/dots)
   for users who've opted out of motion, without touching interaction
   feedback (hover/click still feel responsive either way). */
@media (prefers-reduced-motion: reduce) {
    .stApp::before,
    [data-testid="stAppViewContainer"]::before,
    [data-testid="stAppViewContainer"]::after{
        animation: none !important;
    }
}

/* ═══════════════════════════════════════════
   SMOOTHNESS & INPUT-LATENCY LAYER
   Internal performance polish only — no visual, layout, colour, or
   behaviour change. Purely improves scroll feel, tap responsiveness
   and paint stability.
═══════════════════════════════════════════ */

/* Prevent scroll-chaining jitter (rubber-band bleed into the parent /
   browser chrome) and stop iOS from silently re-scaling text on
   orientation change — both cause perceptible layout jumps. */
html{
    overscroll-behavior-y:contain;
    -webkit-text-size-adjust:100%;
    text-size-adjust:100%;
}

/* Remove the ~300ms mobile tap delay so clicks register instantly,
   while still allowing normal pinch-zoom. Applied only to genuinely
   interactive controls so text selection is unaffected. */
button,a,[role="button"],
.stButton>button,
.pnav-logo,.pnav-item,.pnav-dd-item,
[data-testid="stTextInput"] input{
    touch-action:manipulation;
}

/* Note: the floating nav is already GPU-promoted (translateZ + will-change
   on .pnav) so it composites independently during scroll. We deliberately
   do NOT add CSS `contain` to .pnav-fixed / .pnav here — the hover
   dropdowns (.pnav-dd) are absolutely positioned BELOW the bar and would
   be clipped by paint containment. */

/* Reduced-motion: also collapse one-shot entrance + interaction
   transitions to a snap, so users who opt out get an instant,
   jank-free UI rather than half-running animations. */
@media (prefers-reduced-motion: reduce){
    .reveal-up,.section-dark,.dapp-section-hdr,
    .sr-pre,.sr-in{
        animation:none !important;
        transition:none !important;
        opacity:1 !important;
        transform:none !important;
    }
}

/* ═══════════════════════════════════════════
   PREMIUM MOTION SYSTEM — scroll reveal + stagger
   Apple × Linear × Arc quality, GPU accelerated
═══════════════════════════════════════════ */

/* Momentum-feel smooth scrolling on the main scroll container */
section[data-testid="stMain"]{
    scroll-behavior:smooth!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-y:contain!important;
    /* Single source of truth for nav clearance. Lives on the OUTER
       section, which no inner container rule touches — so page banners
       can never tuck under the floating nav regardless of the cascade
       inside stMainBlockContainer. */
    padding-top:80px !important;
}
@media (max-width:600px){
    section[data-testid="stMain"]{ padding-top:74px !important; }
}
/* Pages with a sidebar (Chat) render main content higher — add extra
   clearance so the first row (language pills) never hides under the
   floating nav. Combined with the in-page .chat-top-spacer, the first
   row is guaranteed to sit clear on the chat page. */
.stApp:has(section[data-testid="stSidebar"]) section[data-testid="stMain"]{
    padding-top:38px !important;
}
/* Belt & braces: the first content block also carries scroll/anchor margin. */
section[data-testid="stMain"] [data-testid="stMainBlockContainer"] > div:first-child{
    scroll-margin-top:110px;
}
section[data-testid="stMain"] > div{
    scroll-behavior:smooth!important;
}
/* Snappy global transition baseline — every interactive element responds fast */
button,a,.stButton>button,[data-testid="stTextInput"] input{
    transition-timing-function:cubic-bezier(0.4,0,0.2,1)!important;
}
/* Reduce all default Streamlit transition lag */
[data-testid="stVerticalBlock"],[data-testid="stHorizontalBlock"]{
    transition:opacity 160ms cubic-bezier(0.4,0,0.2,1)!important;
}

/* Scroll-reveal base state — elements fade+rise into view */
.reveal-up{
    opacity:0;
    transform:translateY(22px);
    animation:reveal-in 0.6s cubic-bezier(0.16,1,0.3,1) forwards;
}
@keyframes reveal-in{
    to{opacity:1;transform:translateY(0);}
}

/* Stagger helper classes — apply progressive delay to siblings */
.reveal-up.d1{animation-delay:0.04s;}
.reveal-up.d2{animation-delay:0.08s;}
.reveal-up.d3{animation-delay:0.12s;}
.reveal-up.d4{animation-delay:0.16s;}
.reveal-up.d5{animation-delay:0.20s;}
.reveal-up.d6{animation-delay:0.24s;}

/* Section entrance — applied to dark headers and major blocks */
.section-dark,.dapp-section-hdr{
    animation:section-rise 0.55s cubic-bezier(0.16,1,0.3,1) both;
}
@keyframes section-rise{
    from{opacity:0;transform:translateY(16px) scale(0.992);}
    to{opacity:1;transform:translateY(0) scale(1);}
}

/* Soft floating idle motion for hero logo — gentle, non-distracting */
@keyframes gentle-float{
    0%,100%{transform:translateY(0px);}
    50%{transform:translateY(-4px);}
}

/* Loading shimmer — premium skeleton states */
@keyframes premium-shimmer{
    0%{background-position:-450px 0;}
    100%{background-position:450px 0;}
}
.skeleton-shimmer{
    background:linear-gradient(90deg,
        rgba(20,20,60,0.04) 0%,
        rgba(20,20,60,0.09) 50%,
        rgba(20,20,60,0.04) 100%);
    background-size:450px 100%;
    animation:premium-shimmer 1.4s ease-in-out infinite;
    border-radius:10px;
}

/* Stat pill micro icon movement on hover */
.stat-pill-dot{transition:transform 220ms cubic-bezier(0.34,1.4,0.64,1)!important;}
.stat-pill:hover .stat-pill-dot{transform:scale(1.4)!important;}

/* "Connect Wallet & View Profile" button — bold black, white text,
   easily visible against the dark gradient banner above it on Home.
   Wrapped in .connect-wallet-btn-wrap below (CSS :contains()/:has()
   with text matching is not valid CSS — using a wrapper div instead,
   the same reliable pattern used elsewhere in this file). */
.connect-wallet-btn-wrap .stButton>button{
    background:#0C0C1A!important;
    color:#FFFFFF!important;
    font-weight:800!important;
    font-size:13.5px!important;
    border:1.5px solid #0C0C1A!important;
    border-radius:10px!important;
    padding:0.65rem 1rem!important;
    text-align:center!important;
    box-shadow:0 6px 18px rgba(12,12,26,0.3)!important;
    letter-spacing:0.01em!important;
}
.connect-wallet-btn-wrap .stButton>button:hover{
    background:#1414E8!important;
    border-color:#1414E8!important;
    box-shadow:0 10px 26px rgba(20,20,232,0.4)!important;
    transform:translateY(-2px)!important;
}

/* Elegant opacity transitions handled by existing page-fadein animation above */

/* ═══════════════════════════════════════════
   TABLET RESPONSIVE — 1024px and below
═══════════════════════════════════════════ */
@media (max-width:1024px) {
    [data-testid="stMainBlockContainer"] {
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
    }
    .hero-title { font-size: 2.1rem !important; }

    /* ── Active Updates — drop to 2 columns on tablet (feature + stack,
       timeline moves below full-width) ── */
    .news-layout{
        grid-template-columns:1.4fr 1fr!important;
    }
    .news-timeline{
        grid-column:1 / -1;
    }
}

 /* ═══════════════════════════════════════════
   MOBILE RESPONSIVE — Phone optimised
   Breakpoint: 768px and below
═══════════════════════════════════════════ */
@media (max-width: 768px) {

    /* ── Layout ── */
    [data-testid="stMainBlockContainer"]{
        padding-left:0.8rem!important;
        padding-right:0.8rem!important;
        padding-top:0!important;
    }
    section[data-testid="stMain"] > div{
        padding-left:0.5rem!important;
        padding-right:0.5rem!important;
    }

    /* ── Hide sidebar on mobile ── */
    [data-testid="stSidebar"]{display:none!important;}
    [data-testid="collapsedControl"]{display:none!important;}

    /* ── Nav bar — stack vertically, scrollable ── */
    [data-testid="stHorizontalBlock"]{
        flex-wrap:wrap!important;
        gap:4px!important;
    }
    .nav-wrap .stButton>button{
        font-size:11px!important;
        padding:0.25rem 0.5rem!important;
    }
    .nav-cta .stButton>button{
        font-size:11px!important;
        padding:0.25rem 0.7rem!important;
    }

    /* ── Hero ── */
    .hero{padding:0.3rem 0 1rem 0!important;}
    .hero-title{font-size:1.55rem!important;letter-spacing:-0.02em!important;}
    .hero-sub{font-size:0.85rem!important;margin-bottom:1rem!important;}
    .hero-actions{gap:6px!important;}
    .hbtn{font-size:12px!important;padding:0.5rem 1rem!important;}

    /* ── Stat strip — 2 columns on mobile ── */
    .home-stat-strip{
        display:grid!important;
        grid-template-columns:1fr 1fr!important;
    }
    .home-stat-item{border-right:none!important;border-bottom:1px solid rgba(255,255,255,0.08)!important;}
    .home-stat-num{font-size:15px!important;}

    /* ── Marquee — slower on mobile for readability ── */
    .marquee-track{animation-duration:40s!important;}

    /* ── Campaign cards — full width single column ── */
    div[style*="grid-template-columns:1fr 1fr"]{
        grid-template-columns:1fr!important;
    }
    .camp-grid{grid-template-columns:1fr!important;}

    /* ── DApp grid — 1 column on phone, 2 on tablet ── */
    div[style*="minmax(260px,1fr)"]{
        grid-template-columns:1fr!important;
    }

    /* ── Active Updates — stack the 3-column editorial layout ── */
    .news-layout{
        grid-template-columns:1fr!important;
        gap:14px!important;
    }
    .news-feature-media{aspect-ratio:16/10!important;}
    .news-feature-title{font-size:1.2rem!important;}
    .news-card{grid-template-columns:64px 1fr!important;}
    .news-card-media{width:64px!important;height:64px!important;}

    /* ── CEX grid — 2 columns ── */
    .cex-grid{grid-template-columns:1fr 1fr!important;}
    .cex-card{padding:0.7rem!important;}
    .cex-name{font-size:13px!important;}

    /* ── Section dark header — smaller text ── */
    .section-h{font-size:1.5rem!important;}
    .section-dark{padding:1.5rem 1rem 1.2rem!important;}

    /* ── Price ticker — 2x2 grid instead of row ── */
    .price-ticker{
        display:grid!important;
        grid-template-columns:1fr 1fr!important;
    }
    .ticker-cell{border-right:none!important;border-bottom:1px solid var(--border)!important;}
    .ticker-value{font-size:14px!important;}

    /* ── Chat input ── */
    [data-testid="stChatInput"] textarea{font-size:14px!important;}

    /* ── Docs banner — stack vertically ── */
    .docs-banner{flex-direction:column!important;gap:6px!important;align-items:flex-start!important;}

    /* ── Build path buttons — 2 columns ── */
    div[style*="grid-template-columns:repeat(4"]{
        grid-template-columns:1fr 1fr!important;
    }

    /* ── General text sizing ── */
    .camp-title{font-size:13px!important;}
    .camp-desc{font-size:11px!important;}
    .dapp-name{font-size:13px!important;}
    .dapp-desc{font-size:11px!important;}
    .news-title{font-size:12px!important;}

    /* ── Buttons full width on mobile ── */
    .stButton>button{font-size:12px!important;}

    /* ── Mode bar ── */
    div[style*="mode_docs"]{flex-wrap:wrap!important;}
}

/* ── Extra small phones (iPhone SE etc) ── */
@media (max-width: 390px) {
    .hero-title{font-size:1.3rem!important;}
    .section-h{font-size:1.2rem!important;}
    .home-stat-num{font-size:13px!important;}
    .nav-wrap .stButton>button{font-size:10px!important;padding:0.2rem 0.4rem!important;}
}
/* ── Force nav buttons black — target by Streamlit's per-element key class ── */
.st-key-nav_home    button,
.st-key-nav_chat    button,
.st-key-nav_campaigns button,
.st-key-nav_updates button,
.st-key-nav_trade   button,
.st-key-nav_ecosystem button,
.st-key-nav_pay     button,
.st-key-nav_request button,
.st-key-nav_network button,
.st-key-nav_spns    button{
    background:#EAEEFF !important;
    background-color:#EAEEFF !important;
    color:#000000 !important;
    border:1px solid #C7D0FF !important;
}
.st-key-nav_home    button *,
.st-key-nav_chat    button *,
.st-key-nav_campaigns button *,
.st-key-nav_updates button *,
.st-key-nav_trade   button *,
.st-key-nav_ecosystem button *,
.st-key-nav_pay     button *,
.st-key-nav_request button *,
.st-key-nav_network button *,
.st-key-nav_spns    button *{
    color:#000000 !important;
}
.st-key-nav_home    button:hover,
.st-key-nav_chat    button:hover,
.st-key-nav_campaigns button:hover,
.st-key-nav_updates button:hover,
.st-key-nav_trade   button:hover,
.st-key-nav_ecosystem button:hover,
.st-key-nav_pay     button:hover,
.st-key-nav_request button:hover,
.st-key-nav_network button:hover,
.st-key-nav_spns    button:hover{
    background:#D8DFFF !important;
    background-color:#D8DFFF !important;
    color:#000000 !important;
    border-color:#1A1AFF !important;
}
                       
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# LAYOUT REDESIGN — Pay / Request / SPN / Network
# Structural-only: 8px spacing system, unified content
# max-width, compact heroes, Inter for UI text, equal
# card sizing. Scoped via :has() so other pages are
# untouched. No functionality / logic / component change.
# ─────────────────────────────────────────────
def inject_redesign_css(page_marker: str) -> None:
    st.markdown(
        f'<div class="rd-marker rd-{page_marker}" style="height:0;margin:0;padding:0;overflow:hidden;"></div>',
        unsafe_allow_html=True,
    )
    st.markdown("""
<style>
/* ===== Layout redesign — applies only to pages carrying a .rd-marker =====
   IMPORTANT: do NOT change the main block container max-width here. The
   sticky top nav lives in this same container, and changing its width makes
   the fixed-weight nav columns reflow / wrap. Keep the container at the app
   default so the nav is pixel-identical on every page; redesigned pages
   compose their own width with inner columns instead. */
[data-testid="stMainBlockContainer"]:has(.rd-marker){
    margin:0 auto !important;
    padding-top:0 !important;
}
/* Consistent vertical rhythm on an 8px grid between top-level blocks */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    section[data-testid="stMain"] *,
[data-testid="stMainBlockContainer"]:has(.rd-marker){}

/* Typography: keep Syne for major titles (h1/h2), Inter for all UI text */
[data-testid="stMainBlockContainer"]:has(.rd-marker) p,
[data-testid="stMainBlockContainer"]:has(.rd-marker) span,
[data-testid="stMainBlockContainer"]:has(.rd-marker) label,
[data-testid="stMainBlockContainer"]:has(.rd-marker) li,
[data-testid="stMainBlockContainer"]:has(.rd-marker) div,
[data-testid="stMainBlockContainer"]:has(.rd-marker) input,
[data-testid="stMainBlockContainer"]:has(.rd-marker) textarea,
[data-testid="stMainBlockContainer"]:has(.rd-marker) button{
    font-family:'Inter','DM Sans',sans-serif;
}
/* Major titles keep the display font */
[data-testid="stMainBlockContainer"]:has(.rd-marker) h1,
[data-testid="stMainBlockContainer"]:has(.rd-marker) h2{
    font-family:'Syne',sans-serif !important;
}
/* Guard: keep the top nav untouched by the redesign cascade so its buttons
   never change size/font/wrap across pages. */
[data-testid="stMainBlockContainer"]:has(.rd-marker) [class*="st-key-nav_"] button,
[data-testid="stMainBlockContainer"]:has(.rd-marker) [class*="st-key-nav_"] button *{
    font-family:'DM Sans',sans-serif !important;
    min-height:0 !important;
    white-space:nowrap !important;
}

/* Tighten the gap Streamlit puts between stacked blocks (8px grid) */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stVerticalBlock"]{
    gap:0.5rem !important;
}

/* Inputs: consistent height + readable LIGHT text on the dark input fill.
   (The app's input background is dark, so text must be near-white.) */
[data-testid="stMainBlockContainer"]:has(.rd-marker) input,
[data-testid="stMainBlockContainer"]:has(.rd-marker) textarea{
    min-height:44px;
    font-size:14px !important;
    color:#F4F7FF !important;
    -webkit-text-fill-color:#F4F7FF !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker) textarea{
    min-height:120px;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker) input::placeholder,
[data-testid="stMainBlockContainer"]:has(.rd-marker) textarea::placeholder{
    color:rgba(244,247,255,0.45) !important;
    -webkit-text-fill-color:rgba(244,247,255,0.45) !important;
}
/* Disabled Token field stays readable but clearly inert */
[data-testid="stMainBlockContainer"]:has(.rd-marker) input:disabled{
    color:#C7D2FE !important;
    -webkit-text-fill-color:#C7D2FE !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stTextInput"] label p,
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stTextArea"] label p{
    font-size:12.5px !important;
    font-weight:600 !important;
    color:#39445D !important;
}
/* Buttons: consistent height + weight.
   Exclude the top-nav buttons (st-key-nav_*) and the CTA so the nav row is
   pixel-identical to every other page. */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    .stButton:not([class*="st-key-nav_"]) button{
    min-height:44px;
    font-weight:600;
}

/* ---- Compact hero: trim the dark gradient banner padding ----
   Original heroes use padding 2rem–2.2rem; cut ~25% to reduce
   vertical whitespace while keeping the gradient/branding. */
[data-testid="stMainBlockContainer"]:has(.rd-hero-compact)
    [data-testid="stMarkdownContainer"]
    > div[style*="linear-gradient(135deg,#0C0C1A"],
[data-testid="stMainBlockContainer"]:has(.rd-hero-compact)
    [data-testid="stMarkdownContainer"]
    > div[style*="linear-gradient(135deg,#0A0A28"]{
    padding-top:1.5rem !important;
    padding-bottom:1.2rem !important;
    margin-bottom:1rem !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-hero-compact) h2{
    font-size:1.7rem !important;
    margin-bottom:0.4rem !important;
}

/* Equal-height, lighter-padding metric / info cards on dashboard */
[data-testid="stMainBlockContainer"]:has(.rd-network)
    [data-testid="stMarkdownContainer"] div[style*="grid-template-columns:repeat(3,1fr)"]{
    align-items:stretch !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-network)
    [data-testid="stMarkdownContainer"] div[style*="grid-template-columns:repeat(3,1fr)"] > div{
    display:flex !important;
    flex-direction:column !important;
    justify-content:flex-start !important;
}

@media (max-width:760px){
  [data-testid="stMainBlockContainer"]:has(.rd-marker)
      [data-testid="stMarkdownContainer"] div[style*="grid-template-columns:repeat(3,1fr)"],
  [data-testid="stMainBlockContainer"]:has(.rd-marker)
      [data-testid="stMarkdownContainer"] div[style*="grid-template-columns:repeat(4,1fr)"]{
    grid-template-columns:1fr 1fr !important;
  }
}

/* ======================================================================
   DESIGN SYSTEM — shared component classes for the recomposed pages.
   Real Streamlit widgets (st.columns / st.container) provide structure;
   these classes provide the surface treatment so columns read as
   designed panels, side rails, toolbars and consoles. Colours/tokens
   are the existing palette — no new brand colours introduced.
   ====================================================================== */

/* Redesigned pages compose their own width via inner columns; the shared
   container width is left at the app default so the nav never reflows. */
[data-testid="stMainBlockContainer"]:has(.rd-wide){
    /* intentionally no max-width override */
}

/* Bordered st.container → designed surface card.
   Streamlit marks bordered containers with stVerticalBlockBorderWrapper.
   Make them solid (not see-through), equal-height within a row, and padded. */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stVerticalBlockBorderWrapper"]{
    background:#FFFFFF !important;
    border:1px solid #E4E8F2 !important;
    border-radius:18px !important;
    box-shadow:0 4px 22px rgba(14,22,52,0.08) !important;
    height:100% !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stVerticalBlockBorderWrapper"] > div{
    padding:0.9rem 1.05rem !important;
    height:100%;
}

/* Kill the app's translucent inner-block fill that makes cards see-through */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stVerticalBlockBorderWrapper"] > div
    > div[data-testid="stVerticalBlock"]{
    background:transparent !important;
    border:none !important;
    box-shadow:none !important;
    padding:0 !important;
    margin-bottom:0 !important;
}

/* Real gutter between side-by-side cards */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"])
    > [data-testid="stColumn"]{
    padding-left:8px !important;
    padding-right:8px !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"])
    > [data-testid="stColumn"]:first-child{ padding-left:0 !important; }
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"])
    > [data-testid="stColumn"]:last-child{ padding-right:0 !important; }
                
/* Force the columns in a horizontal row to stretch to equal height so two
   side-by-side cards always match, regardless of content length.
   Excludes the nav row (it has no bordered cards, and must not be altered). */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"]),
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has(.rd-fillcard),
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has(.rd-stat){
    align-items:stretch !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has([data-testid="stVerticalBlockBorderWrapper"])
    > [data-testid="stColumn"],
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has(.rd-fillcard) > [data-testid="stColumn"],
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"]:has(.rd-stat) > [data-testid="stColumn"]{
    display:flex !important;
    flex-direction:column !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]
    > [data-testid="stVerticalBlockBorderWrapper"]{
    flex:1 1 auto !important;
}
/* Plain markdown cards (SPN use-case tiles, stat tiles) also fill the column
   height so two cards in a row are always equal and never collide.
   Constrained with :has() so only card columns are affected (not the nav). */
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(.rd-fillcard)
    > [data-testid="stVerticalBlock"],
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:has(.rd-stat)
    > [data-testid="stVerticalBlock"]{
    height:90% !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]
    [data-testid="stMarkdownContainer"]:has(> .rd-fillcard),
[data-testid="stMainBlockContainer"]:has(.rd-marker)
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]
    [data-testid="stMarkdownContainer"]:has(> .rd-stat){
    height:90% !important;
}
[data-testid="stMainBlockContainer"]:has(.rd-marker) .rd-fillcard,
[data-testid="stMainBlockContainer"]:has(.rd-marker) .rd-stat{
    height:90% !important;
}

/* The hero "eyebrow" section label used at the top of recomposed columns */
.rd-eyebrow{
    display:inline-flex;align-items:center;gap:6px;
    font-family:'Inter',sans-serif;font-size:10px;font-weight:700;
    letter-spacing:0.14em;text-transform:uppercase;color:#5B6B8C;
    background:rgba(26,26,255,0.06);border:1px solid rgba(26,26,255,0.12);
    border-radius:999px;padding:4px 11px;margin-bottom:0.55rem;
}
.rd-panel-title{
    font-family:'Syne',sans-serif;font-size:15px;font-weight:800;
    color:#0B1020;letter-spacing:-0.01em;margin:0 0 2px 0;display:flex;
    align-items:center;gap:8px;
}
.rd-panel-sub{
    font-family:'Inter',sans-serif;font-size:12px;color:#68738C;
    line-height:1.55;margin:0 0 0.4rem 0;
}
.rd-divider{height:1px;background:#ECEEF6;margin:0.6rem 0;border:0;}

/* Suggestion chips (Pay command examples) rendered as real buttons:
   target the chip column group via a wrapper marker. */
[data-testid="stMainBlockContainer"]:has(.rd-chiprow) .stButton button{
    border-radius:999px !important;
    background:rgba(26,26,255,0.04) !important;
    border:1px solid rgba(26,26,255,0.14) !important;
    color:#2B3656 !important;
    font-size:12.5px !important;font-weight:500 !important;
    min-height:38px !important;padding:0 14px !important;
    text-align:left !important;justify-content:flex-start !important;
    transition:all 160ms ease;
}
[data-testid="stMainBlockContainer"]:has(.rd-chiprow) .stButton button:hover{
    background:rgba(26,26,255,0.10) !important;
    border-color:rgba(26,26,255,0.30) !important;
    transform:translateY(-1px);
}

/* Command surface: make the big Pay prompt textarea feel like the hero */
[data-testid="stMainBlockContainer"]:has(.rd-command) textarea{
    min-height:120px !important;font-size:16px !important;
    line-height:1.5 !important;border-radius:14px !important;
    padding:14px 16px !important;
}

/* Console panel (SPN results) — dark, monospaced artifact surface */
.rd-console{
    background:#0B1020;border:1px solid #1B2440;border-radius:16px;
    padding:1rem 1.15rem;font-family:'DM Mono',ui-monospace,monospace;
    color:#C7D2FE;font-size:12.5px;line-height:1.7;overflow-x:auto;
    box-shadow:inset 0 1px 0 rgba(255,255,255,0.04);
}
.rd-console .rd-con-bar{
    display:flex;align-items:center;gap:6px;margin:-0.2rem 0 0.7rem 0;
    padding-bottom:0.6rem;border-bottom:1px solid #1B2440;
}
.rd-console .rd-dot{width:10px;height:10px;border-radius:50%;}
.rd-k{color:#7C8BB8;}.rd-v{color:#E6EBFF;font-weight:600;}

/* Featured status card accent rail */
.rd-featured{position:relative;overflow:hidden;}
.rd-featured::before{
    content:"";position:absolute;left:0;top:0;bottom:0;width:4px;
    background:linear-gradient(180deg,#1A1AFF,#6B8CFF);
}

/* Stat tile (dashboard) — used inside st.columns for equal sizing */
.rd-stat{
    background:#FFFFFF;border:1px solid #E4E8F2;border-radius:16px;
    padding:1rem 1.15rem;box-shadow:0 2px 12px rgba(20,20,60,0.05);
    height:100%;display:flex;flex-direction:column;
}
.rd-stat .rd-stat-top{display:flex;align-items:center;gap:8px;margin-bottom:0.5rem;}
.rd-stat .rd-stat-ic{width:30px;height:30px;border-radius:9px;display:flex;
    align-items:center;justify-content:center;font-size:15px;}
.rd-stat .rd-stat-lbl{font-family:'Inter',sans-serif;font-size:9.5px;font-weight:600;
    letter-spacing:0.07em;text-transform:uppercase;color:#9499A8;}
.rd-stat .rd-stat-val{font-family:'Syne',sans-serif;font-size:1.9rem;font-weight:800;
    letter-spacing:-0.02em;line-height:1.05;}
.rd-stat .rd-stat-sub{font-family:'Inter',sans-serif;font-size:10.5px;color:#9499A8;margin-top:3px;}

/* Toolbar row (network selector / config bar) sits in a slim bar */
.rd-toolbar{
    display:flex;align-items:center;gap:10px;flex-wrap:wrap;
    background:rgba(255,255,255,0.7);border:1px solid #E4E8F2;
    border-radius:12px;padding:7px 12px;margin-bottom:0.5rem;
}
.rd-toolbar .rd-tb-lbl{font-family:'Inter',sans-serif;font-size:10px;font-weight:700;
    letter-spacing:0.08em;text-transform:uppercase;color:#7A7F96;}

/* Make buttons inside a slim toolbar marker compact */
[data-testid="stMainBlockContainer"]:has(.rd-toolbarrow) .stButton button{
    min-height:38px !important;font-size:12.5px !important;padding:0 14px !important;
}

/* Side rail (Pay wallet / utilities) — subtle inset look */
.rd-rail{
    background:rgba(247,249,253,0.85);border:1px solid #E4E8F2;
    border-radius:16px;padding:1rem 1.1rem;
}
.rd-util{
    font-family:'Inter',sans-serif;font-size:11.5px;color:#68738C;
    display:flex;align-items:center;gap:7px;
}

/* QR frame on the Request result */
.rd-qr{
    background:#FFFFFF;border:1px solid #E4E8F2;border-radius:14px;
    padding:12px;display:inline-flex;box-shadow:0 2px 12px rgba(20,20,60,0.06);
}

/* ═══════════════════════════════════════════════════════════
   DARK MODE for redesigned (.rd-marker) pages — Pay, Request,
   Network, Trade, SPNs, Ecosystem, Memory Ledger. These pages use
   hard-coded light rd-* surfaces + dark text with high specificity,
   so they need matching-specificity dark overrides here.
   ═══════════════════════════════════════════════════════════ */
html[data-theme="dark"] .rd-panel,
html[data-theme="dark"] .rd-stat,
html[data-theme="dark"] .rd-toolbar,
html[data-theme="dark"] .rd-qr,
html[data-theme="dark"] .rd-card,
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [data-testid="stVerticalBlockBorderWrapper"]{
    background:#141826 !important;border-color:#262B3E !important;
}
/* Titles / values → light */
html[data-theme="dark"] .rd-panel-title,
html[data-theme="dark"] .rd-stat-val,
html[data-theme="dark"] .rd-h,
html[data-theme="dark"] .rd-title,
html[data-theme="dark"] .rd-v{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
/* Sub / label / muted → readable grey */
html[data-theme="dark"] .rd-panel-sub,
html[data-theme="dark"] .rd-stat-lbl,
html[data-theme="dark"] .rd-stat-sub,
html[data-theme="dark"] .rd-k,
html[data-theme="dark"] .rd-label,
html[data-theme="dark"] .rd-sub{
    color:#AEB4C8 !important;-webkit-text-fill-color:#AEB4C8 !important;
}
html[data-theme="dark"] .rd-divider{background:#262B3E !important;}
/* Chip buttons */
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-chiprow) .stButton button{
    background:rgba(90,110,255,0.10) !important;border-color:rgba(90,110,255,0.28) !important;
    color:#C4C9DC !important;
}
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-chiprow) .stButton button:hover{
    background:rgba(90,110,255,0.18) !important;border-color:rgba(90,110,255,0.45) !important;
}
/* Broad safety net: on rd-marker pages, force near-black inline text light
   and lift muted greys — highest-specificity so nothing stays stranded. */
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#000000"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#0C0C1A"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#0B1020"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#0B0E1A"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#14141F"]{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#7A7F96"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#9499A8"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#68738C"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#5B5F6E"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#7C8BB8"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="color:#2B3656"]{
    color:#AEB4C8 !important;-webkit-text-fill-color:#AEB4C8 !important;
}
/* Light inline surfaces on rd-marker pages → dark */
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#FFFFFF"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#F9F9FC"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#F4F5FF"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#EEF0FF"],
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#F9FBFF"]{
    background:#161A28 !important;border-color:#262B3E !important;
}
/* Tinted status blocks on rd pages */
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#F0FFF4"]{background:rgba(31,168,85,0.10) !important;}
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#FFF0F0"]{background:rgba(229,72,77,0.10) !important;}
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.rd-marker) [style*="background:#FFFBEB"]{background:rgba(200,150,30,0.10) !important;}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PERFORMANCE & MOTION POLISH (appearance unchanged)
#  · Theme veil: compositor-only layer for the light↔dark cross-blend.
#  · .theme-switching: suppress per-element transitions for the single
#    style pass of the theme swap (this is what removed the lag).
#  · GPU promotion of the hover/nav surfaces so their transforms never
#    trigger paint; stable scrollbar gutter kills layout shift; smooth,
#    contained scrolling on touch devices.
# ─────────────────────────────────────────────
st.markdown("""
<style>
/* Theme-transition veil — opacity + transform only (GPU compositor). */
#theme-veil{
  position:fixed;inset:-2%;z-index:2147483000;pointer-events:none;
  opacity:0;background:#FFFFFF;
  transform:translateZ(0) scale3d(1.02,1.02,1);
  will-change:opacity,transform;backface-visibility:hidden;contain:strict;
  transition:opacity 150ms cubic-bezier(0.4,0,0.2,1),
             transform 150ms cubic-bezier(0.4,0,0.2,1);
}
#theme-veil.veil-in{opacity:1;transform:translateZ(0) scale3d(1,1,1);}
#theme-veil.veil-out{
  opacity:0;transform:translateZ(0) scale3d(1.012,1.012,1);
  transition:opacity 300ms cubic-bezier(0.22,1,0.36,1),
             transform 300ms cubic-bezier(0.22,1,0.36,1);
}
/* One-pass theme swap: no per-element colour tweens fighting the
   recalculation. Removed two frames later by the toggle script. */
html.theme-switching *,
html.theme-switching *::before,
html.theme-switching *::after{transition:none !important;}

/* Rendering & scroll performance — no visual change. */
html{scrollbar-gutter:stable;}
body{overscroll-behavior-y:none;}
section[data-testid="stMain"]{-webkit-overflow-scrolling:touch;}
*{-webkit-tap-highlight-color:transparent;}
.hover-lift,.eco-card,.pnav,.pnav-dd,.octo-loading-wrap{
  transform:translateZ(0);backface-visibility:hidden;
}
.hover-lift{will-change:transform;}
.pnav-icirc,.pnav-theme svg{will-change:transform,opacity;}

/* ═══════════════════════════════════════════════════════════
   THEME-AWARE SURFACES
   Everything below is driven by CSS variables, so light and dark
   are guaranteed to stay in sync and contrast can never silently
   break: there is exactly one definition per element, not two.
   ═══════════════════════════════════════════════════════════ */
.defi-grid{
    display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
    gap:12px;margin-bottom:1.1rem;
}
.defi-card{
    background:var(--bg1);border:1px solid var(--border);border-radius:16px;
    padding:1rem 1.15rem;box-shadow:0 2px 10px rgba(20,20,60,0.05);
    transform:translateZ(0);
}
.defi-card-l{
    font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;
    color:var(--t2);margin-bottom:5px;
}
.defi-card-v{
    font-family:var(--fd,Syne),sans-serif;font-size:19px;font-weight:800;
    color:var(--t1);line-height:1.15;word-break:break-word;
}
.defi-card-s{font-size:11px;font-weight:600;margin-top:3px;}
.defi-panel,.defi-panel-solid{
    background:var(--bg1);border:1px solid var(--border);border-radius:18px;
    padding:1.4rem 1.5rem;box-shadow:0 2px 10px rgba(20,20,60,0.05);
    margin-bottom:1rem;
}
.defi-panel-t{
    font-family:var(--fd,Syne),sans-serif;font-size:14px;font-weight:800;color:var(--t1);
}
.defi-panel-s{font-size:11.5px;color:var(--t2);margin-top:2px;line-height:1.55;}
.defi-bar{height:6px;border-radius:99px;background:var(--bg2);overflow:hidden;}
.defi-bar-f{height:100%;border-radius:99px;transition:width 420ms cubic-bezier(0.22,1,0.36,1);}
.defi-gate{
    background:var(--bg1);border:1px dashed var(--border);border-radius:18px;
    padding:2rem 1.5rem;text-align:center;margin-bottom:1rem;
}
.defi-gate-warn{border-color:#F59E0B;background:rgba(245,158,11,0.06);}
.defi-gate-i{font-size:30px;margin-bottom:0.5rem;}
.defi-gate-t{
    font-family:var(--fd,Syne),sans-serif;font-size:15px;font-weight:800;
    color:var(--t1);margin-bottom:0.3rem;
}
.defi-gate-s{
    font-size:12.5px;color:var(--t2);line-height:1.6;max-width:440px;margin:0 auto;
}
.defi-gate-s b{color:var(--t1);}
.defi-note{
    background:var(--bg2);border:1px solid var(--border);border-radius:14px;
    padding:1.1rem 1.3rem;margin-bottom:0.9rem;
}
.defi-note-t{
    font-family:var(--fd,Syne),sans-serif;font-size:13px;font-weight:700;
    color:var(--t1);margin-bottom:0.35rem;
}
.defi-note-s{font-size:12px;color:var(--t2);line-height:1.65;}
.defi-eyebrow{
    font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;
    color:var(--t2);margin-bottom:0.6rem;
}
.defi-integ{
    display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
    gap:10px;margin-bottom:1rem;
}
.defi-integ-c{
    display:flex;flex-direction:column;align-items:center;gap:6px;text-align:center;
    background:var(--bg1);border:1px solid var(--border);border-radius:14px;
    padding:0.9rem 0.6rem;text-decoration:none;
    box-shadow:0 2px 8px rgba(20,20,60,0.04);
    transition:transform 240ms cubic-bezier(0.34,1.4,0.64,1),box-shadow 240ms ease;
}
.defi-integ-n{font-size:12px;font-weight:700;color:var(--t1);}
.defi-integ-t{font-size:10px;color:var(--t2);}

/* ── DARK MODE CONTRAST AUDIT ──────────────────────────────
   These target the specific low-contrast cases reported: inline
   hard-coded light backgrounds and dark text that survive the
   theme switch because they were written as literal hex values.
   Rather than restyle each card, we remap the literals so text
   inherits a readable colour in dark mode. Appearance in light
   mode is byte-for-byte unchanged. */
html[data-theme="dark"] .defi-integ-c img{
    background:#FFFFFF;padding:1px;   /* keep favicons legible on dark */
}
/* Hard-coded dark text inside inline styles → light in dark mode. */
html[data-theme="dark"] [style*="color:#0C0C1A"],
html[data-theme="dark"] [style*="color:#14141F"],
html[data-theme="dark"] [style*="color:#000000"],
html[data-theme="dark"] [style*="color:#000"],
html[data-theme="dark"] [style*="color:#1A1A2E"]{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
html[data-theme="dark"] [style*="color:#5B5F6E"],
html[data-theme="dark"] [style*="color:#7A7F96"],
html[data-theme="dark"] [style*="color:#9499A8"]{
    color:#AEB4C8 !important;-webkit-text-fill-color:#AEB4C8 !important;
}
/* Inline white/near-white card backgrounds → dark surfaces. */
html[data-theme="dark"] [style*="background:#FFFFFF"],
html[data-theme="dark"] [style*="background:#FFF"],
html[data-theme="dark"] [style*="background:#F4F5F8"],
html[data-theme="dark"] [style*="background:#F7F8FA"],
html[data-theme="dark"] [style*="background:#F8FAFF"],
html[data-theme="dark"] [style*="background:#FAFBFF"],
html[data-theme="dark"] [style*="background:#F0F1F5"]{
    background:#141826 !important;border-color:#262B3E !important;
}
/* Docs banner + chat showcase headers read as washed-out in dark. */
html[data-theme="dark"] .docs-banner{
    background:#141826 !important;border:1px solid #262B3E;
}
html[data-theme="dark"] .docs-banner-text{color:#AEB4C8 !important;}
html[data-theme="dark"] .docs-banner-text strong{color:#EDEFF7 !important;}
html[data-theme="dark"] .chat-showcase-header{background:#1B2030 !important;}
html[data-theme="dark"] .chat-showcase-title{color:#EDEFF7 !important;}
html[data-theme="dark"] .chat-showcase-sub{color:#AEB4C8 !important;}
html[data-theme="dark"] .chat-demo-user{color:#AEB4C8 !important;}
/* Metric strip + captions. */
html[data-theme="dark"] [data-testid="stMetricValue"],
html[data-theme="dark"] [data-testid="stMetricLabel"]{color:#EDEFF7 !important;}
/* Section eyebrow/sub inside dark hero blocks stay light-on-dark. */
html[data-theme="dark"] .section-dark .section-h{color:#FFFFFF !important;}
html[data-theme="dark"] .section-dark .section-sub{color:rgba(255,255,255,0.65) !important;}
/* Text inputs must never render dark-on-dark. */
html[data-theme="dark"] input[type="text"],
html[data-theme="dark"] textarea,
html[data-theme="dark"] [data-baseweb="input"] input,
html[data-theme="dark"] [data-baseweb="textarea"] textarea{
    background:#12151F !important;color:#EDEFF7 !important;border-color:#2A3044 !important;
}
html[data-theme="dark"] input::placeholder,
html[data-theme="dark"] textarea::placeholder{color:#6B7189 !important;}
/* Links inside light-authored cards. */
html[data-theme="dark"] [style*="color:#1A1AFF"]{color:#8FA0FF !important;}

/* ═══════════════════════════════════════════════════════════
   NEWS FEED — Updates & Campaigns
   Large, scannable rows rather than cramped cards: cover image
   left, content right, metadata above the headline. Stacks on
   mobile. Fully variable-driven, so dark mode is automatic.
   ═══════════════════════════════════════════════════════════ */
.nf-list{display:flex;flex-direction:column;gap:14px;margin-bottom:1.4rem;}
.nf-item{
    display:grid;grid-template-columns:220px 1fr;gap:0;
    background:var(--bg1);border:1px solid var(--border);border-radius:18px;
    overflow:hidden;text-decoration:none;
    box-shadow:0 2px 10px rgba(20,20,60,0.05);
    transform:translateZ(0);backface-visibility:hidden;
    transition:transform 240ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 240ms ease,border-color 180ms ease;
    will-change:transform;
}
.nf-item:hover{
    transform:translateY(-3px);
    box-shadow:0 12px 34px rgba(26,26,255,0.12),0 3px 10px rgba(20,20,60,0.07);
    border-color:rgba(26,26,255,0.28);
}
.nf-thumb{
    position:relative;background:linear-gradient(135deg,#EEF0FF,#E4E8FF);
    min-height:150px;overflow:hidden;
}
.nf-thumb img{
    width:100%;height:100%;object-fit:cover;display:block;
    transition:transform 420ms cubic-bezier(0.22,1,0.36,1);
}
.nf-item:hover .nf-thumb img{transform:scale(1.04);}
.nf-body{
    padding:1.15rem 1.4rem 1.15rem 1.3rem;
    display:flex;flex-direction:column;gap:7px;justify-content:center;
}
.nf-meta{display:flex;align-items:center;gap:7px;flex-wrap:wrap;}
.nf-cat{
    font-size:9px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;
    color:var(--blue,#1A1AFF);background:rgba(26,26,255,0.09);
    border:1px solid rgba(26,26,255,0.16);border-radius:20px;padding:3px 9px;
}
.nf-src{font-size:11px;font-weight:600;color:var(--t2);}
.nf-dot{font-size:11px;color:var(--t2);}
.nf-time{font-size:11px;color:var(--t2);font-variant-numeric:tabular-nums;}
.nf-title{
    font-family:var(--fd,Syne),sans-serif;font-size:16px;font-weight:800;
    color:var(--t1);line-height:1.4;letter-spacing:-0.01em;
}
.nf-summ{font-size:13px;color:var(--t2);line-height:1.62;}
.nf-cta{
    font-size:11.5px;font-weight:700;color:var(--blue,#1A1AFF);margin-top:2px;
}
.nf-thumb-camp{display:flex;align-items:center;justify-content:center;}
.nf-thumb-camp .nf-logo{
    width:76px;height:76px;border-radius:18px;object-fit:cover;
    box-shadow:0 6px 20px rgba(0,0,0,0.16);background:#fff;
}
.nf-emoji{
    font-size:52px;line-height:1;display:flex;align-items:center;justify-content:center;
    filter:drop-shadow(0 4px 14px rgba(0,0,0,0.12));
}
.nf-item:hover .nf-thumb-camp .nf-logo{transform:scale(1.05);}
html[data-theme="dark"] .nf-thumb{background:linear-gradient(135deg,#1B2030,#232941);}
html[data-theme="dark"] .nf-cat{
    color:#9FB0FF;background:rgba(90,110,255,0.16);border-color:rgba(120,140,255,0.28);
}
html[data-theme="dark"] .nf-cta{color:#9FB0FF;}
html[data-theme="dark"] .nf-item:hover{border-color:rgba(140,160,255,0.4);}

@media (max-width:820px){
    .nf-item{grid-template-columns:1fr;}
    .nf-thumb{min-height:180px;max-height:200px;}
    .nf-body{padding:1.05rem 1.2rem 1.2rem 1.2rem;}
    .nf-title{font-size:15px;}
}
@media (max-width:420px){
    .nf-thumb{min-height:150px;}
    .nf-summ{font-size:12.5px;}
}

/* Campaign cards — same enlarged, readable treatment. */
.camp-grid-lg{
    display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));
    gap:16px;margin-bottom:1.4rem;
}
@media (max-width:760px){
    .camp-grid-lg{grid-template-columns:1fr;}
}
</style>
""", unsafe_allow_html=True)


_sailor = st.query_params.get("sailor", "")[:60]
if _sailor:
    st.session_state.sailor_name = _sailor
    st.session_state.sailor_done = True
    st.session_state.page = "chat"
    st.query_params.clear()

# ─────────────────────────────────────────────
# NAV BAR (rendered on every page)
# ─────────────────────────────────────────────
logo_b64   = get_logo_b64()
price_data = get_pros_price()

NAV_PAGES = [
    ("🏠", "Home",      "home"),
    ("💬", "Chat",      "chat"),
    ("", "Campaigns", "campaigns"),
    ("📰", "Updates",   "updates"),
    ("📊", "Trade",     "trade"),
    ("🏦", "DeFi",      "defi"),
    ("🧩", "Ecosystem", "ecosystem"),
    ("💸", "Pay",       "pay"),
    ("🧾", "Request",   "request"),
    ("🌐", "Network",   "network"),
    ("⚡", "SPNs",      "spns"),
]
# ── Hidden functional nav buttons ────────────────────────────
# These are the REAL Streamlit navigation actions — identical keys and
# identical behaviour to the previous nav buttons (st.session_state is
# preserved on every click, exactly as before). They are visually hidden
# by the CSS below; the new HTML nav bar triggers them through a
# delegated click handler installed once in the parent document by the
# height-0 bootstrap component further down. No page dispatch logic,
# session handling, or routing behaviour changes.
for _n_icon, _n_label, _n_key in NAV_PAGES + [("🧠", "Memory", "memory"), ("📡", "Pulse", "pulse")]:
    if st.button(_n_label, key="nav_" + _n_key):
        st.session_state.page = _n_key
        st.rerun()

# ── New top navigation bar (replicates the reference design) ─
# Layout: [orange logo tile] [v1.2 badge] [Products ⌄ · Campaigns ·
# Updates · Explore ⌄] ... [🔍 Quick search  ⌘K] [X] [GitHub] [Discord]
# Rendered once at module level → identical appearance, dimensions and
# fixed position on every page of the app.
_pg = st.session_state.page
_PNAV_GITHUB_URL = "https://github.com/isharik/Pharos-Octobot"

_pnav_dd_products = [
    ("💬", "Chat",    "chat"),
    ("📊", "Trade",   "trade"),
    ("🏦", "DeFi",    "defi"),
    ("💸", "Pay",     "pay"),
    ("🧾", "Request", "request"),
    ("⚡", "SPNs",    "spns"),
]
_pnav_dd_explore = [
    ("🧩", "Ecosystem",     "ecosystem"),
    ("🌐", "Network",       "network"),
    ("📡", "Market Pulse",  "pulse"),
    ("🧠", "Memory Ledger", "memory"),
]

def _pnav_dd_items(items):
    out = ""
    for _ic, _lb, _pk in items:
        out += (
            '<div class="pnav-dd-item' + (" on" if _pg == _pk else "") + '" data-pnav-go="' + _pk + '">'
            '<span class="pnav-dd-ico">' + _ic + '</span><span>' + _lb + '</span></div>'
        )
    return out

_PNAV_CSS = """
<style>
/* ── NEW TOP NAV (reference replica) ─────────────────────── */
/* Hide the hidden functional nav buttons (real navigation actions). */
div[class*="st-key-nav_"]{display:none!important;}
/* Hide the height-0 bootstrap component's container so it adds no gap. */
div[data-testid="stElementContainer"]:has(iframe[height="0"]){display:none!important;}

/* Offset page content below the fixed nav (identical on every page). */
section[data-testid="stMain"] > div{padding-top:0 !important;}

.pnav-fixed{
    position:fixed;top:14px;left:0;right:0;z-index:1000;
    display:flex;justify-content:center;
    pointer-events:none;padding:0 1.25rem;
}
/* (Frosted scrim removed — the nav floats directly over the page
   background; content clears it via the container's top padding.) */
.pnav{
    pointer-events:auto;
    transform:translateZ(0);backface-visibility:hidden;
    display:flex;align-items:center;
    width:100%;max-width:1180px;height:64px;
    background:rgba(255,255,255,0.97);
    border:1px solid #E7E8EE;border-radius:16px;
    padding:0 12px;
    box-shadow:0 2px 14px rgba(20,20,60,0.09),0 1px 2px rgba(20,20,60,0.05);
    backdrop-filter:blur(14px) saturate(150%);
    -webkit-backdrop-filter:blur(14px) saturate(150%);
    font-family:'DM Sans','Inter',sans-serif;
}
/* Orange logo tile → Home */
.pnav-logo{
    width:40px;height:40px;border-radius:11px;flex-shrink:0;
    background:linear-gradient(145deg,#FF6A2B 0%,#F04A12 100%);
    display:flex;align-items:center;justify-content:center;cursor:pointer;
    box-shadow:0 2px 8px rgba(240,74,18,0.35),inset 0 1px 0 rgba(255,255,255,0.28);
    transition:transform 160ms cubic-bezier(0.34,1.4,0.64,1),box-shadow 160ms ease;
}
.pnav-logo:hover{
    transform:translateY(-1px) scale(1.04);
    box-shadow:0 5px 14px rgba(240,74,18,0.45),inset 0 1px 0 rgba(255,255,255,0.30);
}
.pnav-logo img{width:26px;height:26px;border-radius:50%;display:block;}
.pnav-logo-emoji{font-size:20px;line-height:1;}
/* Version badge */
.pnav-ver{
    display:inline-flex;align-items:center;gap:6px;margin-left:10px;flex-shrink:0;
    font-size:12.5px;font-weight:600;color:#52525B;
    background:#FFFFFF;border:1px solid #E4E4E9;border-radius:9px;
    padding:5px 9px;user-select:none;
}
/* Chevron caret */
.pnav-caret{
    width:7px;height:7px;flex-shrink:0;
    border-right:1.5px solid #A1A1AA;border-bottom:1.5px solid #A1A1AA;
    transform:rotate(45deg);margin-top:-3px;
    transition:transform 180ms cubic-bezier(0.4,0,0.2,1),margin 180ms cubic-bezier(0.4,0,0.2,1),border-color 150ms ease;
}
/* Center links */
.pnav-links{display:flex;align-items:center;gap:26px;margin-left:30px;min-width:0;}
.pnav-item{
    position:relative;display:flex;align-items:center;gap:6px;
    font-size:14px;font-weight:500;color:#3F3F46;
    cursor:pointer;padding:20px 0;user-select:none;white-space:nowrap;
    transition:color 150ms ease;
}
.pnav-item:hover{color:#0C0C1A;}
.pnav-item.on{color:#0C0C1A;font-weight:700;}
.pnav-item:hover > .pnav-caret{transform:rotate(-135deg);margin-top:3px;border-color:#0C0C1A;}
/* Hover dropdowns */
.pnav-dd{
    will-change:opacity,transform;
    position:absolute;top:calc(100% - 8px);left:-12px;min-width:198px;
    background:#FFFFFF;border:1px solid #E7E8EE;border-radius:13px;padding:6px;
    box-shadow:0 14px 38px rgba(20,20,60,0.13),0 2px 8px rgba(20,20,60,0.06);
    opacity:0;visibility:hidden;transform:translateY(7px) scale(0.985);transform-origin:top left;
    transition:opacity 170ms cubic-bezier(0.4,0,0.2,1),
               transform 170ms cubic-bezier(0.34,1.3,0.64,1),
               visibility 0s linear 170ms;
    z-index:1002;
}
.pnav-item:hover .pnav-dd{
    opacity:1;visibility:visible;transform:translateY(0) scale(1);
    transition:opacity 170ms cubic-bezier(0.4,0,0.2,1),
               transform 170ms cubic-bezier(0.34,1.3,0.64,1),
               visibility 0s;
}
.pnav-dd-item{
    display:flex;align-items:center;gap:9px;
    font-size:13px;font-weight:500;color:#3F3F46;
    border-radius:9px;padding:8px 10px;cursor:pointer;
    transition:background 130ms ease,color 130ms ease;
}
.pnav-dd-item:hover{background:#F4F5F9;color:#0C0C1A;}
.pnav-dd-item.on{background:#EEF0FF;color:#1414E8;font-weight:700;}
.pnav-dd-ico{font-size:14px;line-height:1;width:18px;text-align:center;flex-shrink:0;}
/* Tiny dot separator */
.pnav-dot{width:3px;height:3px;border-radius:50%;background:#D4D4DB;margin:0 18px 0 auto;flex-shrink:0;}
/* Quick search pill (→ Chat, also bound to ⌘K / Ctrl+K) */
.pnav-search{
    display:flex;align-items:center;gap:8px;
    height:40px;width:300px;min-width:0;flex-shrink:1;
    background:#F4F4F6;border:1px solid #ECECF1;border-radius:11px;
    padding:0 8px 0 12px;color:#9AA0AE;cursor:pointer;
    transition:border-color 150ms ease,background 150ms ease,box-shadow 150ms ease;
}
.pnav-search:hover{background:#FFFFFF;border-color:#D9DBE4;box-shadow:0 2px 8px rgba(20,20,60,0.06);}
.pnav-mag{width:15px;height:15px;flex-shrink:0;color:#9AA0AE;}
.pnav-search-ph{font-size:13.5px;font-weight:500;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.pnav-kbd{
    font-size:11px;font-weight:600;color:#6B7280;flex-shrink:0;
    background:#FFFFFF;border:1px solid #E4E4E9;border-radius:6px;
    padding:3px 6px;box-shadow:0 1px 0 rgba(20,20,60,0.05);
}
/* Circular social icon buttons */
.pnav-socials{display:flex;align-items:center;gap:8px;margin-left:12px;flex-shrink:0;}
.pnav-icirc{
    width:40px;height:40px;border-radius:50%;
    background:#F4F4F6;border:1px solid #ECECF1;
    display:flex;align-items:center;justify-content:center;
    color:#17181C;text-decoration:none;
    transition:transform 150ms cubic-bezier(0.34,1.4,0.64,1),
               background 150ms ease,border-color 150ms ease,box-shadow 150ms ease;
}
.pnav-icirc:hover{
    background:#FFFFFF;border-color:#D9DBE4;color:#000;
    transform:translateY(-1px);box-shadow:0 4px 10px rgba(20,20,60,0.10);
}
.pnav-icirc svg{width:17px;height:17px;display:block;}
.pnav-icirc svg path{fill:currentColor;}
.pnav-icirc[title="Discord"]:hover{color:#5865F2;border-color:#5865F2;}
.pnav-icirc[title="X / Twitter"]:hover{color:#000;}
.pnav-icirc[title="GitHub"]:hover{color:#000;}
html[data-theme="dark"] .pnav-icirc[title="Discord"]:hover{color:#7C88FF;border-color:#5865F2;}
html[data-theme="dark"] .pnav-icirc[title="X / Twitter"]:hover,
html[data-theme="dark"] .pnav-icirc[title="GitHub"]:hover{color:#FFFFFF;}
.pnav-theme{cursor:pointer;padding:0;}
.pnav-theme svg{position:absolute;width:17px;height:17px;transition:opacity 200ms ease,transform 300ms cubic-bezier(0.34,1.4,0.64,1);}
.pnav-theme .ic-moon{opacity:0;transform:rotate(-40deg) scale(0.6);}
.pnav-theme .ic-sun{opacity:1;transform:rotate(0) scale(1);}
html[data-theme="dark"] .pnav-theme .ic-sun{opacity:0;transform:rotate(40deg) scale(0.6);}
html[data-theme="dark"] .pnav-theme .ic-moon{opacity:1;transform:rotate(0) scale(1);}
.pnav-theme{position:relative;overflow:hidden;}

/* ── COMMAND PALETTE ─────────────────────────────────────── */
#octo-palette{position:fixed;inset:0;z-index:100000;display:none;}
#octo-palette.open{display:block;}
#octo-palette .op-backdrop{
    position:absolute;inset:0;background:rgba(12,14,26,0.42);
    backdrop-filter:blur(4px);-webkit-backdrop-filter:blur(4px);
    animation:opFade 160ms ease;
}
#octo-palette .op-modal{
    position:absolute;top:14vh;left:50%;transform:translateX(-50%);
    width:min(600px,92vw);
    background:rgba(255,255,255,0.98);border:1px solid #E7E8EE;border-radius:16px;
    box-shadow:0 24px 70px rgba(12,14,40,0.34);
    overflow:hidden;font-family:'DM Sans',sans-serif;
    animation:opPop 200ms cubic-bezier(0.34,1.3,0.64,1);
}
@keyframes opFade{from{opacity:0;}to{opacity:1;}}
@keyframes opPop{from{opacity:0;transform:translateX(-50%) translateY(-10px) scale(0.98);}
                 to{opacity:1;transform:translateX(-50%) translateY(0) scale(1);}}
#octo-palette .op-search{display:flex;align-items:center;gap:10px;padding:14px 16px;border-bottom:1px solid #ECEDF3;}
#octo-palette .op-search svg{width:18px;height:18px;color:#9AA0AE;flex-shrink:0;}
#octo-palette #op-input{
    flex:1;border:none;outline:none;background:transparent;
    font-size:15px;font-weight:500;color:#0C0C1A;font-family:inherit;
}
#octo-palette #op-input::placeholder{color:#9AA0AE;}
#octo-palette .op-esc{font-size:10px;font-weight:700;color:#9AA0AE;background:#F2F3F8;border:1px solid #E4E4E9;border-radius:5px;padding:3px 6px;}
#octo-palette .op-list{max-height:46vh;overflow-y:auto;padding:6px;}
#octo-palette .op-group{font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#9AA0AE;padding:8px 10px 4px;}
#octo-palette .op-row{display:flex;align-items:center;gap:11px;padding:9px 11px;border-radius:10px;cursor:pointer;}
#octo-palette .op-row.on{background:#EEF0FF;}
#octo-palette .op-ico{font-size:15px;width:20px;text-align:center;flex-shrink:0;}
#octo-palette .op-title{font-size:13.5px;font-weight:600;color:#1A1F30;flex:1;}
#octo-palette .op-row.on .op-title{color:#1414E8;}
#octo-palette .op-tag{font-size:9px;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;color:#6B7280;background:#F2F3F8;border:1px solid #E4E4E9;border-radius:5px;padding:2px 6px;}
#octo-palette .op-empty{padding:26px;text-align:center;color:#9AA0AE;font-size:13px;}
#octo-palette .op-foot{display:flex;gap:16px;padding:9px 16px;border-top:1px solid #ECEDF3;font-size:10.5px;font-weight:600;color:#9AA0AE;}
/* dark */
html[data-theme="dark"] #octo-palette .op-modal{background:#14172250;background:#141722;border-color:#262B3E;box-shadow:0 24px 70px rgba(0,0,0,0.6);}
html[data-theme="dark"] #octo-palette .op-search{border-color:#242A3B;}
html[data-theme="dark"] #octo-palette #op-input{color:#EDEFF7;}
html[data-theme="dark"] #octo-palette .op-esc{background:#1B1F30;border-color:#2C3247;color:#AEB4C8;}
html[data-theme="dark"] #octo-palette .op-row.on{background:rgba(60,80,255,0.16);}
html[data-theme="dark"] #octo-palette .op-title{color:#DDE0EE;}
html[data-theme="dark"] #octo-palette .op-row.on .op-title{color:#9FB0FF;}
html[data-theme="dark"] #octo-palette .op-tag{background:#1B1F30;border-color:#2C3247;color:#AEB4C8;}
html[data-theme="dark"] #octo-palette .op-foot{border-color:#242A3B;}

/* Responsive — degrade gracefully, never overlap or clip */
@media (max-width:1120px){
    .pnav-search{width:220px;}
    .pnav-links{gap:20px;margin-left:22px;}
}
@media (max-width:980px){
    .pnav-kbd{display:none;}
    .pnav-search{width:44px;padding:0;justify-content:center;}
    .pnav-search-ph{display:none;}
}
@media (max-width:860px){
    .pnav-ver{display:none;}
    .pnav-links{gap:16px;margin-left:16px;}
}
@media (max-width:700px){
    .pnav-dot{display:none;}
    .pnav-socials .pnav-icirc:nth-child(2){display:none;}
}
/* Home sentiment orb: pinned to the extreme left corner by its own
   script (frameElement inline styles, validated + cleaned up by the
   parent bootstrap when Streamlit recycles the container node). */

@media (max-width:600px){
    .pnav-socials .pnav-icirc:not(:last-child){display:none;}
    .pnav{height:58px;border-radius:14px;padding:0 10px;}
    .pnav-fixed{top:10px;padding:0 0.75rem;}
    .pnav-item{font-size:13px;padding:17px 0;}
    section[data-testid="stMain"] > div{padding-top:0 !important;}
}
</style>
"""

_PNAV_X_SVG = (
    '<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68'
    'l7.73-8.835L1.254 2.25H8.08l4.713 6.231 5.451-6.231zm-1.161 17.52h1.833L7.084 4.126H5.117'
    'l11.966 15.644z"/></svg>'
)
_PNAV_GH_SVG = (
    '<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.56'
    '0-.28-.01-1.02-.02-2-3.2.7-3.88-1.54-3.88-1.54-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.71.08-.71'
    '1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.75.4-1.26.73-1.55-2.55-.29-5.23-1.28-5.23-5.68'
    '0-1.26.45-2.28 1.19-3.09-.12-.29-.52-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 2.9-.39'
    'c.98 0 1.97.13 2.9.39 2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.19 1.83 1.19 3.09'
    '0 4.41-2.69 5.38-5.25 5.66.41.36.78 1.06.78 2.14 0 1.55-.01 2.79-.01 3.17 0 .31.21.68.8.56'
    'A10.52 10.52 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z"/></svg>'
)
_PNAV_SUN_SVG = (
    '<svg class="ic-sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="12" cy="12" r="4"></circle>'
    '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path></svg>'
)
_PNAV_MOON_SVG = (
    '<svg class="ic-moon" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>'
)
_PNAV_DC_SVG = (
    '<svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">'
    '<path d="M20.317 4.37a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25'
    'a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.74 19.74 0 0 0 3.677 4.37'
    'a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.058a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03'
    'a.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892'
    'a.077.077 0 0 1-.008-.128c.126-.094.252-.192.372-.291a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0'
    'a.074.074 0 0 1 .078.009c.12.099.246.198.373.292a.077.077 0 0 1-.006.127 12.3 12.3 0 0 1-1.873.892'
    'a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.84 19.84 0 0 0 6.002-3.03'
    'a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33'
    'c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42'
    '0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419'
    '1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>'
)

if logo_b64:
    _pnav_logo_inner = '<img src="' + logo_b64 + '" alt="OctoBot" />'
else:
    _pnav_logo_inner = '<span class="pnav-logo-emoji">🐙</span>'

_pnav_html = (
    '<div class="pnav-fixed"><nav class="pnav">'
    '<div class="pnav-logo" data-pnav-go="home" title="OctoBot · Home">' + _pnav_logo_inner + '</div>'
    '<div class="pnav-ver">v1.2<span class="pnav-caret"></span></div>'
    '<div class="pnav-links">'
    '<div class="pnav-item' + (" on" if _pg in ("chat", "trade", "defi", "pay", "request", "spns") else "") + '">Products<span class="pnav-caret"></span>'
    '<div class="pnav-dd">' + _pnav_dd_items(_pnav_dd_products) + '</div>'
    '</div>'
    '<div class="pnav-item' + (" on" if _pg == "campaigns" else "") + '" data-pnav-go="campaigns">Campaigns</div>'
    '<div class="pnav-item' + (" on" if _pg == "updates" else "") + '" data-pnav-go="updates">Updates</div>'
    '<div class="pnav-item' + (" on" if _pg in ("ecosystem", "network", "memory", "pulse") else "") + '">Explore<span class="pnav-caret"></span>'
    '<div class="pnav-dd">' + _pnav_dd_items(_pnav_dd_explore) + '</div>'
    '</div>'
    '</div>'
    '<span class="pnav-dot"></span>'
    '<div class="pnav-search" id="pnav-search-pill" title="Search — pages, actions, docs (Ctrl/Cmd + K)">'
    '<svg class="pnav-mag" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" xmlns="http://www.w3.org/2000/svg">'
    '<circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.5" y2="16.5"></line></svg>'
    '<span class="pnav-search-ph">Quick search...</span>'
    '<span class="pnav-kbd">⌘K</span>'
    '</div>'
    '<button class="pnav-icirc pnav-theme" id="pnav-theme-btn" title="Toggle dark mode" aria-label="Toggle dark mode">' + _PNAV_SUN_SVG + _PNAV_MOON_SVG + '</button>'
    '<div class="pnav-socials">'
    '<a class="pnav-icirc" href="' + PHAROS_X_URL + '" target="_blank" rel="noopener" title="X / Twitter">' + _PNAV_X_SVG + '</a>'
    '<a class="pnav-icirc" href="' + _PNAV_GITHUB_URL + '" target="_blank" rel="noopener" title="GitHub">' + _PNAV_GH_SVG + '</a>'
    '<a class="pnav-icirc" href="' + PHAROS_DISCORD_URL + '" target="_blank" rel="noopener" title="Discord">' + _PNAV_DC_SVG + '</a>'
    '</div>'
    '</nav></div>'
)

# ── GLOBAL CONNECT WALLET (fixed top-right, every page) ──────
# Separate from the nav bar, as a fixed overlay. Rendered on every page
# from module level, so it is always present and always consistent.
# Purely presentational here — the parent-document script below owns all
# provider logic and keeps this pill's contents in sync.
_w3a   = st.session_state.get("w3_address", "")
_w3c   = st.session_state.get("w3_chain", "")
_w3l   = st.session_state.get("w3_label", "") or "Wallet"
_short = (_w3a[:6] + "…" + _w3a[-4:]) if _w3a else ""
_right_net = (_w3c or "").lower() == PHAROS_CHAIN_ID_HEX.lower()

if _w3a:
    _dot = "#22C55E" if _right_net else "#F59E0B"
    _net = "Pharos" if _right_net else "Wrong network"
    _wallet_pill = (
        '<div class="w3-pill w3-on" id="w3-pill" title="' + esc(_w3a) + '">'
        '<span class="w3-dot" style="background:' + _dot + ';"></span>'
        '<span class="w3-net">' + esc(_net) + '</span>'
        '<span class="w3-sep"></span>'
        '<span class="w3-addr">' + esc(_short) + '</span>'
        + ('<button class="w3-switch" id="w3-switch-btn" title="Switch to Pharos Mainnet">Switch</button>'
           if not _right_net else '')
        + '<button class="w3-x" id="w3-disconnect-btn" title="Disconnect">✕</button>'
        '</div>'
    )
else:
    _wallet_pill = (
        '<div class="w3-pill" id="w3-pill">'
        '<button class="w3-connect" id="w3-connect-btn">'
        '<span class="w3-ico">🔗</span><span class="w3-lbl">Connect Wallet</span></button>'
        '</div>'
    )

_W3_CSS = """
<style>
/* ── GLOBAL CONNECT WALLET — fixed top-right overlay ───────── */
.w3-fixed{
    position:fixed;top:14px;right:18px;z-index:1002;
    display:flex;justify-content:flex-end;pointer-events:none;
}
.w3-pill{
    pointer-events:auto;display:inline-flex;align-items:center;gap:8px;
    background:#FFFFFF;border:1px solid #E3E5EA;border-radius:999px;
    padding:5px 6px 5px 12px;height:38px;
    box-shadow:0 4px 16px rgba(20,20,60,0.10);
    transform:translateZ(0);
    transition:border-color 160ms ease,box-shadow 200ms ease,background 160ms ease;
}
.w3-pill:hover{border-color:#C3C7D4;box-shadow:0 6px 22px rgba(20,20,60,0.14);}
.w3-connect{
    display:inline-flex;align-items:center;gap:7px;border:none;cursor:pointer;
    background:var(--blue,#1A1AFF);color:#fff;border-radius:999px;
    font-family:inherit;font-size:12.5px;font-weight:700;letter-spacing:0.01em;
    padding:7px 15px;line-height:1;
    transition:transform 180ms cubic-bezier(0.34,1.4,0.64,1),background 160ms ease;
    will-change:transform;
}
.w3-connect:hover{background:#0F0FCC;transform:translateY(-1px);}
.w3-connect:active{transform:translateY(0) scale(0.98);}
.w3-ico{font-size:12px;}
.w3-dot{width:7px;height:7px;border-radius:50%;flex-shrink:0;}
.w3-net{font-size:11px;font-weight:700;color:#5B5F6E;letter-spacing:0.02em;}
.w3-sep{width:1px;height:14px;background:#E3E5EA;}
.w3-addr{font-size:12px;font-weight:700;color:#14141F;font-variant-numeric:tabular-nums;}
.w3-switch{
    border:none;cursor:pointer;background:#FEF3C7;color:#92400E;
    border-radius:999px;font-family:inherit;font-size:10.5px;font-weight:700;
    padding:4px 9px;line-height:1;transition:background 150ms ease;
}
.w3-switch:hover{background:#FDE68A;}
.w3-x{
    border:none;cursor:pointer;background:#F1F2F6;color:#5B5F6E;
    width:24px;height:24px;border-radius:50%;font-size:11px;line-height:1;
    display:flex;align-items:center;justify-content:center;
    transition:background 150ms ease,color 150ms ease;
}
.w3-x:hover{background:#FFE4E6;color:#E5484D;}
/* ── Wallet picker modal ── */
.w3-modal{position:fixed;inset:0;z-index:2147483100;opacity:0;
    transition:opacity 180ms cubic-bezier(0.4,0,0.2,1);}
.w3-modal.on{opacity:1;}
.w3-modal-bd{position:absolute;inset:0;background:rgba(10,10,25,0.45);
    backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);}
.w3-modal-c{
    position:absolute;top:50%;left:50%;width:min(360px,calc(100vw - 32px));
    transform:translate(-50%,-48%) translateZ(0);
    background:#FFFFFF;border:1px solid #E3E5EA;border-radius:18px;
    box-shadow:0 24px 70px rgba(10,10,40,0.30);overflow:hidden;
    transition:transform 220ms cubic-bezier(0.34,1.4,0.64,1);
}
.w3-modal.on .w3-modal-c{transform:translate(-50%,-50%) translateZ(0);}
.w3-modal-h{display:flex;align-items:center;justify-content:space-between;
    padding:14px 16px;border-bottom:1px solid #EFF0F4;
    font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#14141F;}
.w3-modal-x{border:none;background:transparent;cursor:pointer;font-size:13px;
    color:#9499A8;border-radius:8px;padding:4px 7px;line-height:1;
    transition:background 140ms ease,color 140ms ease;}
.w3-modal-x:hover{background:#F3F4F8;color:#14141F;}
.w3-modal-l{padding:8px;display:flex;flex-direction:column;gap:4px;
    max-height:min(52vh,340px);overflow-y:auto;}
.w3-wrow{
    display:flex;align-items:center;gap:11px;width:100%;
    border:1px solid transparent;background:transparent;cursor:pointer;
    border-radius:12px;padding:10px 11px;text-align:left;font-family:inherit;
    transition:background 140ms ease,border-color 140ms ease,transform 140ms ease;
}
.w3-wrow:hover{background:#F6F7FB;border-color:#E3E5EA;transform:translateX(2px);}
.w3-wi{width:28px;height:28px;border-radius:8px;flex-shrink:0;object-fit:contain;
    background:#F3F4F8;}
.w3-wi-ph{display:inline-flex;align-items:center;justify-content:center;
    font-size:13px;font-weight:800;color:#5B5F6E;}
.w3-wn{font-size:13px;font-weight:700;color:#14141F;flex:1;}
.w3-wtag{font-size:9px;font-weight:700;letter-spacing:0.04em;text-transform:uppercase;
    color:#B45309;background:#FEF3C7;border:1px solid #FDE68A;
    border-radius:7px;padding:2px 6px;}
.w3-modal-f{padding:10px 16px 14px;font-size:10.5px;color:#9499A8;line-height:1.5;
    border-top:1px solid #EFF0F4;}
html[data-theme="dark"] .w3-modal-c{background:#141826;border-color:#2A3044;}
html[data-theme="dark"] .w3-modal-h{color:#EDEFF7;border-bottom-color:#232838;}
html[data-theme="dark"] .w3-modal-l .w3-wrow:hover{background:#1C2132;border-color:#333A50;}
html[data-theme="dark"] .w3-wn{color:#EDEFF7;}
html[data-theme="dark"] .w3-modal-f{color:#8A90A6;border-top-color:#232838;}
html[data-theme="dark"] .w3-modal-x:hover{background:#232838;color:#EDEFF7;}
html[data-theme="dark"] .w3-wi,html[data-theme="dark"] .w3-wi-ph{background:#1C2132;}

.w3-toast{
    position:fixed;top:62px;right:18px;z-index:1003;pointer-events:none;
    background:#14141F;color:#fff;border-radius:12px;padding:9px 14px;
    font-size:12px;font-weight:600;max-width:320px;
    box-shadow:0 10px 30px rgba(0,0,0,0.28);
    opacity:0;transform:translateY(-6px) translateZ(0);
    transition:opacity 220ms ease,transform 220ms cubic-bezier(0.22,1,0.36,1);
}
.w3-toast.on{opacity:1;transform:translateY(0) translateZ(0);}
.w3-toast.err{background:#7F1D1D;}
.w3-toast.ok{background:#14532D;}

/* Dark theme */
html[data-theme="dark"] .w3-pill{background:#141826;border-color:#2A3044;box-shadow:0 4px 18px rgba(0,0,0,0.5);}
html[data-theme="dark"] .w3-pill:hover{border-color:#3A4258;}
html[data-theme="dark"] .w3-net{color:#AEB4C8;}
html[data-theme="dark"] .w3-addr{color:#EDEFF7;}
html[data-theme="dark"] .w3-sep{background:#2A3044;}
html[data-theme="dark"] .w3-x{background:#1B2030;color:#AEB4C8;}
html[data-theme="dark"] .w3-x:hover{background:#3B1D1F;color:#FF6B6E;}

/* Keep the pill clear of the nav on narrow screens */
@media (max-width:1120px){
    .w3-fixed{top:auto;bottom:16px;right:16px;}
}
@media (max-width:420px){
    .w3-addr,.w3-net,.w3-sep{display:none;}
    .w3-pill{padding:5px 6px;}
}
</style>
"""
st.markdown(_PNAV_CSS + _pnav_html, unsafe_allow_html=True)
st.markdown(_W3_CSS + '<div class="w3-fixed">' + _wallet_pill + '</div>', unsafe_allow_html=True)

# ── Bootstrap: GSAP + nav wiring + ⌘K + fluid transitions + Aura Swirl ─
# A height-0 component that injects a one-time script INTO THE PARENT
# DOCUMENT (same idempotent, same-origin pattern already used by the
# assistant-bubble navigation above). Running in the parent realm means
# the handlers and animations survive Streamlit reruns.
#
#  1. Loads GSAP 3.12 from cdnjs into the parent page. Every animation
#     below uses GSAP when available and falls back to equivalent
#     vanilla easing if the CDN is unreachable — navigation itself
#     never depends on GSAP.
#  2. window.__pnavGo(page): fluid page transition (quick GSAP fade/
#     lift of the main content) and then a click on the matching hidden
#     Streamlit nav button → navigation keeps using st.session_state
#     exactly like before (no reloads, no session loss).
#  3. Delegated handler: any element with data-pnav-go="<page>" routes
#     through __pnavGo. Cmd/Ctrl+K → Chat (matches the ⌘K pill).
#  4. AURA SWIRL — a fixed, pointer-events:none canvas inserted inside
#     stAppViewContainer at z-index:0: it paints ABOVE the existing
#     wave/aura/dot background layers (same z-index, later in DOM) but
#     BELOW all real content (z-index:1), so it reads as embedded in
#     the background rather than layered on top. Three logarithmic
#     spiral arms + depth-sorted particles are drawn on a mouse-tilted
#     3D plane; energy is tweened with GSAP (power3.out in — snappy;
#     long power2 fade out) and only animates on hover/scroll. The rAF
#     loop fully stops at rest → zero idle cost. Colours are sampled
#     from the existing scheme (#1A1AFF / #6B6BFF / periwinkle).
#     Honors prefers-reduced-motion.
components.html(
    """
<script>
(function(){
  function PNAV_PARENT_MAIN(){
    if (window.__pnavBoot) return;
    window.__pnavBoot = true;
    var doc = document;

    /* ── GSAP loader (graceful) ─────────────────────────── */
    var gsapReady = false;
    (function(){
      if (window.gsap){ gsapReady = true; return; }
      var g = doc.createElement('script');
      g.src = 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js';
      g.async = true;
      g.onload = function(){ gsapReady = !!window.gsap; };
      doc.head.appendChild(g);
    })();

    /* Keep the fixed nav OUTSIDE the app container: if any page applies
       a transform/filter to the main content (e.g. the fluid page
       transition), position:fixed inside it would anchor to that
       container instead of the viewport — the "nav stuck to the top"
       bug on some pages. Relocating the freshly rendered nav node to
       document.body makes its positioning identical on every page. */
    /* Streamlit recycles DOM nodes when switching pages: a container that
       hosted the Home orb (pinned with fixed/96px inline styles) can be
       reused for ordinary text on another page, breaking its layout.
       Validate every pinned holder: it must still contain the live orb
       iframe (identified by window.__isOrb inside it) or it gets fully
       unpinned. Runs on every DOM mutation via the observer below. */
    /* ── Scroll-reveal engine (3D entrances) ─────────────
       Any main-column element that first appears below the fold gets a
       one-shot 3D tilt-up entrance when scrolled into view. Fully
       self-cleaning: classes are removed after the transition so no
       transform or stacking context is left behind. New elements from
       Streamlit reruns are picked up by the same mutation observer
       that maintains the nav. */
    var srIO = null;
    try{
      srIO = new IntersectionObserver(function(entries){
        for (var qi = 0; qi < entries.length; qi++){
          var en2 = entries[qi];
          if (!en2.isIntersecting) continue;
          var el2 = en2.target;
          srIO.unobserve(el2);
          el2.classList.add('sr-in');
          (function(node){
            var done = function(){
              node.classList.remove('sr-pre');
              node.classList.remove('sr-in');
              node.style.willChange = '';
              node.removeEventListener('transitionend', done);
            };
            node.addEventListener('transitionend', done);
            setTimeout(done, 750);   /* fallback */
          })(el2);
        }
      }, {rootMargin: '0px 0px -6% 0px'});
    }catch(e){}

    function scanReveal(){
      if (!srIO) return;
      try{
        var els = doc.querySelectorAll(
          'section[data-testid="stMain"] div[data-testid="stElementContainer"]:not([data-sr])');
        var vh = window.innerHeight;
        for (var ei = 0; ei < els.length; ei++){
          var el3 = els[ei];
          el3.setAttribute('data-sr', '1');
          var rc = el3.getBoundingClientRect();
          /* only below-the-fold, visible-sized blocks get an entrance */
          if (rc.height < 8 || rc.width < 8) continue;
          if (rc.top < vh * 0.92) continue;
          el3.classList.add('sr-pre');
          srIO.observe(el3);
        }
      }catch(e){}
    }

    function orbCleanup(){
      try{
        var holders = doc.querySelectorAll('[data-orb-holder]');
        for (var h = 0; h < holders.length; h++){
          var el = holders[h];
          var fr = el.querySelector('iframe');
          var ok = false;
          try{ ok = !!(fr && fr.contentWindow && fr.contentWindow.__isOrb === true); }catch(e){}
          if (!ok){
            el.removeAttribute('data-orb-holder');
            el.style.position = '';
            el.style.top = ''; el.style.bottom = ''; el.style.left = '';
            el.style.width = ''; el.style.height = '';
            el.style.zIndex = ''; el.style.margin = ''; el.style.padding = '';
            if (fr){ fr.style.width = ''; fr.style.height = ''; }
          }
        }
      }catch(e){}
    }

    function relocateNav(){
      orbCleanup();
      scanReveal();
      try{
        var navs = Array.prototype.slice.call(doc.querySelectorAll('.pnav-fixed'));
        if (!navs.length) return;
        var inside = navs.filter(function(n){ return !n.__pnavMoved; });
        if (!inside.length) return;
        var fresh = inside[inside.length - 1];
        navs.forEach(function(n){ if (n !== fresh && n.__pnavMoved) n.remove(); });
        fresh.__pnavMoved = true;
        doc.body.appendChild(fresh);
      }catch(e){}
    }
    relocateNav();
    try{
      var appRoot = doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;
      new MutationObserver(function(){ relocateNav(); }).observe(appRoot, {childList:true, subtree:true});
    }catch(e){}

    function navButton(key){
      return doc.querySelector('[class*="st-key-nav_' + key + '"] button');
    }
    function mainEl(){
      return doc.querySelector('section[data-testid="stMain"] > div');
    }

    /* ── Fluid page transition + navigation ─────────────── */
    var navBusy = false;
    window.__pnavGo = function(key){
      var btn = navButton(key);
      if (!btn) return;
      if (navBusy){ btn.click(); return; }
      var m = mainEl();
      if (gsapReady && window.gsap && m){
        navBusy = true;
        window.gsap.to(m, {opacity:0.18, duration:0.14, ease:'power2.in',
          onComplete:function(){
            btn.click();
            setTimeout(function(){
              window.gsap.fromTo(m, {opacity:0.18},
                {opacity:1, duration:0.28, ease:'power3.out', clearProps:'opacity',
                 onComplete:function(){ navBusy = false; }});
            }, 240);
          }});
      } else if (m){
        navBusy = true;
        m.style.transition = 'opacity 140ms ease';
        m.style.opacity = '0.25';
        setTimeout(function(){
          btn.click();
          setTimeout(function(){
            m.style.opacity = '1';
            setTimeout(function(){ m.style.transition=''; navBusy=false; }, 260);
          }, 240);
        }, 140);
      } else {
        btn.click();
      }
    };

    /* Delegated nav clicks */
    doc.addEventListener('click', function(e){
      var t = e.target && e.target.closest ? e.target.closest('[data-pnav-go]') : null;
      if (!t) return;
      var k = t.getAttribute('data-pnav-go');
      if (k) window.__pnavGo(k);
    }, true);

    /* ── THEME TOGGLE (dark mode) ─────────────────────────
       Persisted in localStorage; applied to <html data-theme>. */
    function applyTheme(mode){
      try{ doc.documentElement.setAttribute('data-theme', mode === 'dark' ? 'dark' : 'light'); }catch(e){}
    }
    /* Premium GPU-accelerated theme switch.
       Why the old swap lagged: flipping data-theme forces the browser
       to re-match hundreds of html[data-theme="dark"] … !important
       rules AND run every per-element colour transition at once —
       one giant style/paint storm on the main thread.
       Fix: (1) add .theme-switching for the swap so per-element
       transitions are suppressed → the recalculation happens in a
       single cheap pass; (2) mask that single pass with a full-screen
       compositor-only veil animated purely with opacity + transform
       (translateZ/scale — GPU layers, zero layout, zero paint), giving
       a subtle depth cross-blend into the new theme at 60fps without
       ever blocking input (pointer-events:none). */
    var __themeBusy = false;
    function switchTheme(next){
      if (__themeBusy) return;
      try{
        if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches){
          applyTheme(next);
          try{ localStorage.setItem('octobot-theme', next); }catch(e){}
          return;
        }
      }catch(e){}
      __themeBusy = true;
      var root = doc.documentElement;
      var veil = doc.getElementById('theme-veil');
      if (!veil){
        veil = doc.createElement('div');
        veil.id = 'theme-veil';
        doc.body.appendChild(veil);
      }
      veil.style.background = (next === 'dark') ? '#0B0E1A' : '#FFFFFF';
      root.classList.add('theme-switching');
      /* force layout of the veil once so the transition actually runs */
      void veil.offsetWidth;
      veil.classList.remove('veil-out');
      veil.classList.add('veil-in');
      var swapped = false;
      function doSwap(){
        if (swapped) return; swapped = true;
        applyTheme(next);
        try{ localStorage.setItem('octobot-theme', next); }catch(e){}
        requestAnimationFrame(function(){ requestAnimationFrame(function(){
          root.classList.remove('theme-switching');
          veil.classList.remove('veil-in');
          veil.classList.add('veil-out');
          setTimeout(function(){
            veil.classList.remove('veil-out');
            __themeBusy = false;
          }, 340);
        }); });
      }
      veil.addEventListener('transitionend', doSwap, { once: true });
      setTimeout(doSwap, 240); /* safety net if transitionend is swallowed */
    }
    try{ window.__octoSwitchTheme = switchTheme; }catch(e){}
    (function(){
      var saved = 'light';
      try{ saved = localStorage.getItem('octobot-theme') || 'light'; }catch(e){}
      applyTheme(saved);
    })();
    doc.addEventListener('click', function(e){
      var tb = e.target && e.target.closest ? e.target.closest('#pnav-theme-btn') : null;
      if (!tb) return;
      var cur = doc.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      switchTheme(cur === 'dark' ? 'light' : 'dark');
    }, true);

    /* ── EIP-1193 WALLET BRIDGE ───────────────────────────
       Real wallet integration against the injected provider. Works with
       any EVM wallet that follows EIP-1193 (MetaMask, OKX, Rabby,
       Coinbase, Brave, Trust…). Prefers EIP-6963 multi-wallet discovery
       and falls back to window.ethereum.

       This runs in the PARENT document (not a sandboxed iframe), which
       is the only place window.ethereum is reachable — that is why the
       connect button is injected here rather than rendered in a
       component. State is reported back to Python via query params. */
    var W3_CHAIN_HEX  = '0x688';   /* 1672 — Pharos Pacific Mainnet */
    var W3_CHAIN_NAME = 'Pharos Pacific Mainnet';
    var W3_RPC        = 'https://rpc.pharos.xyz';
    var W3_EXPLORER   = 'https://pharosscan.xyz';
    var W3_SYMBOL     = 'PROS';

    /* EIP-6963 multi-wallet discovery.
       Wallets answer 'eip6963:requestProvider' ASYNCHRONOUSLY, and
       extensions inject window.ethereum at document_idle — which can be
       after this bootstrap runs. So we must not probe once and cache the
       answer: we keep the listener alive, re-broadcast the request a few
       times while the page settles, and re-check at click time. */
    var w3providers = [];
    function w3announce(d){
      try{
        if (!d || !d.provider) return;
        for (var i=0;i<w3providers.length;i++){
          if (w3providers[i].info && d.info && w3providers[i].info.uuid === d.info.uuid) return;
        }
        w3providers.push(d);
        w3paint();   /* a wallet appeared → refresh the button label */
      }catch(e){}
    }
    function w3scan(){
      try{ window.dispatchEvent(new Event('eip6963:requestProvider')); }catch(e){}
    }
    try{
      window.addEventListener('eip6963:announceProvider', function(ev){ w3announce(ev.detail); });
      w3scan();
      /* Re-broadcast while the page settles — covers wallets that inject
         late, and wallets that only answer once the DOM is ready. */
      if (doc.readyState === 'loading'){
        doc.addEventListener('DOMContentLoaded', w3scan, { once: true });
      }
      window.addEventListener('load', w3scan);
      var w3tries = 0;
      var w3poll = setInterval(function(){
        w3scan();
        if (++w3tries > 12 || w3providers.length) clearInterval(w3poll);
      }, 250);
    }catch(e){}

    function w3eth(){
      /* window.ethereum, unwrapping multi-provider arrays. Read LIVE —
         never cached, because injection may happen after boot. */
      var eth = window.ethereum;
      if (!eth) return null;
      if (eth.providers && eth.providers.length){
        return eth.providers.find(function(x){ return x.isMetaMask; }) || eth.providers[0];
      }
      return eth;
    }

    /* Is this provider actually usable for EVM?
       Phantom/Solflare inject an `ethereum` shim that often rejects
       eth_requestAccounts with -32603. We do not hide them (Phantom's
       EVM support is real when enabled) — we just never auto-pick one,
       and we label them so the choice is informed. */
    function w3isSolanaFirst(p, name){
      try{
        var n = (name || '').toLowerCase();
        if (n.indexOf('phantom') !== -1 || n.indexOf('solflare') !== -1) return true;
        if (p && (p.isPhantom || p.isSolflare)) return true;
      }catch(e){}
      return false;
    }

    /* Every installed wallet, de-duplicated, best-first. */
    function w3list(){
      if (!w3providers.length) w3scan();
      var out = [], seen = [];
      function push(p, name, icon, uuid){
        if (!p) return;
        for (var i = 0; i < seen.length; i++){ if (seen[i] === p) return; }
        seen.push(p);
        out.push({ p: p, name: name || w3name(p), icon: icon || '',
                   uuid: uuid || '', solFirst: w3isSolanaFirst(p, name || w3name(p)) });
      }
      /* EIP-6963 — the modern, unambiguous source (name + icon + uuid). */
      for (var i = 0; i < w3providers.length; i++){
        var d = w3providers[i];
        push(d.provider, d.info && d.info.name, d.info && d.info.icon, d.info && d.info.uuid);
      }
      /* Legacy window.ethereum.providers[] — wallets that predate 6963. */
      try{
        var eth = window.ethereum;
        if (eth && eth.providers && eth.providers.length){
          for (var j = 0; j < eth.providers.length; j++){ push(eth.providers[j]); }
        } else if (eth){ push(eth); }
      }catch(e){}
      /* EVM-native wallets first; Solana-first shims last. */
      out.sort(function(a, b){ return (a.solFirst ? 1 : 0) - (b.solFirst ? 1 : 0); });
      return out;
    }

    function w3get(){
      /* Single best candidate — used only for labelling, never to
         silently connect when several wallets exist. */
      var l = w3list();
      return l.length ? l[0] : null;
    }
    function w3has(){ return w3list().length > 0; }
    function w3name(p){
      if (!p) return 'Wallet';
      if (p.isRabby) return 'Rabby';
      if (p.isOkxWallet || p.isOKExWallet) return 'OKX';
      if (p.isCoinbaseWallet) return 'Coinbase';
      if (p.isTrust) return 'Trust';
      if (p.isBraveWallet) return 'Brave';
      if (p.isMetaMask) return 'MetaMask';
      return 'Wallet';
    }

    function w3paint(){
      /* Reflect live detection state on the connect button. */
      try{
        var b = doc.getElementById('w3-connect-btn');
        if (!b || b.getAttribute('data-w3-on') === '1') return;
        var l = w3list();
        var lbl = b.querySelector('.w3-lbl');
        if (lbl){
          /* Only name a wallet when there is exactly one — otherwise the
             button would advertise whichever extension announced first
             (that is how "Connect Phantom" happened). */
          lbl.textContent = (l.length === 1 && l[0].name)
            ? ('Connect ' + l[0].name) : 'Connect Wallet';
        }
        b.title = l.length > 1
          ? ('Choose from ' + l.length + ' detected wallets')
          : (l.length === 1 ? ('Connect with ' + l[0].name) : 'Connect an EVM wallet');
      }catch(e){}
    }
    try{ window.__w3paint = w3paint; }catch(e){}

    function w3toast(msg, kind, ms){
      try{
        var t = doc.getElementById('w3-toast');
        if (!t){
          t = doc.createElement('div'); t.id = 'w3-toast'; t.className = 'w3-toast';
          doc.body.appendChild(t);
        }
        t.textContent = msg;
        t.className = 'w3-toast on' + (kind ? ' ' + kind : '');
        clearTimeout(t.__h);
        t.__h = setTimeout(function(){ t.className = 'w3-toast' + (kind ? ' ' + kind : ''); },
                           ms || 3200);
      }catch(e){}
    }
    try{ window.__w3toast = w3toast; }catch(e){}

    /* Push wallet state into Python via query params + rerun. */
    function w3report(addr, chain, label){
      try{
        var u = new URL(window.location.href);
        u.searchParams.set('w3_addr',  addr);
        u.searchParams.set('w3_chain', chain);
        u.searchParams.set('w3_label', label || 'Wallet');
        u.searchParams.delete('w3_act');
        window.history.replaceState({}, '', u.toString());
        window.location.reload();
      }catch(e){}
    }
    function w3reportDisconnect(){
      try{
        var u = new URL(window.location.href);
        u.searchParams.delete('w3_addr'); u.searchParams.delete('w3_chain');
        u.searchParams.delete('w3_label');
        u.searchParams.set('w3_act', 'disconnect');
        window.history.replaceState({}, '', u.toString());
        window.location.reload();
      }catch(e){}
    }

    function w3err(e, g){
      /* Human-readable messages for the standard EIP-1193 error codes.
         `g` is the wallet we were talking to, so the message can be
         specific rather than guessing at "wrong network". */
      var c = e && (e.code !== undefined ? e.code : (e.data && e.data.code));
      var nm = (g && g.name) ? g.name : 'wallet';
      if (c === 4001)  return 'Connection request rejected in ' + nm + '.';
      if (c === -32002) return 'A request is already pending — open ' + nm + ' and approve it.';
      if (c === 4900 || c === 4901) return nm + ' is disconnected.';
      if (c === -32602) return 'Invalid request parameters.';
      if (c === -32603){
        /* The exact case that produced the bogus "wrong network" toast. */
        if (g && g.solFirst){
          return nm + " couldn't complete an EVM request. Enable its EVM/Ethereum "
                 + 'support, or pick an EVM wallet like MetaMask, OKX or Rabby.';
        }
        return nm + ' returned an internal error. Unlock it and try again.';
      }
      return (e && e.message) ? String(e.message).slice(0, 140) : 'Wallet request failed.';
    }

    /* ── Wallet picker ──────────────────────────────────────
       Lists every installed wallet so the user chooses, instead of the
       app silently picking whichever extension announced first. */
    function w3closePicker(){
      try{
        var m = doc.getElementById('w3-modal');
        if (m){ m.classList.remove('on'); setTimeout(function(){ try{ m.remove(); }catch(e){} }, 180); }
      }catch(e){}
    }
    function w3openPicker(list){
      try{
        w3closePicker();
        var m = doc.createElement('div');
        m.id = 'w3-modal'; m.className = 'w3-modal';
        var rows = '';
        for (var i = 0; i < list.length; i++){
          var w = list[i];
          var ic = w.icon
            ? '<img class="w3-wi" src="' + w.icon + '" alt="" />'
            : '<span class="w3-wi w3-wi-ph">' + (w.name || '?').charAt(0).toUpperCase() + '</span>';
          rows +=
            '<button class="w3-wrow" data-w3-idx="' + i + '">' +
              ic +
              '<span class="w3-wn">' + (w.name || 'Wallet') + '</span>' +
              (w.solFirst ? '<span class="w3-wtag">Solana-first</span>' : '') +
            '</button>';
        }
        m.innerHTML =
          '<div class="w3-modal-bd"></div>' +
          '<div class="w3-modal-c" role="dialog" aria-label="Choose a wallet">' +
            '<div class="w3-modal-h">' +
              '<span>Choose a wallet</span>' +
              '<button class="w3-modal-x" aria-label="Close">✕</button>' +
            '</div>' +
            '<div class="w3-modal-l">' + rows + '</div>' +
            '<div class="w3-modal-f">Connecting shares only your public address. ' +
              'It never moves funds and never asks for your seed phrase.</div>' +
          '</div>';
        doc.body.appendChild(m);
        requestAnimationFrame(function(){ m.classList.add('on'); });
        m.querySelector('.w3-modal-bd').addEventListener('click', w3closePicker);
        m.querySelector('.w3-modal-x').addEventListener('click', w3closePicker);
        var btns = m.querySelectorAll('.w3-wrow');
        for (var k = 0; k < btns.length; k++){
          btns[k].addEventListener('click', function(ev){
            var idx = parseInt(ev.currentTarget.getAttribute('data-w3-idx'), 10);
            w3closePicker();
            w3do(list[idx]);
          });
        }
      }catch(e){}
    }

    var w3conn = null;   /* the wallet the user actually chose */
    var w3busy = false;
    async function w3connect(){
      if (w3busy) return;
      var list = w3list();
      if (!list.length){
        /* A wallet may still be announcing — grace period before we
           claim none exists. */
        w3scan();
        for (var i = 0; i < 6 && !w3has(); i++){
          await new Promise(function(r){ setTimeout(r, 120); });
          w3scan();
        }
        list = w3list();
      }
      if (!list.length){
        w3toast('No EVM wallet detected. Install MetaMask, OKX, Rabby or another EVM wallet, '
                + 'then reload this page.', 'err', 5600);
        return;
      }
      /* One wallet → connect it. Several → let the user choose. */
      if (list.length === 1) return w3do(list[0]);
      w3openPicker(list);
    }

    async function w3do(g){
      if (w3busy || !g || !g.p) return;
      w3busy = true;
      try{
        w3toast('Check your ' + (g.name || 'wallet') + ' to approve the connection…', null, 8000);
        var accts = await g.p.request({ method: 'eth_requestAccounts' });
        if (!accts || !accts.length){ w3toast('No accounts returned.', 'err'); w3busy = false; return; }
        var chain = await g.p.request({ method: 'eth_chainId' });
        w3conn = g;              /* Switch/disconnect must target THIS wallet */
        w3bind(g.p);
        w3report(accts[0], chain, g.name);
      }catch(e){
        w3toast(w3err(e, g), 'err', 6000);
        w3busy = false;
      }
    }

    async function w3switch(){
      var g = w3conn || w3get();
      if (!g || !g.p){ w3toast('No wallet detected.', 'err'); return; }
      try{
        await g.p.request({
          method: 'wallet_switchEthereumChain',
          params: [{ chainId: W3_CHAIN_HEX }]
        });
        w3toast('Switched to Pharos.', 'ok');
      }catch(e){
        /* 4902 = chain unknown to the wallet → offer to add it. */
        var c = e && (e.code !== undefined ? e.code : (e.data && e.data.code));
        if (c === 4902 || c === -32603){
          try{
            await g.p.request({
              method: 'wallet_addEthereumChain',
              params: [{
                chainId: W3_CHAIN_HEX,
                chainName: W3_CHAIN_NAME,
                nativeCurrency: { name: 'Pharos', symbol: W3_SYMBOL, decimals: 18 },
                rpcUrls: [W3_RPC],
                blockExplorerUrls: [W3_EXPLORER]
              }]
            });
            w3toast('Pharos network added.', 'ok');
          }catch(e2){ w3toast(w3err(e2), 'err'); return; }
        } else {
          w3toast(w3err(e), 'err'); return;
        }
      }
      try{
        var accts = await g.p.request({ method: 'eth_accounts' });
        var chain = await g.p.request({ method: 'eth_chainId' });
        if (accts && accts.length) w3report(accts[0], chain, g.name);
      }catch(e3){}
    }

    /* Live provider events — account switch, chain switch, disconnect. */
    var w3bound = false;
    function w3bind(p){
      if (w3bound || !p || !p.on) return;
      w3bound = true;
      try{
        p.on('accountsChanged', function(a){
          if (!a || !a.length){ w3reportDisconnect(); return; }
          p.request({ method: 'eth_chainId' }).then(function(c){
            w3report(a[0], c, w3name(p));
          }).catch(function(){});
        });
        p.on('chainChanged', function(c){
          p.request({ method: 'eth_accounts' }).then(function(a){
            if (a && a.length) w3report(a[0], c, w3name(p));
          }).catch(function(){});
        });
        p.on('disconnect', function(){ w3reportDisconnect(); });
      }catch(e){}
    }

    /* Silent re-attach on load: if the wallet is already authorised,
       restore state without prompting (eth_accounts never pops a modal).
       This is what makes the connection persist across reruns/reloads. */
    (function w3restore(){
      try{
        setTimeout(async function(){
          var g = w3get();
          if (!g || !g.p) return;
          w3bind(g.p);
          try{
            var accts = await g.p.request({ method: 'eth_accounts' });
            if (!accts || !accts.length) return;
            var chain = await g.p.request({ method: 'eth_chainId' });
            var u = new URL(window.location.href);
            var known = (u.searchParams.get('w3_addr') || '').toLowerCase();
            var pill  = doc.getElementById('w3-pill');
            var shown = pill && pill.classList.contains('w3-on');
            /* Only reload if Python does not already know this account. */
            if (!shown && known !== accts[0].toLowerCase()){
              w3report(accts[0], chain, g.name);
            }
          }catch(e){}
        }, 350);
      }catch(e){}
    })();

    /* Delegated clicks — survive Streamlit re-renders. */
    doc.addEventListener('click', function(e){
      if (!e.target || !e.target.closest) return;
      if (e.target.closest('#w3-connect-btn')){ e.preventDefault(); w3connect(); return; }
      if (e.target.closest('#w3-switch-btn')){ e.preventDefault(); w3switch(); return; }
      if (e.target.closest('#w3-disconnect-btn')){ e.preventDefault(); w3reportDisconnect(); return; }
    }, true);

    /* Send a real transaction from the connected wallet. Used by the
       Pay flow: Python renders a button carrying the tx params, the
       wallet signs, and the hash is handed back for receipt polling. */
    window.__w3send = async function(to, valueWei, chainHex){
      var g = w3get();
      if (!g || !g.p){ w3toast('No wallet detected.', 'err'); return; }
      try{
        var cur = await g.p.request({ method: 'eth_chainId' });
        if (chainHex && cur !== chainHex){
          w3toast('Switch to Pharos first.', 'err'); return;
        }
        var accts = await g.p.request({ method: 'eth_accounts' });
        if (!accts || !accts.length){ w3toast('Connect your wallet first.', 'err'); return; }
        w3toast('Confirm the transaction in your wallet…', null, 9000);
        var hash = await g.p.request({
          method: 'eth_sendTransaction',
          params: [{ from: accts[0], to: to, value: valueWei }]
        });
        w3toast('Transaction sent — tracking confirmation…', 'ok', 4000);
        try{
          var u = new URL(window.location.href);
          u.searchParams.set('tx_sent', hash);
          window.history.replaceState({}, '', u.toString());
          window.location.reload();
        }catch(e){}
      }catch(e){ w3toast(w3err(e), 'err'); }
    };

    /* ── COMMAND PALETTE (⌘K / Ctrl+K) ────────────────────
       Fuzzy search across pages, quick actions and docs topics.
       Built once, lives in the parent document, survives reruns. */
    var PALETTE = [
      {t:'Home',            s:'dashboard start command center', k:'home',      i:'🏠', g:'Page'},
      {t:'Chat with OctoBot', s:'ask ai assistant question help', k:'chat',   i:'💬', g:'Page'},
      {t:'Trade $PROS',     s:'buy sell exchange price cex',    k:'trade',     i:'📊', g:'Page'},
      {t:'Pay',             s:'send pros payment transfer x402', k:'pay',      i:'💸', g:'Page'},
      {t:'Request Payment', s:'invoice receive request pros',   k:'request',   i:'🧾', g:'Page'},
      {t:'SPNs',            s:'staking restaking native yield',  k:'spns',     i:'⚡', g:'Page'},
      {t:'Campaigns',       s:'quests rewards events active',    k:'campaigns', i:'🎯', g:'Page'},
      {t:'Updates',         s:'news announcements blog latest',  k:'updates',   i:'📰', g:'Page'},
      {t:'Ecosystem',       s:'dapps projects apps defi rwa',    k:'ecosystem', i:'🧩', g:'Page'},
      {t:'DeFi Hub',        s:'bridge liquidity staking lp positions wallet score rwa realfi explorer', k:'defi', i:'🏦', g:'Page'},
      {t:'Network',         s:'stats validators tps chain',      k:'network',   i:'🌐', g:'Page'},
      {t:'Market Pulse',    s:'sentiment community bullish bearish market', k:'pulse', i:'📡', g:'Page'},
      {t:'Memory Ledger',   s:'wallet on-chain intelligence profile', k:'memory', i:'🧠', g:'Page'},
      {t:'Toggle dark mode', s:'theme light dark night appearance', act:'theme', i:'🌓', g:'Action'},
      {t:'What is Pharos?',       s:'docs learn intro l1 blockchain', k:'chat', q:'What is Pharos?', i:'📖', g:'Docs'},
      {t:'What is the $PROS token?', s:'docs tokenomics utility', k:'chat', q:'What is the PROS token?', i:'📖', g:'Docs'},
      {t:'How do I build on Pharos?', s:'docs developer sdk build deploy', k:'chat', q:'How do I build on Pharos?', i:'📖', g:'Docs'},
      {t:'Explain Native Restaking', s:'docs spn restake security', k:'chat', q:'Explain Native Restaking on Pharos', i:'📖', g:'Docs'},
      {t:'What is RWA on Pharos?', s:'docs real world assets realfi', k:'chat', q:'What is RWA on Pharos?', i:'📖', g:'Docs'}
    ];

    function fuzzy(q, item){
      q = q.toLowerCase().trim();
      if (!q) return 1;
      var hay = (item.t + ' ' + item.s + ' ' + item.g).toLowerCase();
      var qi = 0, score = 0, streak = 0;
      for (var hi = 0; hi < hay.length && qi < q.length; hi++){
        if (hay[hi] === q[qi]){ qi++; streak++; score += streak; }
        else streak = 0;
      }
      if (qi < q.length) return 0;
      if (hay.indexOf(q) !== -1) score += 40;      /* substring bonus */
      if (item.t.toLowerCase().indexOf(q) === 0) score += 30; /* prefix on title */
      return score + 1;
    }

    var pal = null, palInput = null, palList = null, palSel = 0, palRows = [];
    function buildPalette(){
      if (pal) return;
      pal = doc.createElement('div');
      pal.id = 'octo-palette';
      pal.innerHTML =
        '<div class="op-backdrop"></div>' +
        '<div class="op-modal" role="dialog" aria-label="Command palette">' +
          '<div class="op-search">' +
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><line x1="21" y1="21" x2="16.5" y2="16.5"></line></svg>' +
            '<input id="op-input" placeholder="Search pages, actions, docs…" autocomplete="off" spellcheck="false"/>' +
            '<span class="op-esc">ESC</span>' +
          '</div>' +
          '<div class="op-list" id="op-list"></div>' +
          '<div class="op-foot"><span>↑↓ navigate</span><span>↵ open</span><span>⌘K toggle</span></div>' +
        '</div>';
      doc.body.appendChild(pal);
      palInput = pal.querySelector('#op-input');
      palList  = pal.querySelector('#op-list');
      pal.querySelector('.op-backdrop').addEventListener('click', closePalette);
      palInput.addEventListener('input', renderPalette);
      palInput.addEventListener('keydown', paletteKeys);
    }
    function runItem(it){
      closePalette();
      if (it.act === 'theme'){
        var cur = doc.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        switchTheme(cur === 'dark' ? 'light' : 'dark');
        return;
      }
      if (it.q){ try{ sessionStorage.setItem('octobot-prefill', it.q); }catch(e){} }
      if (it.k){ window.__pnavGo(it.k); }
    }
    function renderPalette(){
      var q = palInput ? palInput.value : '';
      var scored = [];
      for (var i = 0; i < PALETTE.length; i++){
        var sc = fuzzy(q, PALETTE[i]);
        if (sc > 0) scored.push([sc, PALETTE[i]]);
      }
      scored.sort(function(a,b){ return b[0] - a[0]; });
      palRows = scored.map(function(x){ return x[1]; }).slice(0, 8);
      palSel = 0;
      var html = '';
      if (!palRows.length){ html = '<div class="op-empty">No matches</div>'; }
      var lastG = '';
      for (var r = 0; r < palRows.length; r++){
        var it = palRows[r];
        if (it.g !== lastG){ html += '<div class="op-group">' + it.g + '</div>'; lastG = it.g; }
        html += '<div class="op-row' + (r === 0 ? ' on' : '') + '" data-idx="' + r + '">' +
                  '<span class="op-ico">' + it.i + '</span>' +
                  '<span class="op-title">' + it.t + '</span>' +
                  (it.g === 'Docs' ? '<span class="op-tag">ask</span>' : '') +
                '</div>';
      }
      palList.innerHTML = html;
      var rows = palList.querySelectorAll('.op-row');
      for (var j = 0; j < rows.length; j++){
        rows[j].addEventListener('mouseenter', function(){ setSel(+this.getAttribute('data-idx')); });
        rows[j].addEventListener('click', function(){ runItem(palRows[+this.getAttribute('data-idx')]); });
      }
    }
    function setSel(n){
      palSel = n;
      var rows = palList.querySelectorAll('.op-row');
      for (var i = 0; i < rows.length; i++) rows[i].classList.toggle('on', i === palSel);
      var cur = rows[palSel];
      if (cur && cur.scrollIntoView) cur.scrollIntoView({block:'nearest'});
    }
    function paletteKeys(e){
      if (e.key === 'ArrowDown'){ e.preventDefault(); if (palRows.length) setSel((palSel+1)%palRows.length); }
      else if (e.key === 'ArrowUp'){ e.preventDefault(); if (palRows.length) setSel((palSel-1+palRows.length)%palRows.length); }
      else if (e.key === 'Enter'){ e.preventDefault(); if (palRows[palSel]) runItem(palRows[palSel]); }
      else if (e.key === 'Escape'){ e.preventDefault(); closePalette(); }
    }
    function openPalette(){
      buildPalette();
      pal.classList.add('open');
      palInput.value = '';
      renderPalette();
      setTimeout(function(){ palInput.focus(); }, 30);
    }
    function closePalette(){ if (pal) pal.classList.remove('open'); }
    function togglePalette(){ if (pal && pal.classList.contains('open')) closePalette(); else openPalette(); }

    doc.addEventListener('keydown', function(e){
      if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')){
        e.preventDefault(); togglePalette();
      }
    }, true);
    doc.addEventListener('click', function(e){
      var sp = e.target && e.target.closest ? e.target.closest('#pnav-search-pill') : null;
      if (sp){ e.preventDefault(); openPalette(); }
    }, true);

    /* ── AMBIENT · glassy perspective grid room ──
       Four grid-lined walls (floor, ceiling, left, right) projected to a
       central vanishing point — a wireframe room seen head-on, like the
       reference. Very faint, glassy, almost transparent. Depth lines
       scroll toward the viewer so the room feels alive without being
       busy. Theme-aware, delta-time, pauses when hidden, vanishing point
       drifts gently. Zero per-frame allocations beyond the closing glow. */
    try{
      var host = doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;
      var cv = doc.createElement('canvas');
      cv.id = 'aura-3d-canvas';
      cv.setAttribute('aria-hidden', 'true');
      cv.style.cssText = 'position:fixed;inset:0;width:100%;height:100%;z-index:0;pointer-events:none;';
      host.appendChild(cv);
      var ctx = null;
      try{ ctx = cv.getContext('2d', {alpha:true, desynchronized:true}); }catch(e){}
      if (!ctx) ctx = cv.getContext('2d');
      var DPR = Math.min(window.devicePixelRatio || 1, 2);
      function fit(){
        cv.width  = (window.innerWidth  * DPR) | 0;
        cv.height = (window.innerHeight * DPR) | 0;
      }
      fit();
      window.addEventListener('resize', fit, {passive:true});

      function isDark(){ return doc.documentElement.getAttribute('data-theme') === 'dark'; }

      var t0 = 0, running = true;
      var CELLS = 12;     /* grid divisions along each wall edge */
      var DEPTH = 14;     /* number of scrolling depth lines      */

      /* click glows — a small pool of ripples, no per-frame allocation.
         Each glow carries its own colour so paintGlow is self-contained
         (no reliance on an outer rgbGlow), which is what lets the first
         frame paint synchronously on pointerdown for instant feedback. */
      function glowRGB(){ return isDark() ? '150,168,255' : '30,40,120'; }
      var glows = [
        {x:0,y:0,life:0,rgb:'30,40,120'},
        {x:0,y:0,life:0,rgb:'30,40,120'},
        {x:0,y:0,life:0,rgb:'30,40,120'},
        {x:0,y:0,life:0,rgb:'30,40,120'},
        {x:0,y:0,life:0,rgb:'30,40,120'},
        {x:0,y:0,life:0,rgb:'30,40,120'}
      ];
      var gi = 0;
      /* One click impact: a bright core that punches in, a soft bloom,
         and TWO concentric expanding rings offset in phase so the click
         reads as a quick wavy ripple pressed into the screen. e=life 1→0 */
      function paintGlow(gx, gy, e, rgb){
        var grow = 1 - e;
        var ease = 1 - Math.pow(e, 2.2);   /* fast-out radius easing */
        var R = 14 + ease * 190;           /* outer ripple radius    */

        var bloomR = 26 + grow * 90;
        var bg = ctx.createRadialGradient(gx, gy, 0, gx, gy, bloomR);
        bg.addColorStop(0,   'rgba(' + rgb + ',' + (0.34 * e) + ')');
        bg.addColorStop(0.5, 'rgba(' + rgb + ',' + (0.14 * e) + ')');
        bg.addColorStop(1,   'rgba(' + rgb + ',0)');
        ctx.fillStyle = bg;
        ctx.beginPath(); ctx.arc(gx, gy, bloomR, 0, Math.PI * 2); ctx.fill();

        if (e > 0.55){                      /* bright core snap */
          var core = (e - 0.55) / 0.45;
          ctx.beginPath();
          ctx.fillStyle = 'rgba(' + rgb + ',' + (0.42 * core) + ')';
          ctx.arc(gx, gy, 10 * core + 4, 0, Math.PI * 2); ctx.fill();
        }

        ctx.beginPath();                    /* ripple ring 1 (leading) */
        ctx.strokeStyle = 'rgba(' + rgb + ',' + (0.55 * e) + ')';
        ctx.lineWidth = 2.0 * e + 0.4;
        ctx.arc(gx, gy, R, 0, Math.PI * 2); ctx.stroke();

        ctx.beginPath();                    /* ripple ring 2 (trailing) */
        ctx.strokeStyle = 'rgba(' + rgb + ',' + (0.30 * e) + ')';
        ctx.lineWidth = 1.4 * e + 0.3;
        ctx.arc(gx, gy, R * 0.62, 0, Math.PI * 2); ctx.stroke();
      }
      /* pointerdown fires earlier than click → lower perceived latency;
         we paint the first frame synchronously so feedback is immediate. */
      function spawnGlow(cx, cy){
        var g = glows[gi]; gi = (gi + 1) % glows.length;
        g.x = cx; g.y = cy; g.life = 1; g.rgb = glowRGB();
        try{ paintGlow(g.x, g.y, 1, g.rgb); }catch(_){}   /* instant first frame */
        if (!running){ running = true; t0 = 0; requestAnimationFrame(tick); }
      }
      doc.addEventListener('pointerdown', function(e){
        if (e.isTrusted === false) return;
        spawnGlow(e.clientX, e.clientY);
      }, {passive:true, capture:true});
      /* Bridge for ripples triggered from inside Streamlit iframes. */
      try{ window.parent.__octoRipple = spawnGlow; }catch(_e){}
      window.__octoRipple = spawnGlow;

      doc.addEventListener('visibilitychange', function(){
        if (doc.hidden){ running = false; }
        else if (!running){ running = true; t0 = 0; requestAnimationFrame(tick); }
      });

      function tick(t){
        if (!running) return;
        if (!t0) t0 = t;
        var time = (t - t0) / 1000;
        var dt = Math.min(0.05, (t - (tick._prev || t)) / 1000 || 0.016);
        tick._prev = t;
        var W = window.innerWidth, H = window.innerHeight;
        ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
        ctx.clearRect(0, 0, W, H);
        if (!cv.isConnected){ host.appendChild(cv); }

        var dark = isDark();
        var rgb = dark ? '150,168,255' : '52,64,130';   /* darker light-mode lines */
        var rgbGlow = dark ? '150,168,255' : '30,40,120';
        /* glassy but clearly visible */
        var aLine = dark ? 0.13 : 0.16;

        /* vanishing point — near centre, drifting gently */
        var vx = W * 0.5 + Math.cos(time * 0.12) * W * 0.03;
        var vy = H * 0.5 + Math.sin(time * 0.10) * H * 0.03;

        ctx.lineWidth = 1;

        /* Each wall edge on the near (screen) plane is the full viewport
           rectangle; every point converges to (vx,vy). We draw:
             • perspective "depth" rectangles scrolling outward
             • straight grid rails from near-plane divisions to the VP */

        /* ── depth rectangles (scrolling toward viewer) ── */
        var speed = 0.22;
        var phase = (time * speed) % 1;
        for (var r = 0; r < DEPTH; r++){
          var depth = (r + phase) / DEPTH;      /* 0 far … 1 near */
          var d = Math.pow(depth, 1.9);          /* perspective spacing */
          if (d < 0.045) continue;               /* keep a clear open centre — no collapse to a point */
          var x0 = vx + (0     - vx) * d;
          var y0 = vy + (0     - vy) * d;
          var x1 = vx + (W     - vx) * d;
          var y1 = vy + (H     - vy) * d;
          ctx.beginPath();
          ctx.rect(x0, y0, x1 - x0, y1 - y0);
          ctx.strokeStyle = 'rgba(' + rgb + ',' + (aLine * (0.4 + 0.6 * depth)) + ')';
          ctx.stroke();
        }

        /* ── grid rails: each fades to transparent BEFORE reaching the
           centre, so there is no starburst convergence point — the lines
           read as a continuous flowing grid rather than emerging from a
           hole. `stop` = fraction of the way to the VP where the line
           ends; a per-rail gradient makes the fade smooth. ── */
        var stop = 0.82;   /* rails end 82% of the way in → open centre */
        function rail(sx, sy){
          var ex = sx + (vx - sx) * stop;
          var ey = sy + (vy - sy) * stop;
          var g = ctx.createLinearGradient(sx, sy, ex, ey);
          g.addColorStop(0,   'rgba(' + rgb + ',' + aLine + ')');
          g.addColorStop(0.7, 'rgba(' + rgb + ',' + (aLine * 0.6) + ')');
          g.addColorStop(1,   'rgba(' + rgb + ',0)');
          ctx.strokeStyle = g;
          ctx.beginPath(); ctx.moveTo(sx, sy); ctx.lineTo(ex, ey); ctx.stroke();
        }
        for (var c = 0; c <= CELLS; c++){
          var fx = (c / CELLS) * W;
          var fy = (c / CELLS) * H;
          rail(fx, 0);   /* ceiling */
          rail(fx, H);   /* floor   */
          rail(0,  fy);  /* left    */
          rail(W,  fy);  /* right   */
        }

        /* ── click glows: a soft expanding ring + warm bloom, sleek and
           quick, tinted to the grid colour ── */
        var anyGlow = false;
        for (var gk = 0; gk < glows.length; gk++){
          var gg = glows[gk];
          if (gg.life <= 0.001) continue;
          anyGlow = true;
          gg.life -= dt / 0.42;   /* full fade in ~0.42s — snappy & wavy */
          if (gg.life < 0) gg.life = 0;
          paintGlow(gg.x, gg.y, gg.life, gg.rgb);
        }
        requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    }catch(err){ /* ambient background is decorative — never break the app */ }
  }

  /* Inject once into the parent realm so it survives Streamlit reruns
     (same same-origin parent-document pattern used elsewhere in app). */
  try{
    var PW = window.parent;
    if (PW && !PW.__pnavBoot){
      var s = PW.document.createElement('script');
      s.id = 'pnav-aura-bootstrap';
      s.textContent = '(' + PNAV_PARENT_MAIN.toString() + ')();';
      PW.document.body.appendChild(s);
    }
  }catch(e){}
})();
</script>
    """,
    height=0,
    scrolling=False,
)


# ═════════════════════════════════════════════
# PAGE: HOME
# ═════════════════════════════════════════════
if st.session_state.page == "home":

    # ── Hero ──────────────────────────────────
    # ── Interactive logo (feature 3) ────────────
    render_interactive_logo(logo_b64)

    p = price_data
    if p.get("available") and p.get("price_usd"):
        chg    = p["change_24h"] or 0
        sym    = "▲" if chg >= 0 else "▼"
        cc     = "#1FA855" if chg >= 0 else "#E5484D"
        price_pill = (
            f'<span style="font-size:15px;color:#1A6AFF;font-family:Syne,sans-serif;font-weight:500;letter-spacing:0.04em;">$PROS&nbsp;</span>'
            f'<span class="hero-price-val" style="font-size:15px;font-weight:700;font-family:Syne,sans-serif;">${p["price_usd"]:.4f}</span>'
            f'<span style="font-size:15px;color:{cc};margin-left:4px;">{sym}{abs(chg):.2f}%</span>'
        )
    else:
        price_pill = '<span style="font-size:15px;color:#1A6AFF;font-family:Syne,sans-serif;font-weight:500;letter-spacing:0.04em;">$PROS&nbsp;</span>'

    st.markdown(
        '<div class="hero">'
        '<div class="hero-eyebrow"><div class="live-dot"></div>Live On Pharos Network </div>'
        '<h1 class="hero-title">Your <span>Pharos</span> Command Center</h1>'
        '<p class="hero-sub">Ask OctoBot anything about Pharos, track live $PROS price, explore active campaigns, read the latest updates, and trade — all in one place.</p>'
        '<div style="margin-bottom:1.2rem;">' + price_pill + '</div>'
        '<div class="hero-actions">'
        '<a class="hbtn hbtn-ghost" href="' + PHAROS_DISCORD_URL + '" target="_blank">Join the Pharos Discord for more updates and insights 🌊↗</a>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Feature badges — polished static display, not clickable buttons
    st.markdown(
        '<div style="display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-bottom:1.2rem;">'

        '<div style="display:inline-flex;align-items:center;gap:9px;'
        'background:#FFFFFF;border:1px solid rgba(0,0,0,0.09);'
        'border-radius:12px;padding:0.55rem 1.1rem;'
        'box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
        '<span style="font-size:16px;line-height:1;">💬</span>'
        '<div>'
        '<div style="font-family:Syne,sans-serif;font-size:12px;font-weight:700;color:#0C0C1A;line-height:1.2;">Multilingual</div>'
        '<div style="font-size:10px;color:#7A7F96;margin-top:1px;">Ask in any language</div>'
        '</div></div>'

        '<div style="display:inline-flex;align-items:center;gap:9px;'
        'background:#FFFFFF;border:1px solid rgba(0,0,0,0.09);'
        'border-radius:12px;padding:0.55rem 1.1rem;'
        'box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
        '<span style="font-size:16px;line-height:1;">🌐</span>'
        '<div>'
        '<div style="font-family:Syne,sans-serif;font-size:12px;font-weight:700;color:#0C0C1A;line-height:1.2;">50+ Languages</div>'
        '<div style="font-size:10px;color:#7A7F96;margin-top:1px;">Hindi, Arabic, Chinese & more</div>'
        '</div></div>'

        '<div style="display:inline-flex;align-items:center;gap:9px;'
        'background:#FFFFFF;border:1px solid rgba(0,0,0,0.09);'
        'border-radius:12px;padding:0.55rem 1.1rem;'
        'box-shadow:0 1px 4px rgba(0,0,0,0.06);">'
        '<span style="font-size:16px;line-height:1;">📊</span>'
        '<div>'
        '<div style="font-family:Syne,sans-serif;font-size:12px;font-weight:700;color:#0C0C1A;line-height:1.2;">Real-time Markets</div>'
        '<div style="font-size:10px;color:#7A7F96;margin-top:1px;">Live $PROS price & chart</div>'
        '</div></div>'

        '</div>',
        unsafe_allow_html=True,
    )

    # ── Memory Ledger + Payment Agent — elegant side-by-side cards ──
    home_card_col1, home_card_col2 = st.columns(2, gap="medium")

    with home_card_col1:
        # Memory Ledger card
        st.markdown(
            '<div style="background:linear-gradient(135deg,#0C0C1A 0%,#1414E8 100%);'
            'border-radius:20px;padding:1.6rem 1.6rem 1.2rem 1.6rem;'
            'box-shadow:0 8px 32px rgba(20,20,90,0.22);position:relative;overflow:hidden;'
            'min-height:170px;display:flex;flex-direction:column;justify-content:space-between;">'
            '<div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px;border-radius:50%;'
            'background:radial-gradient(circle,rgba(100,130,255,0.18) 0%,transparent 70%);pointer-events:none;"></div>'
            '<div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,0.04) 1px,transparent 1px);'
            'background-size:18px 18px;pointer-events:none;"></div>'
            '<div style="position:relative;z-index:1;">'
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.75rem;">'
            '<div style="width:42px;height:42px;border-radius:12px;background:rgba(255,255,255,0.1);'
            'display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;'
            'border:1px solid rgba(255,255,255,0.12);">🧠</div>'
            '<div>'
            '<div style="display:flex;align-items:center;gap:7px;">'
            '<span style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;color:#FFFFFF;">Memory Ledger</span>'
            '<span style="font-size:8.5px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;'
            'color:#9FB4FF;background:rgba(159,180,255,0.18);border-radius:8px;padding:2px 7px;border:1px solid rgba(159,180,255,0.25);">New</span>'
            '</div>'
            '<div style="font-size:11px;color:rgba(255,255,255,0.45);margin-top:1px;">On-chain wallet intelligence</div>'
            '</div></div>'
            '<div style="font-size:12.5px;color:rgba(255,255,255,0.62);line-height:1.6;margin-bottom:1rem;">'
            'Connect your wallet — OctoBot reads on-chain activity and personalises every answer.</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="connect-wallet-btn-wrap">', unsafe_allow_html=True)
        if st.button("🔗 View Wallet Profile →", key="home_memory_btn", use_container_width=True):
            st.session_state.page = "memory"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with home_card_col2:
        # Payment Agent card
        st.markdown(
            '<div style="background:linear-gradient(135deg,#0A2A0A 0%,#166016 100%);'
            'border-radius:20px;padding:1.6rem 1.6rem 1.2rem 1.6rem;'
            'box-shadow:0 8px 32px rgba(10,60,20,0.22);position:relative;overflow:hidden;'
            'min-height:170px;display:flex;flex-direction:column;justify-content:space-between;">'
            '<div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px;border-radius:50%;'
            'background:radial-gradient(circle,rgba(139,255,176,0.15) 0%,transparent 70%);pointer-events:none;"></div>'
            '<div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,0.04) 1px,transparent 1px);'
            'background-size:18px 18px;pointer-events:none;"></div>'
            '<div style="position:relative;z-index:1;">'
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.75rem;">'
            '<div style="width:42px;height:42px;border-radius:12px;background:rgba(255,255,255,0.1);'
            'display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0;'
            'border:1px solid rgba(255,255,255,0.12);">💸</div>'
            '<div>'
            '<div style="display:flex;align-items:center;gap:7px;">'
            '<span style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;color:#FFFFFF;">Payment Agent</span>'
            '<span style="font-size:8.5px;font-weight:700;letter-spacing:0.07em;text-transform:uppercase;'
            'color:#8BFFB0;background:rgba(139,255,176,0.18);border-radius:8px;padding:2px 7px;border:1px solid rgba(139,255,176,0.25);">Beta</span>'
            '</div>'
            '<div style="font-size:11px;color:rgba(255,255,255,0.45);margin-top:1px;">AI-powered PROS transfers</div>'
            '</div></div>'
            '<div style="font-size:12.5px;color:rgba(255,255,255,0.62);line-height:1.6;margin-bottom:1rem;">'
            'Send PROS with plain English — "Send 5 PROS to 0x1234…" and OctoBot handles the rest.</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div style="margin-top:0.6rem;"></div>', unsafe_allow_html=True)
        if st.button("💸 Open Payment Agent →", key="home_pay_btn", use_container_width=True):
            st.session_state.page = "pay"; st.rerun()

    st.markdown('<div style="margin-bottom:0.8rem;"></div>', unsafe_allow_html=True)

    # ── Docs badge banner ─────────────────────
    st.markdown(
        '<div class="docs-banner">'
        '<div class="docs-banner-left">'
        '<span class="docs-banner-icon">📄</span>'
        '<span class="docs-banner-text"><strong>Pharos Documentation</strong> — Full technical docs, API reference, guides, and tutorials</span>'
        '</div>'
        '<a class="docs-banner-link" href="' + PHAROS_DOCS_URL + '" target="_blank">Visit docs ↗</a>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Live price ticker ─────────────────────
    if p.get("available") and p.get("price_usd"):
        chg     = p["change_24h"] or 0
        chg_cls = "green" if chg >= 0 else "red"
        chg_sym = "▲" if chg >= 0 else "▼"
        mcap    = p.get("market_cap_usd")
        vol     = p.get("volume_24h")
        st.markdown(
            '<div class="price-ticker">'
            '<div class="ticker-cell"><div class="ticker-label">$PROS Price</div>'
            '<div class="ticker-value">$' + f'{p["price_usd"]:.4f}' + '</div></div>'
            '<div class="ticker-cell"><div class="ticker-label">24h Change</div>'
            '<div class="ticker-value ' + chg_cls + '">' + chg_sym + f'{abs(chg):.2f}%</div></div>'
            '<div class="ticker-cell"><div class="ticker-label">Market Cap</div>'
            '<div class="ticker-value">' + ("$" + f"{mcap:,.0f}" if mcap else "—") + '</div></div>'
            '<div class="ticker-cell"><div class="ticker-label">24h Volume</div>'
            '<div class="ticker-value">' + ("$" + f"{vol:,.0f}" if vol else "—") + '</div></div>'
            '</div>'
            '<div class="ticker-source">CoinGecko · Updated ' + (p.get("last_updated","—")) + '</div>',
            unsafe_allow_html=True,
        )

    # ── Chat showcase ──────────────────────────
    st.markdown(
        '<div class="chat-showcase">'
        '<div class="chat-showcase-header">'
        '<div>'
        '<div class="chat-showcase-title">🐙 OctoBot — Pharos AI Assistant</div>'
        '<div class="chat-showcase-sub">Answers from verified documentation · Zero hallucination</div>'
        '</div></div>'
        '<div class="chat-demo-msg">'
        '<div class="chat-demo-user"><div class="chat-demo-q">For Example : What are SPNs in Pharos?</div></div>'
        '</div>'
        '<div class="chat-demo-msg">'
        '<div class="chat-demo-bot"><div class="chat-demo-a">'
        'SPNs (Special Processing Networks) are specialized execution environments within Pharos '
        'that handle specific computation types — from DeFi calculations to compliance checks and '
        'AI inference. Each SPN runs in parallel, enabling Pharos to achieve 30,000+ TPS while '
        'remaining EVM compatible. Builders can deploy to specific SPNs based on their app\'s needs.'
        '</div></div>'
        '</div>'
        '<div style="padding:0.8rem 1rem;border-top:1px solid #E3E5EA;">'
        '<span style="font-size:11px;color:#9499A8;">Ask OctoBot anything about Pharos → </span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if st.button("Open Chat with OctoBot →", key="home_open_chat"):
        st.session_state.page = "chat"; st.rerun()

    # ── Active Campaigns mini preview ─────────
    st.markdown(
        '<div class="section-dark">'
        '<div style="position:relative;z-index:1;">'
        '<div class="section-eyebrow"><span class="drop">◆</span> LIVE</div>'
        '<h2 class="section-h">Active Campaigns</h2>'
        '<p class="section-sub">Real-time opportunities in the Pharos ecosystem.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )
    home_camp_html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:0.8rem;">'
    for c in CAMPAIGNS[:2]:
        home_camp_html += (
            f'<div style="background:#FFFFFF;border:1px solid #E3E5EA;border-radius:12px;'
            f'padding:1rem 1.1rem;display:flex;align-items:flex-start;justify-content:space-between;gap:10px;'
            f'box-shadow:0 1px 3px rgba(20,20,60,0.04);transition:transform 180ms cubic-bezier(0.34,1.4,0.64,1),box-shadow 180ms ease;">'
            f'<div style="flex:1;min-width:0;">'
            f'<div class="camp-tag" style="margin-bottom:5px;">{c["tag"]}</div>'
            f'<div class="camp-title" style="margin-bottom:4px;">{c["title"]}</div>'
            f'<div class="camp-desc" style="margin-bottom:6px;">{c["desc"]}</div>'
            f'<a class="camp-link" href="{c["link"]}" target="_blank">{c["cta"]} ↗</a>'
            f'</div>'
            f'<div style="width:44px;height:44px;border-radius:12px;flex-shrink:0;'
            f'background:{c["bg"]};display:flex;align-items:center;justify-content:center;'
            f'font-size:22px;line-height:1;">{c["icon"]}</div>'
            f'</div>'
        )
    home_camp_html += '</div>'
    st.markdown(home_camp_html, unsafe_allow_html=True)
    if st.button("View all campaigns →", key="home_all_camp"):
        st.session_state.page = "campaigns"; st.rerun()

    # ── Stats strip ───────────────────────────────────────────────
    st.markdown(
        '<div class="home-stat-strip">'
        '<div class="home-stat-item"><div class="home-stat-num">30K+</div><div class="home-stat-lbl">TPS Capacity</div></div>'
        '<div class="home-stat-item"><div class="home-stat-num">$44M</div><div class="home-stat-lbl">Series A Raised</div></div>'
        '<div class="home-stat-item"><div class="home-stat-num">14+</div><div class="home-stat-lbl">Ecosystem DApps</div></div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Animated features marquee (centered, replaces 3-card grid) ─
    MARQUEE_ITEMS = [
        ("🤖", "RAG-Powered AI",      "Zero hallucination"),
        ("🌐", "50+ Languages",       "Ask in any language"),
        ("📊", "Live Market Data",    "Real-time $PROS price"),
        ("⚡", "30,000+ TPS",         "Fastest EVM L1"),
        ("🔐", "Built-in Compliance", "zk-KYC & SPNs"),
        ("🏦", "RWA Native",          "Tokenized real assets"),
        ("🛠", "EVM Compatible",      "Deploy existing contracts"),
        ("🐙", "OctoBot AI Hub",      "Your Pharos assistant"),
    ]
    # Duplicate items so seamless infinite loop works
    def _mk_item(icon, title, sub):
        return (
            f'<div class="marquee-item">'
            f'<span class="marquee-icon">{icon}</span>'
            f'<span class="marquee-label">{title}</span>'
            f'<span class="marquee-sub">{sub}</span>'
            f'</div>'
        )
    items_html = "".join([_mk_item(i,t,s) for i,t,s in MARQUEE_ITEMS])
    # Duplicate for seamless loop
    items_html = items_html + items_html
    st.markdown(
        '<div style="text-align:center;margin:0 0 0.4rem 0;">'
        '<span style="font-size:10px;font-weight:600;letter-spacing:0.1em;'
        'text-transform:uppercase;color:#9499A8;">What OctoBot can do</span>'
        '</div>'
        '<div class="marquee-wrap">'
        '<div class="marquee-track">' + items_html + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Build Path Generator (feature 2 — home entry point) ───────
    st.markdown(
        '<div style="background:#FFFFFF;border:1px solid #E3E5EA;border-radius:14px;'
        'padding:1.1rem 1.3rem;margin-bottom:0.8rem;box-shadow:0 1px 4px rgba(20,20,60,0.04);">'
        '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;color:#0C0C1A;margin-bottom:0.3rem;">'
        '🛠 Build on Pharos</div>'
        '<div style="font-size:12px;color:#7A7F96;margin-bottom:0.8rem;">'
        'Get a personalised roadmap — choose your goal and OctoBot builds your path.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    bp1, bp2, bp3, bp4 = st.columns(4)
    for col, goal in zip([bp1,bp2,bp3,bp4], ["Agent","dApp","Learning","Infrastructure"]):
        icons = {"Agent":"🤖","dApp":"🏗","Learning":"📚","Infrastructure":"⚙️"}
        with col:
            if st.button(icons[goal] + " " + goal, key="bp_home_" + goal, use_container_width=True):
                st.session_state.build_path_goal = goal
                st.session_state.build_path_data = None
                st.session_state.page = "chat"
                st.session_state["pending_q"] = f"Build path for {goal} on Pharos"
                st.rerun()


# ═════════════════════════════════════════════
# PAGE: MEMORY LEDGER — On-chain wallet intelligence
# ═════════════════════════════════════════════
elif st.session_state.page == "memory":

    # ── Premium header — bold brain-aura "neural" theme ─────────────────
    components.html(
        """
        <style>
        body{margin:0;padding:0;background:transparent;font-family:'DM Sans',sans-serif;overflow:hidden;}
        .ml-wrap{display:flex;flex-direction:column;align-items:center;text-align:center;padding-top:10px;width:100%;position:relative;}

        .ml-badge{
            display:inline-flex;align-items:center;gap:7px;
            font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
            color:#FFFFFF;background:linear-gradient(90deg,#0C0C1A,#1414E8);
            border:none;border-radius:30px;padding:7px 18px;margin-bottom:22px;
            box-shadow:0 6px 18px rgba(20,20,90,0.3);
            animation:ml-fadein 0.5s cubic-bezier(0.16,1,0.3,1) both;
        }
        .ml-badge .dot{
            width:6px;height:6px;border-radius:50%;background:#3CFF9E;
            box-shadow:0 0 8px #3CFF9E;animation:ml-blink 2s ease-in-out infinite;
        }
        @keyframes ml-blink{0%,100%{opacity:1}50%{opacity:0.25}}

        /* ── Bold neural brain core with layered aura ──
           Reduced from 4 orbiting sparks to 3, and slowed the pulse/
           orbit cycles slightly — same layered "alive" feel, fewer
           simultaneous animations recalculating every frame on this
           one small area. */
        .ml-brain-wrap{
            position:relative;width:50px;height:50px;
            display:flex;align-items:center;justify-content:center;
            margin-bottom:14px;
            animation:ml-fadein 0.6s cubic-bezier(0.16,1,0.3,1) 0.1s both;
            will-change:auto;
        }
        .ml-aura{
            position:absolute;inset:0;border-radius:50%;
            background:radial-gradient(circle, rgba(26,26,255,0.38) 0%, rgba(26,26,255,0.12) 60%, transparent 20%);
            animation:ml-pulse 3.8s ease-in-out infinite;
            will-change:transform;
        }
        .ml-aura.a2{
            inset:-24px;
            background:radial-gradient(circle, rgba(107,140,255,0.24) 0%, transparent 40%);
            animation:ml-pulse 3.8s ease-in-out infinite 0.5s;
            will-change:transform;
        }
        .ml-aura.a3{
            inset:-46px;
            background:radial-gradient(circle, rgba(20,20,232,0.12) 0%, transparent 48%);
            animation:ml-pulse 5s ease-in-out infinite 1s;
            will-change:transform;
        }
        @keyframes ml-pulse{
            0%,100%{ transform:scale(0.9); opacity:0.65; }
            50%{ transform:scale(1.12); opacity:1; }
        }
       @keyframes node-pulse{
            0%,100%{ opacity:0.4; }
            50%{ opacity:1; }
        }
        @keyframes node-pulse-slow{
            0%,100%{ opacity:0.3; }
            50%{ opacity:0.9; }
        }
        @keyframes brain-float{
            0%,100%{ transform:translateY(0); }
            50%{ transform:translateY(-6px); }
        }
        @keyframes data-flicker{
            0%,100%{ opacity:0.18; }
            50%{ opacity:0.38; }
        }
        .brain-svg-wrap{
            animation:brain-float 5s ease-in-out infinite;
            will-change:transform;
        }
        .node-glow{ animation:node-pulse 3s ease-in-out infinite; }
        .node-glow2{ animation:node-pulse 3s ease-in-out infinite 1s; }
        .node-glow3{ animation:node-pulse-slow 4s ease-in-out infinite 0.5s; }
        .data-text{ animation:data-flicker 4s ease-in-out infinite; }
        .data-text2{ animation:data-flicker 4s ease-in-out infinite 1.4s; }
        .data-text3{ animation:data-flicker 4s ease-in-out infinite 2.2s; }

        .ml-title{
            font-family:'Space Grotesk',sans-serif;font-size:2rem;font-weight:600;
            color:#0C0C1A;letter-spacing:-0.02em;margin-bottom:12px;line-height:1.1;
            animation:ml-fadein 0.6s cubic-bezier(0.16,1,0.3,1) 0.18s both;
        }
        .ml-title span{
            background:linear-gradient(90deg,#1414E8,#6B6BFF,#1414E8);
            background-size:200% auto;
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;
            animation:ml-shimmer 5s linear infinite;
            will-change:background-position;
        }
        /* Note: text-clip gradients cannot use transform (it would move
           the text itself, not just the gradient fill), so this one
           keeps background-position but is slowed from 4s to 5s and
           marked will-change so the browser keeps it on its own paint
           layer — this is a small, narrow text element, not a
           full-viewport layer, so the cost here is minimal even with
           background-position; the real wins were the large layers
           (wave/dots) fixed earlier. */
        @keyframes ml-shimmer{ to{ background-position:200% center; } }
        .ml-sub{
            font-size:14.5px;color:#5B5F6E;max-width:520px;line-height:1.7;font-weight:400;
            animation:ml-fadein 0.6s cubic-bezier(0.16,1,0.3,1) 0.26s both;
            padding-bottom:10px;
        }
        @keyframes ml-fadein{
            from{ opacity:0; transform:translateY(16px); }
            to{ opacity:1; transform:translateY(0); }
        }
        /* Dark-mode overrides — this header lives in its own iframe and
           cannot inherit the parent <html data-theme>, so we mirror the
           theme onto this iframe's own <html> (see script below) and
           re-skin the hard-coded light inks. */
        html[data-theme="dark"] .ml-title{ color:#EDEFF7; }
        html[data-theme="dark"] .ml-sub{ color:#AEB4C8; }
        html[data-theme="dark"] .ml-badge{
            background:linear-gradient(90deg,#1B1F2E,#2A2AF0);
            box-shadow:0 6px 18px rgba(0,0,0,0.4);
        }
        </style>
        <script>
        /* Mirror the parent app's theme onto this iframe so the header
           text stays readable in dark mode. Reads the same localStorage
           key the nav toggle writes, and also polls the parent <html>
           so it updates live when the user flips the switch. */
        (function(){
          function parentTheme(){
            try{
              var pt = window.parent.document.documentElement.getAttribute('data-theme');
              if(pt) return pt;
            }catch(e){}
            try{ return localStorage.getItem('octobot-theme') || 'light'; }catch(e){}
            return 'light';
          }
          function apply(){
            var mode = parentTheme() === 'dark' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', mode);
          }
          apply();
          setInterval(apply, 400);
        })();
        </script>

        <div class="ml-wrap">
         <div class="ml-brain-wrap" style="width:180px;height:200px;cursor:pointer;position:relative;" id="octo-mem" onclick="octoSquish()">
            <div style="position:absolute;inset:-16px;border-radius:50%;border:1.5px solid rgba(96,165,250,0.30);animation:ml-spin 20s linear infinite;pointer-events:none;top:10px;"></div>
            <div style="position:absolute;inset:-6px;border-radius:50%;border:1px dashed rgba(129,140,248,0.22);animation:ml-spin 32s linear infinite reverse;pointer-events:none;top:10px;"></div>
            <div style="position:absolute;width:6px;height:6px;border-radius:50%;background:#60A5FA;box-shadow:0 0 10px rgba(96,165,250,0.9);top:0px;left:45%;animation:node-pulse 2.2s ease-in-out infinite;pointer-events:none;"></div>
            <div style="position:absolute;width:4px;height:4px;border-radius:50%;background:#818CF8;box-shadow:0 0 8px rgba(129,140,248,0.9);top:18%;right:-8px;animation:node-pulse 2.8s ease-in-out infinite 0.7s;pointer-events:none;"></div>
            <div style="position:absolute;width:4px;height:4px;border-radius:50%;background:#38BDF8;box-shadow:0 0 8px rgba(56,189,248,0.9);top:18%;left:-8px;animation:node-pulse 3s ease-in-out infinite 1.3s;pointer-events:none;"></div>
            <div style="position:absolute;width:5px;height:5px;border-radius:50%;background:#6B8FFF;box-shadow:0 0 8px rgba(107,143,255,0.8);bottom:30px;right:-4px;animation:node-pulse 2.5s ease-in-out infinite 0.4s;pointer-events:none;"></div>
            <div id="octo-mem-inner" style="filter:drop-shadow(0 0 18px rgba(59,130,246,0.60)) drop-shadow(0 0 44px rgba(26,26,255,0.32));animation:ml-float 4s ease-in-out infinite;will-change:transform;">
              <svg id="octo-svg" width="180" height="200" viewBox="0 0 180 200" xmlns="http://www.w3.org/2000/svg" style="transform-origin:center bottom;overflow:visible;">
                <defs>
                  <radialGradient id="cg-body" cx="36%" cy="28%" r="70%">
                    <stop offset="0%" stop-color="#7EB5FF"/>
                    <stop offset="40%" stop-color="#2563EB"/>
                    <stop offset="100%" stop-color="#0F1F8A"/>
                  </radialGradient>
                  <radialGradient id="cg-head" cx="36%" cy="26%" r="68%">
                    <stop offset="0%" stop-color="#93C5FD"/>
                    <stop offset="38%" stop-color="#3B82F6"/>
                    <stop offset="100%" stop-color="#1E3A8A"/>
                  </radialGradient>
                  <radialGradient id="cg-shine" cx="32%" cy="22%" r="50%">
                    <stop offset="0%" stop-color="white" stop-opacity="0.55"/>
                    <stop offset="60%" stop-color="white" stop-opacity="0.08"/>
                    <stop offset="100%" stop-color="white" stop-opacity="0"/>
                  </radialGradient>
                  <radialGradient id="cg-iris" cx="38%" cy="32%" r="65%">
                    <stop offset="0%" stop-color="#BFDBFE"/>
                    <stop offset="30%" stop-color="#2563EB"/>
                    <stop offset="100%" stop-color="#0C1660"/>
                  </radialGradient>
                  <linearGradient id="cg-tent" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" stop-color="#3B82F6"/>
                    <stop offset="100%" stop-color="#1E3A8A"/>
                  </linearGradient>
                  <filter id="cg-rim" x="-15%" y="-15%" width="130%" height="130%">
                    <feGaussianBlur in="SourceAlpha" stdDeviation="3.5" result="b"/>
                    <feFlood flood-color="#60A5FA" flood-opacity="0.55" result="c"/>
                    <feComposite in="c" in2="b" operator="in" result="g"/>
                    <feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge>
                  </filter>
                </defs>
                <path d="M54,150 C42,156 32,162 30,172 C29,178 33,180 36,176 C38,171 36,165 42,160" stroke="url(#cg-tent)" stroke-width="11" fill="none" stroke-linecap="round"/>
                <path d="M54,150 C42,156 32,162 30,172 C29,178 33,180 36,176 C38,171 36,165 42,160" stroke="#5BA5FF" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.4"/>
                <circle cx="33" cy="176" r="5" fill="#60A5FA" style="animation:node-pulse 2.2s ease-in-out infinite;"/>
                <path d="M66,158 C58,168 54,176 56,184 C57,189 53,191 51,187 C49,182 53,174 55,168" stroke="url(#cg-tent)" stroke-width="11" fill="none" stroke-linecap="round"/>
                <path d="M66,158 C58,168 54,176 56,184 C57,189 53,191 51,187 C49,182 53,174 55,168" stroke="#5BA5FF" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.4"/>
                <circle cx="51" cy="188" r="5" fill="#818CF8" style="animation:node-pulse 2.6s ease-in-out infinite 0.4s;"/>
                <path d="M79,163 C76,174 74,182 76,190 C77,195 74,197 72,193 C70,188 73,180 75,173" stroke="url(#cg-tent)" stroke-width="11" fill="none" stroke-linecap="round"/>
                <path d="M79,163 C76,174 74,182 76,190 C77,195 74,197 72,193 C70,188 73,180 75,173" stroke="#5BA5FF" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.4"/>
                <circle cx="72" cy="194" r="5" fill="#38BDF8" style="animation:node-pulse 2s ease-in-out infinite 0.8s;"/>
                <path d="M101,163 C104,174 106,182 104,190 C103,195 106,197 108,193 C110,188 107,180 105,173" stroke="url(#cg-tent)" stroke-width="11" fill="none" stroke-linecap="round"/>
                <path d="M101,163 C104,174 106,182 104,190 C103,195 106,197 108,193 C110,188 107,180 105,173" stroke="#5BA5FF" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.4"/>
                <circle cx="108" cy="194" r="5" fill="#38BDF8" style="animation:node-pulse 2s ease-in-out infinite 1s;"/>
                <path d="M114,158 C122,168 126,176 124,184 C123,189 127,191 129,187 C131,182 127,174 125,168" stroke="url(#cg-tent)" stroke-width="11" fill="none" stroke-linecap="round"/>
                <path d="M114,158 C122,168 126,176 124,184 C123,189 127,191 129,187 C131,182 127,174 125,168" stroke="#5BA5FF" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.4"/>
                <circle cx="129" cy="188" r="5" fill="#818CF8" style="animation:node-pulse 2.6s ease-in-out infinite 0.6s;"/>
                <path d="M126,150 C138,156 148,162 150,172 C151,178 147,180 144,176 C142,171 144,165 138,160" stroke="url(#cg-tent)" stroke-width="11" fill="none" stroke-linecap="round"/>
                <path d="M126,150 C138,156 148,162 150,172 C151,178 147,180 144,176 C142,171 144,165 138,160" stroke="#5BA5FF" stroke-width="4" fill="none" stroke-linecap="round" opacity="0.4"/>
                <circle cx="147" cy="176" r="5" fill="#60A5FA" style="animation:node-pulse 2.2s ease-in-out infinite 0.3s;"/>
                <path d="M44,130 C30,122 20,112 22,100 C24,92 32,90 36,96" stroke="url(#cg-tent)" stroke-width="9" fill="none" stroke-linecap="round"/>
                <circle cx="23" cy="100" r="4" fill="#60A5FA" opacity="0.7" style="animation:node-pulse 2.8s ease-in-out infinite 1.1s;"/>
                <path d="M136,130 C150,122 160,112 158,100 C156,92 148,90 144,96" stroke="url(#cg-tent)" stroke-width="9" fill="none" stroke-linecap="round"/>
                <circle cx="157" cy="100" r="4" fill="#60A5FA" opacity="0.7" style="animation:node-pulse 2.8s ease-in-out infinite 0.5s;"/>
                <ellipse cx="90" cy="148" rx="36" ry="28" fill="url(#cg-body)" filter="url(#cg-rim)"/>
                <ellipse cx="90" cy="162" rx="30" ry="12" fill="#0F1F8A" opacity="0.35"/>
                <ellipse cx="78" cy="136" rx="14" ry="9" fill="white" opacity="0.16"/>
                <circle cx="90" cy="88" r="68" fill="url(#cg-head)" filter="url(#cg-rim)"/>
                <ellipse cx="90" cy="148" rx="50" ry="18" fill="#1E3A8A" opacity="0.28"/>
                <circle cx="90" cy="88" r="68" fill="url(#cg-shine)"/>
                <ellipse cx="62" cy="55" rx="16" ry="10" fill="white" opacity="0.20" transform="rotate(-20,62,55)"/>
                <ellipse class="expr-eye-l" cx="68" cy="88" rx="20" ry="22" fill="white"/>
                <ellipse class="expr-eye-r" cx="112" cy="88" rx="20" ry="22" fill="white"/>
                <circle cx="68" cy="90" r="14" fill="url(#cg-iris)"/>
                <circle cx="112" cy="90" r="14" fill="url(#cg-iris)"/>
                <circle class="expr-pupil-l" cx="70" cy="92" r="8" fill="#060820"/>
                <circle class="expr-pupil-r" cx="114" cy="92" r="8" fill="#060820"/>
                <circle cx="76" cy="82" r="5" fill="white" opacity="0.96"/>
                <circle cx="120" cy="82" r="5" fill="white" opacity="0.96"/>
                <circle cx="63" cy="90" r="2.2" fill="white" opacity="0.70"/>
                <circle cx="107" cy="90" r="2.2" fill="white" opacity="0.70"/>
                <circle cx="78" cy="86" r="1.4" fill="white" opacity="0.55"/>
                <circle cx="122" cy="86" r="1.4" fill="white" opacity="0.55"/>
                <circle cx="68" cy="90" r="14" fill="none" stroke="#BFDBFE" stroke-width="1.2" opacity="0.55"/>
                <circle cx="112" cy="90" r="14" fill="none" stroke="#BFDBFE" stroke-width="1.2" opacity="0.55"/>
                <ellipse cx="68" cy="88" rx="20" ry="22" fill="none" stroke="#1E3A8A" stroke-width="1.2" opacity="0.25"/>
                <ellipse cx="112" cy="88" rx="20" ry="22" fill="none" stroke="#1E3A8A" stroke-width="1.2" opacity="0.25"/>
                <path d="M50,104 Q68,114 86,104" fill="none" stroke="#1E3A8A" stroke-width="1" opacity="0.2" stroke-linecap="round"/>
                <path d="M94,104 Q112,114 130,104" fill="none" stroke="#1E3A8A" stroke-width="1" opacity="0.2" stroke-linecap="round"/>
                <ellipse class="expr-blush-l" cx="44" cy="106" rx="14" ry="8" fill="#F472B6" opacity="0.22"/>
                <ellipse class="expr-blush-r" cx="136" cy="106" rx="14" ry="8" fill="#F472B6" opacity="0.22"/>
                <path class="expr-mouth" d="M74,116 Q90,128 106,116" fill="none" stroke="#BFDBFE" stroke-width="2.8" stroke-linecap="round"/>
                <path d="M78,118 Q90,126 102,118" fill="white" opacity="0.80"/>
                <g font-family="monospace" font-size="6" fill="#93C5FD" opacity="0.30">
                  <text x="12" y="72" style="animation:data-flicker 3.2s ease-in-out infinite;">01</text>
                  <text x="154" y="80" style="animation:data-flicker 3.2s ease-in-out infinite 1.1s;">10</text>
                  <text x="18" y="108" style="animation:data-flicker 3.2s ease-in-out infinite 2s;">11</text>
                  <text x="148" y="112" style="animation:data-flicker 3.2s ease-in-out infinite 0.6s;">00</text>
                </g>
                <circle cx="90" cy="88" r="68" fill="none" stroke="#60A5FA" stroke-width="1.8" opacity="0.20"/>
              </svg>
            </div>
          </div>
          <style>
          @keyframes octo-squish{
            0%  { transform:scale(1,1); }
            20% { transform:scale(1.22,0.80); }
            50% { transform:scale(0.88,1.18); }
            75% { transform:scale(1.06,0.96); }
            100%{ transform:scale(1,1); }
          }
          @keyframes ml-spin{
            from{ transform:rotate(0deg); }
            to{ transform:rotate(360deg); }
          }
          #octo-mem{ user-select:none; }
          .expr-eye-l,.expr-eye-r,.expr-pupil-l,.expr-pupil-r,
          .expr-mouth,.expr-blush-l,.expr-blush-r{
            transition:all 0.22s cubic-bezier(0.4,0,0.2,1);
          }
          </style>
          <script>
          (function(){
            var exprTimeout = null;
            function setExpression(expr){
              var svg = document.getElementById('octo-svg');
              if(!svg) return;
              svg.setAttribute('data-expr', expr);
              if(expr !== 'idle'){
                clearTimeout(exprTimeout);
                exprTimeout = setTimeout(function(){ setExpression('idle'); }, 3200);
              }
            }
            function octoSquish(){
              var svg = document.getElementById('octo-svg');
              if(!svg) return;
              setExpression('excited');
              svg.style.animation = 'none';
              void svg.offsetWidth;
              svg.style.animation = 'octo-squish 0.55s cubic-bezier(0.34,1.4,0.64,1) forwards';
              setTimeout(function(){ svg.style.animation = ''; }, 580);
            }
            window.octoSquish  = octoSquish;
            window.octoSetExpr = setExpression;
          })();
          </script>
          <div class="ml-title">OctoBot <span>Memory Ledger</span></div>
          <div class="ml-sub">
            A Pharos-native AI companion that knows you before you speak.
          </div>
        </div>
        """,
        height=380,
    )

    # ── Side-by-side layout: Wallet entry (left) + Transaction Explainer (right) ──
    mem_col_left, mem_col_right = st.columns(2, gap="large")

    with mem_col_left:
        if not st.session_state.wallet_address:
            # ── Manual address entry — only connection method ──────────────
            st.markdown('<div style="margin-top:-0.8rem;"></div>', unsafe_allow_html=True)

            # ── Rotating advisory ticker strip ────────────────────────────
            st.markdown(
                '<style>'
                '@keyframes ml-ticker-scroll{0%{transform:translateX(0);}100%{transform:translateX(-50%);}}'
                '.ml-ticker-wrap{overflow:hidden;background:linear-gradient(90deg,#F0FFF4,#E8F5FF);'
                'border:1px solid #86EFAC;border-radius:12px;padding:0;margin-bottom:0.9rem;position:relative;}'
                '.ml-ticker-wrap::before,.ml-ticker-wrap::after{content:"";position:absolute;top:0;bottom:0;'
                'width:40px;z-index:2;pointer-events:none;}'
                '.ml-ticker-wrap::before{left:0;background:linear-gradient(90deg,#F0FFF4,transparent);}'
                '.ml-ticker-wrap::after{right:0;background:linear-gradient(270deg,#F0FFF4,transparent);}'
                '.ml-ticker-track{display:flex;align-items:center;width:max-content;'
                'animation:ml-ticker-scroll 22s linear infinite;padding:9px 0;}'
                '.ml-ticker-track:hover{animation-play-state:paused;}'
                '.ml-ticker-item{display:inline-flex;align-items:center;gap:6px;padding:0 1.6rem;'
                'white-space:nowrap;border-right:1px solid #86EFAC;font-size:12px;font-weight:600;color:#15803D;}'
                '.ml-ticker-item:last-child{border-right:none;}'
                '.ml-ticker-dot{width:6px;height:6px;border-radius:50%;background:#22C55E;flex-shrink:0;}'
                '</style>'
                '<div class="ml-ticker-wrap"><div class="ml-ticker-track">'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>🔒 No signing required</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>⛽ Zero gas used</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>👁 Read-only access</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>🔌 No wallet extension needed</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>📋 Just paste your address</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>🛡 Your funds are never touched</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>🔒 No signing required</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>⛽ Zero gas used</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>👁 Read-only access</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>🔌 No wallet extension needed</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>📋 Just paste your address</div>'
                '<div class="ml-ticker-item"><span class="ml-ticker-dot"></span>🛡 Your funds are never touched</div>'
                '</div></div>',
                unsafe_allow_html=True,
            )

            st.markdown(
                '<div style="display:flex;justify-content:center;">'
                '<div style="background:#FFFFFF;border:1.5px solid rgba(26,26,255,0.2);border-radius:18px;'
                'padding:1.5rem 1.7rem;'
                'box-shadow:0 6px 20px rgba(20,20,60,0.07),0 0 0 4px rgba(26,26,255,0.06),0 0 28px rgba(56,189,248,0.12),0 0 56px rgba(26,26,255,0.08);'
                'max-width:560px;width:100%;min-height:188px;display:flex;flex-direction:column;">'
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                '<div style="width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#1414E8,#0C0C1A);'
                'display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">🔑</div>'
                '<span style="font-family:Syne,sans-serif;font-size:15px;font-weight:700;color:#0C0C1A;">'
                'Enter your Pharos wallet address</span>'
                '</div>'
                '<div style="font-size:13px;color:#000000;margin-bottom:14px;line-height:1.55;min-height:36px;">'
                'Paste any Pharos wallet address to view its on-chain profile — '
                'read-only, zero risk, nothing to install.</div>',
                unsafe_allow_html=True,
            )
            manual_addr = st.text_input(
                "Wallet address", placeholder="0x1234...your Pharos wallet address",
                key="manual_wallet_input", label_visibility="collapsed",
            )
            if st.button("🔎  View Profile", key="manual_wallet_btn", use_container_width=True):
                if valid_addr(manual_addr):
                    st.session_state.wallet_address = manual_addr.strip()
                    st.session_state.wallet_data    = None
                    st.session_state.wallet_profile = None
                    st.rerun()
                else:
                    st.error("Enter a valid 0x... wallet address (42 characters).")
            st.markdown('</div></div>', unsafe_allow_html=True)

        else:
            # ── Connected — fetch and show profile ────────────────────────
            addr = st.session_state.wallet_address
            short_addr = addr[:6] + "…" + addr[-4:]

            top1, top2 = st.columns([3, 1])
            with top1:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:12px;'
                    f'background:linear-gradient(90deg,#0C0C1A,#1414E8);'
                    f'border-radius:16px;padding:1rem 1.3rem;margin-bottom:1.1rem;'
                    f'box-shadow:0 8px 24px rgba(20,20,90,0.22);">'
                    f'<div style="width:38px;height:38px;border-radius:10px;'
                    f'background:rgba(255,255,255,0.12);display:flex;align-items:center;'
                    f'justify-content:center;font-size:18px;flex-shrink:0;">🔗</div>'
                    f'<div><div style="font-size:10px;color:rgba(255,255,255,0.55);font-weight:700;'
                    f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:2px;">Connected Wallet</div>'
                    f'<div style="font-size:15px;color:#fff;font-weight:700;font-family:monospace;letter-spacing:0.01em;">{esc(short_addr)}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with top2:
                if st.button("✕ Disconnect", key="disconnect_wallet", use_container_width=True):
                    st.session_state.wallet_address  = ""
                    st.session_state.wallet_data     = None
                    st.session_state.wallet_profile  = None
                    st.rerun()

            # Fetch on-chain data once
            if st.session_state.wallet_data is None:
                with st.spinner("Reading on-chain activity from Pharos…"):
                    st.session_state.wallet_data = fetch_pharos_onchain_data(addr)

            data = st.session_state.wallet_data

            if not data.get("available"):
                st.warning(
                    "⚠️ Could not reach Pharos RPC right now — this wallet may be new, "
                    "or the network is temporarily unavailable. Your address was still read "
                    "successfully — no funds or gas were used."
                )

            # On-chain stats row — bold cards with glow accent on hover
            bal      = data.get("balance_pros")
            tx_count = data.get("tx_count")
            st.markdown(
                '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:1.2rem;">'
                f'<div style="background:#FFFFFF;border:1.5px solid #E3E5EA;border-radius:16px;padding:1.1rem 1rem;'
                f'text-align:center;box-shadow:0 4px 14px rgba(20,20,60,0.05);">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;color:#9499A8;margin-bottom:6px;">💰 PROS Balance</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:19px;font-weight:800;color:#1414E8;">'
                f'{f"{bal:.4f}" if bal is not None else "—"}</div></div>'
                f'<div style="background:#FFFFFF;border:1.5px solid #E3E5EA;border-radius:16px;padding:1.1rem 1rem;'
                f'text-align:center;box-shadow:0 4px 14px rgba(20,20,60,0.05);">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;color:#9499A8;margin-bottom:6px;">⚡ Transactions</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:19px;font-weight:800;color:#1414E8;">'
                f'{tx_count if tx_count is not None else "—"}</div></div>'
                f'<div style="background:#FFFFFF;border:1.5px solid #E3E5EA;border-radius:16px;padding:1.1rem 1rem;'
                f'text-align:center;box-shadow:0 4px 14px rgba(20,20,60,0.05);">'
                f'<div style="font-size:9px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;color:#9499A8;margin-bottom:6px;">🏷 Address Type</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:19px;font-weight:800;color:#1414E8;">'
                f'{"Contract" if data.get("is_contract") else "Wallet"}</div></div>'
                '</div>',
                unsafe_allow_html=True,
            )

            # Synthesize profile via Gemini (once)
            if st.session_state.wallet_profile is None:
                with st.spinner("OctoBot is synthesising your intelligence profile…"):
                    st.session_state.wallet_profile = synthesize_wallet_profile(data)

            profile = st.session_state.wallet_profile

            tags_html = "".join([
                f'<span class="tag" style="margin-right:6px;margin-bottom:6px;display:inline-block;'
                f'font-weight:700;">{esc(t)}</span>'
                for t in profile.get("tags", [])
            ])
            st.markdown(
                '<div style="background:linear-gradient(160deg,#F0F1FF 0%,#E4E8FF 100%);'
                'border:1.5px solid rgba(26,26,255,0.18);border-radius:20px;padding:1.6rem 1.7rem;'
                'margin-bottom:1.1rem;box-shadow:0 12px 36px rgba(20,20,90,0.1);position:relative;overflow:hidden;">'
                '<div style="position:absolute;top:-40px;right:-40px;width:140px;height:140px;border-radius:50%;'
                'background:radial-gradient(circle, rgba(26,26,255,0.15) 0%, transparent 70%);pointer-events:none;"></div>'
                '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.9rem;position:relative;z-index:1;">'
                '<div style="width:36px;height:36px;border-radius:50%;'
                'background:linear-gradient(135deg,#1414E8,#0C0C1A);display:flex;align-items:center;'
                'justify-content:center;font-size:18px;flex-shrink:0;'
                'box-shadow:0 4px 12px rgba(20,20,90,0.3);">🐙</div>'
                '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;color:#0C0C1A;">'
                'OctoBot says:</div></div>'
                f'<div style="font-size:14.5px;color:#0C0C1A;line-height:1.7;font-style:italic;margin-bottom:1.1rem;position:relative;z-index:1;">'
                f'"{esc(profile.get("summary", ""))}"</div>'
                f'<div style="margin-bottom:0.9rem;position:relative;z-index:1;">{tags_html}'
                f'<span class="tag" style="background:rgba(31,168,85,0.12);border-color:rgba(31,168,85,0.35);'
                f'color:#1FA855;display:inline-block;font-weight:700;">Risk: {esc(profile.get("risk", "Unknown"))}</span></div>'
                f'<div style="font-size:13px;color:#42475A;background:rgba(255,255,255,0.7);'
                f'border-radius:12px;padding:0.8rem 1rem;position:relative;z-index:1;">'
                f'💡 <strong>Suggested next step:</strong> {esc(profile.get("insight", ""))}</div>'
                '</div>',
                unsafe_allow_html=True,
            )

            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("💬 Ask OctoBot about my profile", key="memory_to_chat", use_container_width=True):
                    bal_display = f"{bal:.4f}" if bal is not None else "0"
                    st.session_state["pending_q"] = (
                        f"Based on my wallet with {tx_count or 0} transactions and "
                        f"{bal_display} PROS balance, what should I do next on Pharos?"
                    )
                    # Wallet-derived questions aren't in the docs — switch to
                    # Docs + General mode so OctoBot can actually answer them
                    # via the Gemini fallback instead of saying "not found".
                    st.session_state.chat_mode = "general"
                    st.session_state.page = "chat"
                    st.rerun()
            with col_b:
                st.link_button(
                    "🔍 View on Pharos Explorer",
                    PHAROS_EXPLORER_URL + "/address/" + addr,
                    use_container_width=True,
                )

            st.markdown(
                '<div style="font-size:10.5px;color:#B0B4C4;text-align:center;margin-top:1rem;">'
                'Profile generated from public on-chain data only · No funds accessed · '
                'Disconnect anytime above</div>',
                unsafe_allow_html=True,
            )

    with mem_col_right:
        # ── Transaction Explainer ───────────────────────────────────────
        # Shows regardless of wallet-connect state above — works as a
        # standalone read-only tool. Reuses the exact same RPC pattern and
        # safety guarantees as the wallet profile feature: no signature,
        # no transaction sent, no funds touched, only public on-chain data.
        #
        # Mirrors the left wallet card's exact structure (badges row,
        # then a white card that stays open through the Streamlit input
        # and button, closed afterward) so both cards share identical
        # heading markup, spacing, and overall card height.
        st.markdown('<div style="margin-top:1.9rem;"></div>', unsafe_allow_html=True)
        st.markdown(
            '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:0.1rem;justify-content:center;">'
            '<div style="font-size:11.5px;font-weight:600;color:#42475A;background:#FFFFFF;border:1px solid #E3E5EA;'
            'border-radius:20px;padding:7px 15px;box-shadow:0 2px 8px rgba(20,20,60,0.05);">'
            '⛓️ Reads any public transaction</div>'
            '<div style="font-size:11.5px;font-weight:600;color:#42475A;background:#FFFFFF;border:1px solid #E3E5EA;'
            'border-radius:20px;padding:7px 15px;box-shadow:0 2px 8px rgba(20,20,60,0.05);">'
            '⚡ Instant on-chain lookup</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        st.markdown(
            '<div style="display:flex;justify-content:center;">'
            '<div style="background:#FFFFFF;border:1.5px solid rgba(26,26,255,0.2);border-radius:18px;'
            'padding:1.5rem 1.7rem;'
            'box-shadow:0 6px 20px rgba(20,20,60,0.07),0 0 0 4px rgba(26,26,255,0.06),0 0 28px rgba(56,189,248,0.12),0 0 56px rgba(26,26,255,0.08);'
            'max-width:560px;width:100%;min-height:188px;display:flex;flex-direction:column;">'
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
            '<div style="width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#1414E8,#0C0C1A);'
            'display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">🔎</div>'
            '<span style="font-family:Syne,sans-serif;font-size:15px;font-weight:700;color:#0C0C1A;">'
            'Transaction Explainer</span>'
            '</div>'
            '<div style="font-size:13px;color:#000000;margin-bottom:14px;line-height:1.55;min-height:36px;">'
            'Paste any Pharos transaction hash — OctoBot reads it on-chain and explains it in plain language.</div>',
            unsafe_allow_html=True,
        )
        tx_input = st.text_input(
            "Transaction hash", placeholder="0x...transaction hash from pharosscan.xyz",
            key="tx_hash_field", label_visibility="collapsed",
        )
        if st.button("🧠  Explain this transaction", key="explain_tx_btn", use_container_width=True):
            cleaned = tx_input.strip()
            if valid_txhash(cleaned):
                st.session_state.tx_hash_input  = cleaned
                st.session_state.tx_data        = None
                st.session_state.tx_explanation = None
                st.rerun()
            else:
                st.error("Enter a valid 0x... transaction hash (66 characters).")
        st.markdown('</div></div>', unsafe_allow_html=True)

        if st.session_state.tx_hash_input:
            tx_h = st.session_state.tx_hash_input

            if st.session_state.tx_data is None:
                with st.spinner("Reading transaction from Pharos…"):
                    st.session_state.tx_data = fetch_pharos_transaction(tx_h)

            tx_data = st.session_state.tx_data

            if tx_data.get("error") and not tx_data.get("from_addr"):
                st.warning("⚠️ " + str(tx_data.get("error", "Could not read this transaction.")))
            else:
                short_hash = tx_h[:10] + "…" + tx_h[-6:]
                status     = tx_data.get("status")
                status_color = (
                    "#1FA855" if status == "success" else
                    "#E5484D" if status == "failed" else
                    "#9499A8"
                )
                status_label = (
                    "✓ Success" if status == "success" else
                    "✕ Failed"  if status == "failed"  else
                    "⏳ Pending"
                )

                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:12px;'
                    f'background:linear-gradient(90deg,#0C0C1A,#1414E8);'
                    f'border-radius:16px;padding:1rem 1.3rem;margin-top:1rem;margin-bottom:1.1rem;'
                    f'box-shadow:0 8px 24px rgba(20,20,90,0.22);">'
                    f'<div style="width:38px;height:38px;border-radius:10px;'
                    f'background:rgba(255,255,255,0.12);display:flex;align-items:center;'
                    f'justify-content:center;font-size:18px;flex-shrink:0;">🧾</div>'
                    f'<div><div style="font-size:10px;color:rgba(255,255,255,0.55);font-weight:700;'
                    f'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:2px;">Transaction</div>'
                    f'<div style="font-size:14px;color:#fff;font-weight:700;font-family:monospace;'
                    f'letter-spacing:0.01em;">{short_hash}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

                # On-chain stats row — same card style as wallet profile stats
                value_pros = tx_data.get("value_pros")
                gas_used   = tx_data.get("gas_used")
                st.markdown(
                    '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:1.1rem;">'
                    f'<div style="background:#FFFFFF;border:1.5px solid #E3E5EA;border-radius:16px;padding:1.1rem 1rem;'
                    f'text-align:center;box-shadow:0 4px 14px rgba(20,20,60,0.05);">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;color:#9499A8;margin-bottom:6px;">📌 Status</div>'
                    f'<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;color:{status_color};">'
                    f'{status_label}</div></div>'
                    f'<div style="background:#FFFFFF;border:1.5px solid #E3E5EA;border-radius:16px;padding:1.1rem 1rem;'
                    f'text-align:center;box-shadow:0 4px 14px rgba(20,20,60,0.05);">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;color:#9499A8;margin-bottom:6px;">💰 Value</div>'
                    f'<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;color:#1414E8;">'
                    f'{f"{value_pros:.4f}" if value_pros is not None else "—"}</div></div>'
                    f'<div style="background:#FFFFFF;border:1.5px solid #E3E5EA;border-radius:16px;padding:1.1rem 1rem;'
                    f'text-align:center;box-shadow:0 4px 14px rgba(20,20,60,0.05);">'
                    f'<div style="font-size:9px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;color:#9499A8;margin-bottom:6px;">⚡ Gas Used</div>'
                    f'<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;color:#1414E8;">'
                    f'{f"{gas_used:,}" if gas_used is not None else "—"}</div></div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                # Plain-language explanation via Gemini (with deterministic fallback)
                if st.session_state.tx_explanation is None:
                    with st.spinner("OctoBot is explaining this transaction…"):
                        st.session_state.tx_explanation = explain_transaction(tx_data)

                explanation = st.session_state.tx_explanation
                steps_html = "".join([
                    f'<div style="display:flex;align-items:flex-start;gap:8px;padding:0.4rem 0;'
                    f'border-bottom:1px solid rgba(255,255,255,0.5);font-size:12px;color:#42475A;">'
                    f'<span style="color:#1A1AFF;flex-shrink:0;">→</span><span>{esc(s)}</span></div>'
                    for s in explanation.get("plain_steps", [])
                ])
                st.markdown(
                    '<div style="background:linear-gradient(160deg,#F0F1FF 0%,#E4E8FF 100%);'
                    'border:1.5px solid rgba(26,26,255,0.18);border-radius:20px;padding:1.4rem 1.5rem;'
                    'margin-bottom:1rem;box-shadow:0 12px 36px rgba(20,20,90,0.1);position:relative;overflow:hidden;">'
                    '<div style="position:absolute;top:-40px;right:-40px;width:140px;height:140px;border-radius:50%;'
                    'background:radial-gradient(circle, rgba(26,26,255,0.15) 0%, transparent 70%);pointer-events:none;"></div>'
                    '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.9rem;position:relative;z-index:1;">'
                    '<div style="width:36px;height:36px;border-radius:50%;'
                    'background:linear-gradient(135deg,#1414E8,#0C0C1A);display:flex;align-items:center;'
                    'justify-content:center;font-size:18px;flex-shrink:0;'
                    'box-shadow:0 4px 12px rgba(20,20,90,0.3);">🐙</div>'
                    '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;color:#0C0C1A;">'
                    'OctoBot explains:</div></div>'
                    f'<div style="font-size:14px;color:#0C0C1A;line-height:1.65;font-style:italic;margin-bottom:0.9rem;position:relative;z-index:1;">'
                    f'"{esc(explanation.get("summary", ""))}"</div>'
                    f'<span class="tag" style="display:inline-block;margin-bottom:0.9rem;position:relative;z-index:1;">'
                    f'{esc(explanation.get("category", "Transaction"))}</span>'
                    f'<div style="position:relative;z-index:1;">{steps_html}</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )

                col_tx1, col_tx2 = st.columns(2)
                with col_tx1:
                    if st.button("✕ Clear", key="clear_tx", use_container_width=True):
                        st.session_state.tx_hash_input  = ""
                        st.session_state.tx_data        = None
                        st.session_state.tx_explanation = None
                        st.rerun()
                with col_tx2:
                    st.link_button(
                        "🔍 View on Pharos Explorer",
                        PHAROS_EXPLORER_URL + "/tx/" + tx_h,
                        use_container_width=True,
                    )

                st.markdown(
                    '<div style="font-size:10.5px;color:#B0B4C4;text-align:center;margin-top:1rem;">'
                    'Explanation generated from public on-chain data only · Read-only · No funds accessed</div>',
                    unsafe_allow_html=True,
                )

    

# ═════════════════════════════════════════════
# PAGE: CHAT
# ═════════════════════════════════════════════
elif st.session_state.page == "chat":

    # ── Loading screen ─────────────────────────
    _lp = st.empty()
    _ll = ('<img src="' + logo_b64 + '" />' if logo_b64 else '<span class="fi">🐙</span>')
    with _lp.container():
        st.markdown(
            '<div class="octo-loading">'
            '<div class="octo-loading-wrap">'
            '<div class="octo-lr r1"></div><div class="octo-lr r2"></div><div class="octo-lr r3"></div>'
            + _ll +
            '</div>'
            '<div class="octo-loading-title">Loading OctoBot</div>'
            '<div class="octo-loading-sub">Connecting to knowledge base…</div>'
            '<div class="octo-loading-dots"><span></span><span></span><span></span></div>'
            '</div>',
            unsafe_allow_html=True,
        )

    # Wait on the init worker instead of spin-rerunning the whole app.
    # Common case: OctoBot is ready within this wait and the chat renders
    # on the FIRST run — no rerun, no flash, no wasted CPU. Slow case: we
    # rerun at most once every few seconds, so the init thread actually
    # gets the CPU it needs. The hard timeout inside load_octobot() still
    # guarantees this state always terminates.
    _octo = octobot_wait(8.0)

    if not _octo["done"]:
        st.rerun()

    _lp.empty()

    if _octo.get("error") or _octo.get("bot") is None:
        _err = esc(_octo.get("error") or "Unknown initialisation error")
        st.markdown(
            '<div style="max-width:560px;margin:3rem auto;background:#FFFFFF;'
            'border:1px solid #F3C7C7;border-radius:18px;padding:1.6rem 1.8rem;'
            'box-shadow:0 2px 12px rgba(20,20,60,0.06);">'
            '<div style="font-size:26px;margin-bottom:0.4rem;">⚠️</div>'
            '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;'
            'color:#14141F;margin-bottom:0.35rem;">Knowledge base failed to load</div>'
            '<div style="font-size:12.5px;color:#5B5F6E;line-height:1.55;">' + _err + '</div>'
            '<div style="font-size:11.5px;color:#9499A8;margin-top:0.6rem;">'
            'If this is the first run, build the index with '
            '<code>python build_vectorstore.py</code>, then retry.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        _c1, _c2 = st.columns([1, 3])
        with _c1:
            if st.button("↺ Retry loading", key="octo_retry"):
                _octobot_reset()
                st.rerun()
        st.stop()

    bot = _octo["bot"]

    # ── Settings moved to sidebar — just get chunk count here ──
    chunk_count = _octo.get("chunk_count")
    if chunk_count is None:
        try:
            chunk_count = bot.vectorstore._collection.count()
        except Exception:
            chunk_count = 0

    # ── Sidebar — price + controls + examples ──────────────────
    with st.sidebar:

        # Live $PROS price card
        p = price_data
        # OctoBot branding — text only, no image dependency
        st.markdown(
            '<div style="display:flex;align-items:center;gap:8px;padding:0.3rem 0 0.8rem 0;'
            'border-bottom:1px solid #D0D3E0;margin-bottom:0.8rem;">'
            '<span style="font-size:20px;">🐙</span>'
            '<div>'
            '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#0C0C1A;">OctoBot</div>'
            '<div style="font-size:10px;color:#7A7F96;letter-spacing:0.05em;">Pharos AI Hub</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

           
        # New conversation
        st.markdown(
            '<div style="font-size:10px;font-weight:700;color:#0C0C1A;'
            'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:5px;">Conversation</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
        if st.button("↺  New Conversation", use_container_width=True, key="reset_chat"):
            st.session_state.messages        = []
            st.session_state.sources_history = []
            bot.reset_memory()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<hr style="border:none;border-top:1px solid #D0D3E0;margin:0.7rem 0;">', unsafe_allow_html=True)

        # Settings toggles
        st.markdown(
            '<div style="font-size:10px;font-weight:700;color:#0C0C1A;'
            'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">Settings</div>',
            unsafe_allow_html=True,
        )
        st.session_state.show_sources = st.toggle("🔍 Show sources", value=st.session_state.show_sources)
        st.session_state.voice_reply  = st.toggle("🗣 Read aloud",   value=st.session_state.voice_reply)

        st.markdown('<hr style="border:none;border-top:2px solid #D0D3E0;margin:0.7rem 0;">', unsafe_allow_html=True)

        # Build Path Generator entry
        st.markdown(
            '<div style="font-size:12px;font-weight:800;color:#0C0C1A;'
            'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:5px;">🛠 Build Path (General Mode Exclusive)</div>',
            unsafe_allow_html=True,
        )
        for goal, icon in [("Agent","🤖"),("dApp","🏗"),("Learning","📚"),("Infrastructure","⚙️")]:
            if st.button(icon + " " + goal, key="bp_sb_" + goal, use_container_width=True):
                st.session_state.build_path_goal = goal
                st.session_state.build_path_data = None
                st.session_state["pending_q"]    = f"How do I start building a {goal} on Pharos?"
                st.rerun()

        st.markdown('<hr style="border:none;border-top:1px solid #D0D3E0;margin:0.7rem 0;">', unsafe_allow_html=True)

        # Example prompts
        st.markdown(
            '<div style="font-size:12px;font-weight:800;color:#0C0C1A;'
            'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">Example Prompts</div>',
            unsafe_allow_html=True,
        )
        for q in ["What is Pharos?","What is the PROS token?", "How do I build on Pharos?", "What is RWA?"]:
            if st.button(q, key="sb_" + q, use_container_width=True):
                st.session_state["pending_q"] = q
                st.rerun()

    # ── Top spacer: guarantees the first row clears the fixed nav on the
    #    chat page regardless of sidebar layout timing / CSS cascade ──
    st.markdown('<div class="chat-top-spacer" style="height:0px;"></div>', unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════
    #  CHAT CONTROL DECK  —  rebuilt from scratch
    #  One cohesive glass card, compact and left-anchored, holding the
    #  language selector, answer-mode segmented control, and the x402
    #  premium row. Display markup is inside a single .cdeck card; the
    #  functional Streamlit widgets (buttons/toggle/input) are styled to
    #  sit flush inside it. Fully theme-aware.
    # ══════════════════════════════════════════════════════════
    st.markdown('<div class="cdeck-anchor"></div>', unsafe_allow_html=True)
    st.markdown(
        """
<style>
.cdeck-anchor{height:0;margin:0;padding:0;}

/* ── The control deck card ─────────────────────────────────── */
[data-testid="stMainBlockContainer"]:has(.cdeck-anchor) .cdeck{
    max-width:600px;margin:0 0 0.9rem 0;
    background:linear-gradient(180deg,rgba(255,255,255,0.96),rgba(247,248,252,0.96));
    border:1px solid #E1E4EE;border-radius:16px;
    box-shadow:0 4px 20px rgba(20,20,60,0.06);
    padding:1rem 1.1rem 0.5rem;
    backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
}
.cdeck-hd{display:flex;align-items:center;gap:8px;margin-bottom:0.85rem;}
.cdeck-hd .dot{width:7px;height:7px;border-radius:50%;background:#1FA855;box-shadow:0 0 6px #1FA855;}
.cdeck-hd .ttl{font-family:'Syne',sans-serif;font-size:13px;font-weight:800;color:#0C0C1A;letter-spacing:-0.01em;}
.cdeck-hd .sub{font-size:10.5px;font-weight:600;color:#9AA0AE;margin-left:auto;white-space:nowrap;}
.cdeck-sec{font-size:9.5px;font-weight:800;letter-spacing:0.1em;text-transform:uppercase;
    color:#5B6178;margin:0.35rem 0 6px 1px;display:flex;align-items:center;gap:5px;}

/* ── Language flag buttons ─────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.st-key-lang_English){
    max-width:600px;margin:0 0 0.9rem 0 !important;gap:5px !important;
}
[data-testid="stHorizontalBlock"]:has(.st-key-lang_English) [data-testid="stColumn"]{padding:0 !important;}
[data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button{
    min-height:38px !important;height:38px !important;padding:0 !important;
    font-size:12px !important;font-weight:700 !important;line-height:1.1 !important;border-radius:9px !important;
    color:#2A3050 !important;
    background:#FFFFFF !important;border:1px solid #E1E4EE !important;
    transition:transform 140ms ease,border-color 140ms ease,box-shadow 140ms ease !important;
}
[data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button p,
[data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button div{
    color:#2A3050 !important;
}
[data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button:hover{
    transform:translateY(-1px) !important;border-color:#B9C0FF !important;
    box-shadow:0 4px 12px rgba(26,26,255,0.12) !important;
}

/* ── Mode segmented control ────────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.st-key-mode_docs){
    max-width:600px;margin:0 0 0.9rem 0 !important;gap:6px !important;
}
[data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button{
    min-height:38px !important;font-size:12.5px !important;font-weight:600 !important;
    border-radius:10px !important;background:#FFFFFF !important;border:1px solid #E1E4EE !important;color:#2A3050 !important;
    transition:transform 140ms ease,border-color 140ms ease,box-shadow 140ms ease !important;
}
[data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button p,
[data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button div{ color:#2A3050 !important; }
[data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button:hover{
    transform:translateY(-1px) !important;border-color:#B9C0FF !important;
    box-shadow:0 4px 12px rgba(26,26,255,0.12) !important;
}

/* ── x402 toggle + wallet row ──────────────────────────────── */
[data-testid="stHorizontalBlock"]:has(.st-key-x402_enabled_toggle_main){
    max-width:600px;margin:0 0 0.3rem 0 !important;align-items:center !important;
}

/* ══ DARK MODE ══ */
html[data-theme="dark"] [data-testid="stMainBlockContainer"]:has(.cdeck-anchor) .cdeck{
    background:#141722;border-color:#262B3E;box-shadow:0 4px 20px rgba(0,0,0,0.45);
}
html[data-theme="dark"] .cdeck-hd .ttl{color:#EDEFF7;}
html[data-theme="dark"] .cdeck-hd .sub{color:#7B8199;}
html[data-theme="dark"] .cdeck-sec{color:#7B8199;}
html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button,
html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button{
    background:#181C2A !important;border-color:#2A3044 !important;color:#C4C9DC !important;
}
html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button p,
html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button div,
html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button p,
html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button div{ color:#C4C9DC !important; }
html[data-theme="dark"] .cdeck-sec{color:#8891A8 !important;}
/* Extra dark-mode contrast safety net */
html[data-theme="dark"] [style*="color:#3A4055"],
html[data-theme="dark"] [style*="color:#2A3050"],
html[data-theme="dark"] [style*="color:#3A4050"],
html[data-theme="dark"] [style*="color:#2A3040"]{ color:#DDE0EE !important; }
html[data-theme="dark"] [style*="color:#8A90A6"],
html[data-theme="dark"] [style*="color:#8891A8"]{ color:#AEB4C8 !important; }
/* Toggle & radio tracks readable on dark */
html[data-theme="dark"] [data-baseweb="checkbox"] div[role="checkbox"]{border-color:#3A4260 !important;}
html[data-theme="dark"] [data-testid="stChatInput"] textarea{color:#EDEFF7 !important;}
html[data-theme="dark"] [data-testid="stChatInput"] textarea::placeholder{color:#7B8199 !important;}
/* Dropdown menus / popovers / tooltips (render at <body> root) */
html[data-theme="dark"] [data-baseweb="popover"] [role="listbox"],
html[data-theme="dark"] [data-baseweb="menu"],
html[data-theme="dark"] ul[role="listbox"]{
    background:#161A28 !important;border:1px solid #2A3044 !important;
}
html[data-theme="dark"] [data-baseweb="popover"] li,
html[data-theme="dark"] [role="option"]{ color:#DDE0EE !important;background:transparent !important; }
html[data-theme="dark"] [role="option"]:hover,
html[data-theme="dark"] [aria-selected="true"][role="option"]{ background:rgba(90,110,255,0.14) !important; }
html[data-theme="dark"] [data-baseweb="tooltip"]{ background:#1B1F2E !important;color:#EDEFF7 !important;border:1px solid #2A3044 !important; }
/* Selectbox / text-input display value */
html[data-theme="dark"] [data-baseweb="select"] *{ color:#DDE0EE !important; }
html[data-theme="dark"] [data-baseweb="input"],
html[data-theme="dark"] [data-baseweb="base-input"]{ background:#12151F !important; }


/* ══ DARK MODE · comprehensive inline light-surface coverage ══
   These pages (Campaigns, Updates, Ecosystem, Network, Memory Ledger,
   Pay, Request) render cards with inline light backgrounds + light
   gradient icon headers. In dark mode those stayed light while their
   text flipped light → invisible. Re-skin every light inline surface. */
html[data-theme="dark"] [style*="background:#F9F9FC"],
html[data-theme="dark"] [style*="background:#F4F5FF"],
html[data-theme="dark"] [style*="background:#EEF0FF"],
html[data-theme="dark"] [style*="background:#F2F3F8"],
html[data-theme="dark"] [style*="background:#F4F5F8"],
html[data-theme="dark"] [style*="background:#F4F4F6"],
html[data-theme="dark"] [style*="background:#ECEEF4"],
html[data-theme="dark"] [style*="background:#E3E5EA"],
html[data-theme="dark"] [style*="background:#F4F5F9"],
html[data-theme="dark"] [style*="background:#EAEEFF"],
html[data-theme="dark"] [style*="background:#FAFBFF"],
html[data-theme="dark"] [style*="background:#F9FAFC"],
html[data-theme="dark"] [style*="background:#F8FAFF"],
html[data-theme="dark"] [style*="background:#F8F9FF"],
html[data-theme="dark"] [style*="background:#F7F8FA"],
html[data-theme="dark"] [style*="background:#F6F8FF"],
html[data-theme="dark"] [style*="background:#F5F6FA"],
html[data-theme="dark"] [style*="background:#F5F6FB"],
html[data-theme="dark"] [style*="background:#F0F2F8"],
html[data-theme="dark"] [style*="background:#EEF0F5"],
html[data-theme="dark"] [style*="background:#ECEEF6"],
html[data-theme="dark"] [style*="background:#EAECF4"],
html[data-theme="dark"] [style*="background:#E8EBF2"],
html[data-theme="dark"] [style*="background:#D8DFFF"],
html[data-theme="dark"] [style*="background:#E4E8FF"],
html[data-theme="dark"] [style*="background:#F9FBFF"]{
    background:#161A28 !important;border-color:#262B3E !important;
}
/* Translucent-white cards (Market Pulse, some panels) */
html[data-theme="dark"] [style*="background:rgba(255,255,255,0.92)"],
html[data-theme="dark"] [style*="background:rgba(255,255,255,0.95)"],
html[data-theme="dark"] [style*="background:rgba(255,255,255,0.97)"],
html[data-theme="dark"] [style*="background:rgba(255,255,255,0.9)"],
html[data-theme="dark"] [style*="background:rgba(255, 255, 255, 0.92)"]{
    background:#141826 !important;border-color:#262B3E !important;
}
/* Light borders used as dividers → dark */
html[data-theme="dark"] [style*="border-top:1px solid #E3E5EA"],
html[data-theme="dark"] [style*="border-top:1px solid #ECEEF4"],
html[data-theme="dark"] [style*="border-bottom:1px solid #E3E5EA"],
html[data-theme="dark"] [style*="border:1px solid #ECEDF3"]{
    border-color:#262B3E !important;
}
/* Light gradient icon headers → subtle dark gradient */
html[data-theme="dark"] [style*="linear-gradient(135deg,#EEF0FF,#E4E8FF)"]{
    background:linear-gradient(135deg,#1B2030,#181C2A) !important;
}
/* Tinted status backgrounds (success/warn/danger) → muted dark tints */
html[data-theme="dark"] [style*="background:#F0FFF4"]{ background:rgba(31,168,85,0.10) !important;border-color:rgba(31,168,85,0.28) !important; }
html[data-theme="dark"] [style*="background:#FFFBEB"]{ background:rgba(200,150,30,0.10) !important;border-color:rgba(200,150,30,0.28) !important; }
html[data-theme="dark"] [style*="background:#FFF0F0"],
html[data-theme="dark"] [style*="background:#FFF6F6"]{ background:rgba(229,72,77,0.10) !important;border-color:rgba(229,72,77,0.28) !important; }

/* Force ALL near-black inline heading/label text light in dark mode.
   (Broad catch so no card title, stat label, or form label is stranded.) */
html[data-theme="dark"] [style*="color:#0C0C1A"],
html[data-theme="dark"] [style*="color:#0C0C1a"],
html[data-theme="dark"] [style*="color: #0C0C1A"],
html[data-theme="dark"] [style*="color:#14141F"],
html[data-theme="dark"] [style*="color:#0B1020"],
html[data-theme="dark"] [style*="color:#111827"],
html[data-theme="dark"] [style*="color:#1A1A3A"]{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
/* Uppercase field labels (#7A7F96 / #9499A8) → readable grey */
html[data-theme="dark"] [style*="color:#7A7F96"],
html[data-theme="dark"] [style*="color:#9499A8"]{ color:#AEB4C8 !important;-webkit-text-fill-color:#AEB4C8 !important; }
html[data-theme="dark"] [style*="color:#42475A"],
html[data-theme="dark"] [style*="color:#39445D"],
html[data-theme="dark"] [style*="color:#3D4358"],
html[data-theme="dark"] [style*="color:#5B5F6E"],
html[data-theme="dark"] [style*="color:#68738C"],
html[data-theme="dark"] [style*="color:#4A4F60"],
html[data-theme="dark"] [style*="color:#6B7280"],
html[data-theme="dark"] [style*="color:#52525B"]{ color:#AEB4C8 !important;-webkit-text-fill-color:#AEB4C8 !important; }
/* Success-green and other dark-on-tint accent text stays legible */
html[data-theme="dark"] [style*="color:#15803D"],
html[data-theme="dark"] [style*="color:#166534"]{ color:#4ADE80 !important;-webkit-text-fill-color:#4ADE80 !important; }
html[data-theme="dark"] [style*="color:#B91C1C"]{ color:#F87171 !important;-webkit-text-fill-color:#F87171 !important; }

/* Card titles that use var(--t1) inherit the dark token already, but a
   few use gradient text-fill — force those readable too. */
html[data-theme="dark"] .camp-title,
html[data-theme="dark"] .news-title,
html[data-theme="dark"] .news-title a,
html[data-theme="dark"] .dapp-name,
html[data-theme="dark"] .cex-name,
html[data-theme="dark"] .stat-value,
html[data-theme="dark"] .rd-stat-val{
    color:#EDEFF7 !important;-webkit-text-fill-color:#EDEFF7 !important;
}
/* Dark inputs on these pages: readable text + placeholder */
html[data-theme="dark"] [style*="background:#0"] input,
html[data-theme="dark"] input[style*="background:#1"],
html[data-theme="dark"] textarea[style*="background:#1"]{ color:#EDEFF7 !important; }


html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-lang_English) button:hover,
html[data-theme="dark"] [data-testid="stHorizontalBlock"]:has(.st-key-mode_docs) button:hover{
    border-color:#3A4260 !important;box-shadow:0 4px 12px rgba(60,80,255,0.22) !important;
}
</style>
        """,
        unsafe_allow_html=True,
    )

    LANG_OPTIONS = {
        "English":  "🇬🇧", "Hindi": "🇮🇳", "Spanish": "🇪🇸",
        "Arabic":   "🇸🇦", "Chinese": "🇨🇳", "Japanese": "🇯🇵",
    }
    cur_lang = st.session_state.octobot_lang
    cur_flag = LANG_OPTIONS.get(cur_lang, "🌐")
    current_mode = st.session_state.chat_mode
    is_general   = current_mode == "general"
    _x402_on     = bool(st.session_state.get("x402_enabled"))

    st.markdown(
        '<div class="cdeck">'
        '<div class="cdeck-hd">'
        '<span class="dot"></span>'
        '<span class="ttl">OctoBot Console</span>'
        '<span class="sub">' + cur_flag + ' ' + esc(cur_lang)
        + ' \u00b7 ' + ('Docs + General' if is_general else 'Docs Only') + '</span>'
        '</div>'
        '<div class="cdeck-sec">\U0001F310 Response language</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    LANG_CODE = {"English":"EN","Hindi":"HI","Spanish":"ES","Arabic":"AR","Chinese":"ZH","Japanese":"JA"}
    lang_cols = st.columns(len(LANG_OPTIONS))
    for li, (lang, flag) in enumerate(LANG_OPTIONS.items()):
        with lang_cols[li]:
            _code = LANG_CODE.get(lang, lang[:2].upper())
            _lbl = flag + " " + _code + ("  \u2713" if lang == cur_lang else "")
            if st.button(_lbl, key="lang_" + lang, use_container_width=True, help=lang):
                st.session_state.octobot_lang = lang
                st.rerun()

    st.markdown('<div class="cdeck-sec">\u2699\ufe0f Answer mode</div>', unsafe_allow_html=True)
    mc1, mc2 = st.columns(2)
    with mc1:
        _dl = "\U0001F4DA Docs Only" + ("  \u2713" if not is_general else "")
        if st.button(_dl, key="mode_docs", use_container_width=True):
            st.session_state.chat_mode = "docs"; st.rerun()
    with mc2:
        _gl = "\U0001F310 Docs + General" + ("  \u2713" if is_general else "")
        if st.button(_gl, key="mode_general", use_container_width=True):
            st.session_state.chat_mode = "general"; st.rerun()

    st.markdown('<div class="cdeck-sec">\U0001F4A0 Premium answers \u00b7 x402</div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.7rem;'
        'background:' + ("linear-gradient(135deg,#0A0A28,#1A1AFF)" if _x402_on else "#F5F6FB") + ';'
        'border:1px solid ' + ("#1A1AFF" if _x402_on else "#E1E4EE") + ';border-radius:12px;'
        'padding:0.7rem 0.95rem;box-shadow:' + ("0 6px 16px rgba(26,26,255,0.22)" if _x402_on else "none") + ';">'
        '<span style="font-size:19px;line-height:1;">\U0001F4A0</span>'
        '<div style="min-width:0;flex:1;">'
        '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
        '<span style="font-family:Syne,sans-serif;font-size:12.5px;font-weight:800;'
        'color:' + ("#FFFFFF" if _x402_on else "#0C0C1A") + ';">Premium \u00b7 x402</span>'
        '<span style="font-size:8.5px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;'
        'border-radius:999px;padding:2px 8px;'
        + ("background:rgba(255,255,255,0.18);color:#FFFFFF;" if _x402_on
           else "background:#FFFFFF;color:#9AA0AE;border:1px solid #E1E4EE;")
        + '">' + ("ON \u00b7 pay-per-call" if _x402_on else "OFF \u00b7 free mode") + '</span>'
        '</div>'
        '<div style="font-size:10.5px;line-height:1.5;margin-top:2px;'
        'color:' + ("rgba(255,255,255,0.75)" if _x402_on else "#8A90A6") + ';">'
        + (("Next question ~" + ("%.2f" % X402_PRICE_PROS) + " PROS \u2014 settle on-chain for a deeper answer.")
           if _x402_on else
           "Answers are free. Enable to settle a tiny PROS micro-payment for an expert, in-depth reply.")
        + '</div></div></div>',
        unsafe_allow_html=True,
    )

    _xc1, _xc2 = st.columns([1, 2], gap="small")
    with _xc1:
        st.session_state.x402_enabled = st.toggle(
            "Pay-per-call",
            value=st.session_state.x402_enabled,
            key="x402_enabled_toggle_main",
            help=("When ON, your next question is a premium (x402) call: OctoBot returns an "
                  "HTTP 402 payment challenge, you settle a tiny PROS micro-payment on-chain, "
                  "and the verified payment unlocks a deeper answer. Free answering stays on when OFF."),
        )
    with _xc2:
        _payto_in = st.text_input(
            "x402 pay-to address",
            value=st.session_state.get("x402_payto", ""),
            key="x402_payto_input",
            placeholder="\U0001F4B3 Wallet 0x\u2026 (blank = safe placeholder)",
            label_visibility="collapsed",
            help="Premium micro-payments are sent here. Paste your own wallet address. "
                 "Leave blank to use the safe placeholder (a burn address).",
        )
        if _payto_in != st.session_state.get("x402_payto", ""):
            _clean = (_payto_in or "").strip()
            if _clean == "" or valid_addr(_clean):
                st.session_state.x402_payto = _clean
            else:
                st.warning("That doesn\'t look like a valid 0x\u2026 address \u2014 keeping the previous one.")

    _active_payto = x402_get_payto()
    _is_custom = bool(valid_addr(st.session_state.get("x402_payto", "")))
    st.markdown(
        '<div style="font-size:9.5px;color:'
        + ("#15803D" if _is_custom else "#9AA0AE") + ';line-height:1.45;margin:2px 0 2px 2px;'
        'word-break:break-all;max-width:600px;">'
        + ("\u2713 Payments go to: " if _is_custom else "Using placeholder: ")
        + '<span style="font-family:DM Mono,monospace;">' + esc(_active_payto) + '</span></div>',
        unsafe_allow_html=True,
    )
    if st.session_state.x402_receipts:
        with st.expander("\U0001F9FE x402 receipts \u00b7 " + str(len(st.session_state.x402_receipts)), expanded=False):
            for _r in reversed(st.session_state.x402_receipts[-8:]):
                st.markdown(
                    '<div style="background:#F4F5F8;border-left:3px solid #1A1AFF;'
                    'border-radius:0 8px 8px 0;padding:0.45rem 0.7rem;margin-bottom:0.4rem;">'
                    '<div style="font-size:11px;font-weight:700;color:#0C0C1A;">'
                    + esc(_r.get("amount", "")) + ' PROS \u00b7 settled</div>'
                    '<div style="font-size:10px;color:#7A7F96;word-break:break-all;">'
                    + esc(_r.get("tx", "")[:22]) + '\u2026</div></div>',
                    unsafe_allow_html=True,
                )

    # ── Name gate — blocks chat until name entered ──
    if not st.session_state.sailor_done:
        st.markdown("""
        <style>
        section[data-testid="stSidebar"]{display:none!important;}
        div[data-testid="stDecoration"]{display:none!important;}
        .gate-wrap{
            display:flex;flex-direction:column;align-items:center;
            justify-content:flex-start;min-height:auto;padding:0.4rem 1rem 0 1rem;
        }
        .gate-card{
            background:#FFFFFF;
            border:1.5px solid rgba(26,26,255,0.15);
            border-radius:18px;
            padding:1.7rem 1.9rem 1.5rem 1.9rem;
            width:100%;max-width:330px;
            text-align:center;
            box-shadow:0 24px 60px rgba(26,26,255,0.13),
                       0 6px 18px rgba(0,0,0,0.07);
            position:relative;overflow:hidden;
            animation:card-pop 0.6s cubic-bezier(0.34,1.5,0.64,1) 0.1s both;
        }
        @keyframes card-pop{
            0%  {opacity:0;transform:scale(0.78) translateY(40px);}
            60% {opacity:1;transform:scale(1.04) translateY(-6px);}
            80% {transform:scale(0.98) translateY(2px);}
            100%{transform:scale(1) translateY(0);}
        }
        .gate-card::after{
            content:'';position:absolute;
            width:180px;height:180px;border-radius:50%;
            background:radial-gradient(circle,rgba(26,26,255,0.10) 0%,transparent 70%);
            top:-60px;right:-60px;pointer-events:none;
        }
        .gate-emoji{
            font-size:60px;display:block;margin-bottom:1rem;
            animation:emoji-bounce 0.7s cubic-bezier(0.34,1.6,0.64,1) 0.5s both;
        }
        @keyframes emoji-bounce{
            0%  {opacity:0;transform:scale(0.4) rotate(-15deg);}
            60% {transform:scale(1.18) rotate(6deg);}
            80% {transform:scale(0.94) rotate(-2deg);}
            100%{opacity:1;transform:scale(1) rotate(0deg);}
        }
        .gate-title{
            font-family:'Syne',sans-serif;font-size:21px;font-weight:800;
            color:#0C0C1A;margin-bottom:0.3rem;letter-spacing:-0.025em;
            animation:rise 0.5s cubic-bezier(0.16,1,0.3,1) 0.65s both;
        }
        .gate-sub{
            font-size:12px;color:#7A7F96;line-height:1.6;margin-bottom:0.4rem;
            animation:rise 0.5s cubic-bezier(0.16,1,0.3,1) 0.78s both;
        }
        .gate-divider{
            width:0%;height:1.5px;
            background:linear-gradient(90deg,#1A1AFF,#6B8CFF,#1A1AFF);
            border-radius:4px;margin:0 auto 1.4rem auto;
            animation:line-draw 0.6s cubic-bezier(0.4,0,0.2,1) 0.9s both;
        }
        @keyframes line-draw{
            from{width:0%;opacity:0;}to{width:60%;opacity:1;}
        }
        @keyframes rise{
            from{opacity:0;transform:translateY(12px);}
            to{opacity:1;transform:translateY(0);}
        }
        .gate-input-wrap div[data-testid="stTextInput"] input{
            border-radius:14px!important;
            border:2px solid rgba(26,26,255,0.18)!important;
            background:#F8F9FF!important;
            font-size:16px!important;font-weight:500!important;
            text-align:center!important;padding:0.9rem 1rem!important;
            font-family:'DM Sans',sans-serif!important;color:#0C0C1A!important;
            transition:border-color 200ms ease,box-shadow 200ms ease!important;
            animation:rise 0.5s cubic-bezier(0.16,1,0.3,1) 1s both;
        }
        .gate-input-wrap div[data-testid="stTextInput"] input:focus{
            border-color:#1A1AFF!important;
            box-shadow:0 0 0 4px rgba(26,26,255,0.10)!important;
            background:#FFFFFF!important;outline:none!important;
        }
        .gate-input-wrap div[data-testid="stTextInput"] input::placeholder{
            color:#B0B4C4!important;font-size:13px!important;
        }
        </style>
        <div class="gate-wrap">
          <div class="gate-card">
            <span class="gate-emoji">🐙</span>
            <div class="gate-title">Ahoy, Sailor!</div>
            <div class="gate-sub">What should I call you?<br>Enter your name to open OctoBot.</div>
            <div class="gate-divider"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.markdown('<div class="gate-input-wrap">', unsafe_allow_html=True)
            name_val = st.text_input(
                "name",
                placeholder="Your name… then press Enter",
                key="sailor_input",
                label_visibility="collapsed",
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown(
                '<p style="text-align:center;font-size:11px;color:#B0B4C4;margin-top:0.3rem;">Press Enter after typing</p>',
                unsafe_allow_html=True,
            )

        if name_val.strip():
            st.session_state.sailor_name = name_val.strip()
            st.session_state.sailor_done = True
            st.rerun()
        st.stop()

    # ── Welcome card with name ──────────────────
    if not st.session_state.messages:
        name      = st.session_state.sailor_name
        mode_note = ("Docs + General mode: OctoBot answers from docs first, then uses Gemini for anything not in documentation."
                     if st.session_state.chat_mode == "general"
                     else "Docs only mode: OctoBot answers strictly from verified Pharos documentation.")
        st.markdown(
            '<div class="welcome-card" style="animation:page-fadein 0.5s cubic-bezier(0.4,0,0.2,1) both;">'
            '<h3>Hi ' + esc(name) + '! 👋 Welcome aboard</h3>'
            '<p>Ask me anything about Pharos Network — SPNs, Native Restaking, RWA, consensus, '
            'building on Pharos, or the $PROS token. <em>' + mode_note + '</em></p>'
            '<div class="tag-row">'
            '<span class="tag">SPNs</span><span class="tag">L1 Architecture</span>'
            '<span class="tag">Native Restaking</span><span class="tag">RWA</span>'
            '<span class="tag">DeFi</span><span class="tag">Build on Pharos</span>'
            '<span class="tag">$PROS Token</span><span class="tag">🌐 Multilingual</span>'
            '</div></div>'
            '<p class="notice" style="color:#000000;font-weight:700;">⚠️ If chat is not responding or not loading, API usage may be exhausted. '
            'Run OctoBot locally with your own API key to continue.</p>',
            unsafe_allow_html=True,
        )


    # ── x402: render any pending payment gate FIRST (persists across reruns) ──
    # Its Verify/Simulate buttons live here, not inside `if question:`, so a
    # button click — which reruns with empty chat_input — still finds the gate.
    if st.session_state.get("x402_challenge"):
        if x402_render_pending_gate():
            st.stop()

    # ── Chat input + answer ────────────────────
    pending    = st.session_state.pop("pending_q", None)
    sel_lang   = st.session_state.get("octobot_lang", "English")
    placeholder = (
        "Ask anything about Pharos — any language 🌐"
        if sel_lang == "English"
        else f"Ask OctoBot in {sel_lang} 🌐"
    )
    user_input = st.chat_input(placeholder)

    # Palette "docs" items land here with a prefilled question stashed by
    # the command palette; drop it into the chat box for the user to send.
    components.html(
        """
<script>
(function(){
  try{
    var PW = window.parent;
    var q = PW.sessionStorage.getItem('octobot-prefill');
    if (!q) return;
    PW.sessionStorage.removeItem('octobot-prefill');
    var tries = 0;
    var iv = setInterval(function(){
      tries++;
      var ta = PW.document.querySelector('[data-testid="stChatInput"] textarea');
      if (ta){
        var setter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype,'value').set;
        setter.call(ta, q);
        ta.dispatchEvent(new Event('input', {bubbles:true}));
        ta.focus();
        clearInterval(iv);
      }
      if (tries > 40) clearInterval(iv);
    }, 80);
  }catch(e){}
})();
</script>
        """,
        height=0,
    )

    question   = pending or user_input

    if question:
        # Prepend a language instruction to guide OctoBot's response language
        lang_prefix = (
            "" if sel_lang == "English"
            else f"[RESPOND IN {sel_lang.upper()} ONLY] "
        )
        guided_question = lang_prefix + question

        st.session_state.messages.append({"role":"user","content":question})
        with st.chat_message("user", avatar="👤"):
            st.markdown(question)

        # ── x402 GATE (trigger only) ─────────────────────────────
        # If premium mode is ON and this resource isn't paid yet, persist a
        # challenge and rerun. The gate is rendered by x402_render_pending_gate()
        # at the top of the chat page, so its Verify/Simulate buttons survive the
        # rerun a click triggers (this fixes the "tx hash does nothing" bug).
        # Free mode skips this entirely.
        _x402_ch = x402_make_challenge(question)
        _x402_premium = bool(st.session_state.get("x402_enabled"))
        _x402_paid = _x402_ch["resource"] in st.session_state.get("x402_unlocked", {})

        if _x402_premium and not _x402_paid:
            _x402_ch["question"] = question
            st.session_state.x402_challenge = _x402_ch
            st.session_state.messages.append({
                "role": "assistant",
                "content": "⚡ **402 Payment Required** — this premium question is waiting for an x402 "
                           "micro-payment of " + ("%.2f" % _x402_ch["amount_pros"]) + " PROS to unlock.",
            })
            st.session_state.sources_history.append([])
            st.rerun()

        with st.chat_message("assistant", avatar="🐙"):
            # ── Thinking orb (feature 1) ──────────────
            orb_slot = st.empty()
            with orb_slot.container():
                render_thinking_orb("thinking")

            with st.spinner(""):
                try:
                    # x402: if this question's resource was paid for, generate
                    # the ENHANCED premium answer instead of the standard one.
                    _x402_ch_now = x402_make_challenge(question)
                    if _x402_ch_now["resource"] in st.session_state.get("x402_unlocked", {}):
                        answer  = x402_generate_premium_answer(question, bot, sel_lang)
                        sources = []
                    elif detect_app_feature(question):
                        # In-app DeFi assistant: the user is asking how to DO
                        # something in this app. The docs index describes Pharos,
                        # not this UI, so answer from the app's own feature guide.
                        _feat   = detect_app_feature(question)
                        answer  = render_feature_guide(_feat)
                        sources = []
                        if sel_lang and sel_lang != "English":
                            try:
                                _tl = ChatGoogleGenerativeAI(
                                    model="gemini-2.5-flash", temperature=0.2,
                                    google_api_key=os.getenv("GEMINI_API_KEY"),
                                )
                                answer = _tl.invoke([HumanMessage(
                                    content="Translate to " + sel_lang +
                                            ". Keep all markdown, numbers, addresses and "
                                            "UI labels exactly as-is:\n\n" + answer
                                )]).content
                            except Exception:
                                pass  # fall back to the English guide
                    else:
                        # General mode: try docs first, fall back to Gemini if not found
                        answer, sources = bot.ask(guided_question)
                        if (st.session_state.chat_mode == "general"
                                and "I could not find that information" in answer):
                            fallback_llm = ChatGoogleGenerativeAI(
                                model="gemini-2.5-flash", temperature=0.5,
                                google_api_key=os.getenv("GEMINI_API_KEY"),
                            )
                            lang_instruction = (
                                f"CRITICAL: You MUST respond entirely in {sel_lang}. "
                                f"Do not use any other language. "
                                if sel_lang != "English"
                                else "Always respond in English. "
                            )
                            fb_answer = fallback_llm.invoke([
                                HumanMessage(content=
                                    "You are OctoBot, a helpful AI assistant for the Pharos blockchain community. "
                                    "Answer this question helpfully and accurately. "
                                    "If relevant, mention that Pharos is a Layer 1 blockchain focused on RWA tokenization and institutional DeFi.\n"
                                    + lang_instruction +
                                    "Keep technical terms (PROS, SPN, RWA, L1, EVM) in their original English form.\n\n"
                                    "Question: " + question
                                )
                            ])
                            answer  = fb_answer.content
                            sources = []
                except Exception as e:
                    answer  = "An error occurred: " + str(e)
                    sources = []

            # ── Orb: done state ───────────────────────
            with orb_slot.container():
                render_thinking_orb("done")

            if x402_make_challenge(question)["resource"] in st.session_state.get("x402_unlocked", {}):
                _rec_tx = st.session_state.get("x402_unlocked", {}).get(
                    x402_make_challenge(question)["resource"], "")
                _sim = (_rec_tx == "SIMULATED")
                st.markdown(
                    '<div style="display:inline-flex;align-items:center;gap:7px;'
                    'background:linear-gradient(135deg,#1414E8,#7c3aed);color:#fff;'
                    'border-radius:999px;padding:4px 12px;font-size:11px;font-weight:700;'
                    'margin-bottom:8px;">⚡ Premium · x402 settled'
                    + ('  ·  demo' if _sim else '') + '</div>',
                    unsafe_allow_html=True,
                )

            st.markdown(answer)

            # ── Build Path card (feature 2) ───────────
            msg_idx = str(len(st.session_state.messages))
            goal = st.session_state.get("build_path_goal")
            if goal and st.session_state.get("build_path_data") is None:
                with st.spinner("Generating your build path…"):
                    bp_data = build_path_generator(goal, bot)
                st.session_state.build_path_data = bp_data
                st.session_state.build_path_goal = None

            bp = st.session_state.get("build_path_data")
            if bp and isinstance(bp, dict):
                steps_html = "".join([
                    f'<div class="build-path-step">'
                    f'<div class="build-step-num">{esc(s["num"])}</div>'
                    f'<div><div class="build-step-text">{esc(s["title"])}</div>'
                    f'<div class="build-step-sub">{esc(s["desc"])}</div></div>'
                    f'</div>'
                    for s in bp.get("steps", [])
                ])
                docs_html = " · ".join([
                    f'<a href="{esc_url(d["url"])}" target="_blank" rel="noopener noreferrer" '
                    f'style="color:#1A1AFF;font-size:11px;font-weight:600;text-decoration:none;">'
                    f'{esc(d["title"])} ↗</a>'
                    for d in bp.get("docs", [])
                ])
                actions_html = "".join([
                    f'<a class="build-action-btn" href="{esc_url(a["url"])}" target="_blank" rel="noopener noreferrer">{esc(a["label"])} ↗</a>'
                    for a in bp.get("actions", [])
                ])
                st.markdown(
                    f'<div class="build-path-card">'
                    f'<div class="build-path-title">Your Build Path</div>'
                    f'<div class="build-path-goal">{esc(bp.get("goal",""))}</div>'
                    f'{steps_html}'
                    f'<div style="margin-top:0.7rem;font-size:11px;color:#7A7F96;margin-bottom:4px;">📄 Key Docs</div>'
                    f'<div style="display:flex;gap:8px;flex-wrap:wrap;">{docs_html}</div>'
                    f'<div class="build-path-actions">{actions_html}'
                    f'<button class="build-action-btn build-action-ghost" '
                    f'onclick="(function(){{document.getElementById(\'bpc\').style.display=\'none\';}})()">✕ Dismiss</button>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("✕ Clear build path", key="clear_bp_" + msg_idx):
                    st.session_state.build_path_data = None
                    st.rerun()

            # ── Voice ─────────────────────────────────
            if st.session_state.voice_reply:
                speak_text(answer)

            # ── Action buttons row ────────────────────
            render_copy_share_download(answer, btn_key=msg_idx)

            # Read aloud button
            if st.button("🔊 Read", key="replay_" + msg_idx, help="Read aloud"):
                speak_text(answer)

            # ── Show relevant images ──────────────────
            img_key = "show_imgs_" + msg_idx
            if img_key not in st.session_state:
                st.session_state[img_key] = False
            if not st.session_state[img_key]:
                if st.button("🖼 Show Images", key="imgs_btn_" + msg_idx):
                    st.session_state[img_key] = True
                    st.rerun()
            else:
                imgs = get_image_search_results(question)
                img_cols = st.columns(3)
                for ci, img in enumerate(imgs[:3]):
                    with img_cols[ci]:
                        try:
                            st.image(img["url"], use_container_width=True, caption="")
                        except Exception:
                            st.markdown(
                                f'<img src="{img["url"]}" style="width:100%;border-radius:8px;" />',
                                unsafe_allow_html=True,
                            )
                if st.button("✕ Hide images", key="imgs_hide_" + msg_idx):
                    st.session_state[img_key] = False
                    st.rerun()

            # ── Price chart if relevant ───────────────
            q_lower = question.lower()
            if any(kw in q_lower for kw in ["price","market cap","pros","$pros","token"]):
                with st.container(border=True):
                    st.markdown('<div class="chart-card-label">$PROS · 24H</div>', unsafe_allow_html=True)
                    render_price_chart(
                        get_price_chart_df(),
                        chart_key="chat_chart_" + msg_idx
                    )

            # ── Sources ───────────────────────────────
            if sources:
                with st.expander(f"📚 Sources · {len(sources)}", expanded=False):
                    for s in sources:
                        st.markdown(
                            f'<div style="background:#F4F5F8;border-left:3px solid #1A1AFF;'
                            f'border-radius:0 8px 8px 0;padding:0.6rem 0.9rem;margin-bottom:0.5rem;">'
                            f'<div style="font-size:13px;font-weight:600;color:#0C0C1A;margin-bottom:3px;">{esc(s["title"])}</div>'
                            f'<a href="{esc_url(s["url"])}" target="_blank" rel="noopener noreferrer" '
                            f'style="font-size:11px;color:#1A1AFF;text-decoration:none;word-break:break-all;">'
                            f'{esc(s["url"])}</a>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

            # ── Follow-up questions ───────────────────
            try:
                if "fups_" + msg_idx not in st.session_state:
                    fups = get_followup_questions(question, answer)
                    st.session_state["fups_" + msg_idx] = fups
                fups = st.session_state.get("fups_" + msg_idx, [])
            except Exception:
                fups = []

            if fups:
                st.markdown(
                    '<div style="margin-top:0.7rem;padding-top:0.5rem;border-top:1px solid #D0D3E0;">'
                    '<div style="font-size:10px;font-weight:600;color:#7A7F96;letter-spacing:0.08em;'
                    'text-transform:uppercase;margin-bottom:0.5rem;">Follow-up questions</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="followup-btn-row">', unsafe_allow_html=True)
                fup_cols = st.columns(len(fups))
                for fup_i, (fcol, fq) in enumerate(zip(fup_cols, fups)):
                    with fcol:
                        # Key uses the loop position (enumerate), never
                        # fups.index(fq) or hash(fq) — both of those can
                        # collide (duplicate questions from Gemini, or
                        # hash-seed randomisation across processes) and
                        # trigger a Streamlit "duplicate element ID" error,
                        # which crashes the whole page render and looks
                        # exactly like the button "doing nothing."
                        fq_key = "fup_" + msg_idx + "_" + str(fup_i)
                        if st.button("↪ " + fq, key=fq_key, use_container_width=True):
                            st.session_state["pending_q"] = fq
                            # Clear this answer's cached follow-ups so the
                            # NEXT answer (from the follow-up question) gets
                            # its own fresh set instead of reusing this one.
                            st.session_state.pop("fups_" + msg_idx, None)
                            st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

        st.session_state.messages.append({"role":"assistant","content":answer})
        st.session_state.sources_history.append(sources)


# ═════════════════════════════════════════════
# PAGE: CAMPAIGNS
# ═════════════════════════════════════════════
# ═════════════════════════════════════════════
# PAGE: DEFI HUB
#
# Design principle: every number shown here is either read live from
# chain / a market API, or it is not shown at all. There are no
# simulated positions, no invented APRs, and no placeholder yields.
#
# Where Pharos publishes a verified contract (tokens, MultiCall3), we
# call it directly. Where no contract is published — PROS staking and
# the FaroSwap mainnet router are NOT in the official docs, and stPROS
# is publicly described as not yet live — we deep-link to the official
# protocol UI rather than send funds to an unverified address.
# ═════════════════════════════════════════════
elif st.session_state.page == "defi":

    DEFI_INTEGRATIONS = [
        ("FaroSwap",  "faroswap.xyz",      "DEX · AMM & PMM",       FAROSWAP_URL,                 "🔄"),
        ("LI.FI",     "li.fi",             "Bridge Aggregation",    "https://jumper.exchange",    "🌉"),
        ("CCIP",      "chain.link",        "Cross-chain Messaging", "https://docs.pharos.xyz/tooling-and-infrastructure/cross-chain/chainlink-ccip", "🔗"),
        ("CCTP v2",   "circle.com",        "Native USDC Transfers", "https://docs.pharos.xyz/tooling-and-infrastructure/cross-chain/circle-cctp", "💵"),
        ("LayerZero", "layerzero.network", "Omnichain Protocol",    "https://docs.pharos.xyz/tooling-and-infrastructure/cross-chain/layerzero", "🕸️"),
        ("Faroo",     "faroo.xyz",         "Pharos Incubator",      "https://x.com/Farooxyz",     "⚓"),
        ("R2",        "r2.money",          "Yield-bearing Stables", PHAROS_ECOSYSTEM_URL,         "🏛️"),
        ("AquaFlux",  "aquaflux.pro",      "RWA Structuring",       "https://aquaflux.pro",       "💧"),
        ("Zona",      "zona.finance",      "RealFi Markets",        PHAROS_ECOSYSTEM_URL,         "🏘️"),
        ("Morpho",    "morpho.org",        "Lending",               "https://morpho.org",         "🦋"),
        ("Bitverse",  "bitverse.zone",     "Onchain CLOB",          PHAROS_ECOSYSTEM_URL,         "📈"),
        ("Ember",     "ember.ag",          "AI DeFi Agent",         PHAROS_ECOSYSTEM_URL,         "🔥"),
    ]

    st.session_state.setdefault("defi_tab", "Portfolio")

    _w3a       = st.session_state.get("w3_address", "")
    _w3c       = st.session_state.get("w3_chain", "")
    _connected = bool(_w3a)
    _right_net = (_w3c or "").lower() == PHAROS_CHAIN_ID_HEX.lower()
    _pros_usd  = (price_data or {}).get("price_usd") or 0

    def _stat_card(label, value, sub="", accent="var(--blue)"):
        return (
            '<div class="defi-card hover-lift">'
            f'<div class="defi-card-l">{esc(label)}</div>'
            f'<div class="defi-card-v">{value}</div>'
            + (f'<div class="defi-card-s" style="color:{accent};">{sub}</div>' if sub else '')
            + '</div>'
        )

    def _stat_grid(cards):
        return '<div class="defi-grid">' + "".join(cards) + '</div>'

    def _panel(title, sub=""):
        return (
            '<div class="defi-panel">'
            f'<div class="defi-panel-t">{title}</div>'
            + (f'<div class="defi-panel-s">{sub}</div>' if sub else '')
            + '</div>'
        )

    def _gate(action="use this feature"):
        """Wallet is the single auth layer for every on-chain action."""
        if not _connected:
            st.markdown(
                '<div class="defi-gate">'
                '<div class="defi-gate-i">🔗</div>'
                '<div class="defi-gate-t">Connect your wallet</div>'
                f'<div class="defi-gate-s">Connect an EVM wallet to {esc(action)}. '
                'Use the <b>Connect Wallet</b> button in the top-right corner.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            return False
        if not _right_net:
            st.markdown(
                '<div class="defi-gate defi-gate-warn">'
                '<div class="defi-gate-i">⚠️</div>'
                '<div class="defi-gate-t">Wrong network</div>'
                '<div class="defi-gate-s">Your wallet is connected to another chain. '
                'Click <b>Switch</b> in the wallet pill to move to Pharos Pacific Mainnet '
                '(chain 1672).</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            return False
        return True

    def _not_live(title, body, url, cta):
        """Honest state for protocols with no published mainnet contract."""
        st.markdown(
            '<div class="defi-note">'
            f'<div class="defi-note-t">{title}</div>'
            f'<div class="defi-note-s">{body}</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        st.link_button(cta, url, use_container_width=False)

    # ── Header ───────────────────────────────────────────────
    st.markdown(
        '<div class="section-dark">'
        '<div style="position:relative;z-index:1;">'
        '<div class="section-eyebrow"><span style="font-size:12px;">🏦</span>&nbsp;PHAROS DEFI HUB</div>'
        '<h2 class="section-h">Your Pharos Portfolio</h2>'
        '<p class="section-sub">Live balances, wallet intelligence and RWA markets — read directly '
        'from Pharos Pacific Mainnet. Connect any EVM wallet to begin.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    DEFI_TABS = ["Portfolio", "Swap", "Bridge", "Staking", "Wallet Score",
                 "History", "RWA Market", "Explorer"]
    _tab_cols = st.columns(len(DEFI_TABS))
    for _ti, _tn in enumerate(DEFI_TABS):
        with _tab_cols[_ti]:
            if st.button(_tn, key="defi_tab_" + _tn.replace(" ", "_"), use_container_width=True):
                st.session_state["defi_tab"] = _tn
                st.rerun()
    _tab = st.session_state["defi_tab"]
    st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)

    # ══ PORTFOLIO — real balances ═══════════════════════════
    if _tab == "Portfolio":
        st.markdown(_panel("💼 Portfolio",
                    "Native PROS and registry tokens, read live from chain via MultiCall3."),
                    unsafe_allow_html=True)
        if _gate("view your live portfolio"):
            if st.button("↻ Refresh balances", key="defi_bal_refresh"):
                st.session_state.pop("defi_balances", None)
            if "defi_balances" not in st.session_state:
                with st.spinner("Reading balances from Pharos mainnet…"):
                    st.session_state["defi_balances"] = fetch_token_balances(_w3a)
            _b = st.session_state["defi_balances"]

            if not _b.get("available"):
                st.error("Could not read balances: " + esc(_b.get("error") or "RPC unreachable"))
                if st.button("Try again", key="defi_bal_retry"):
                    st.session_state.pop("defi_balances", None)
                    st.rerun()
            else:
                _nat = _b.get("native") or 0.0
                _cards = [_stat_card(
                    "PROS · Native", f"{_nat:,.6f}",
                    (f"≈ ${_nat * _pros_usd:,.2f}" if _pros_usd else "gas token"),
                )]
                for _t in _b.get("tokens", []):
                    _cards.append(_stat_card(
                        _t["sym"] + " · " + _t["label"], f"{_t['bal']:,.6f}",
                        "Pharos mainnet", "var(--t2)"))
                st.markdown(_stat_grid(_cards), unsafe_allow_html=True)
                st.caption("Token addresses come from the official Pharos Token Registry "
                           "(docs.pharos.xyz). Balances are read live — never cached server-side.")
                st.link_button("View wallet on PharosScan ↗",
                               PHAROS_EXPLORER_URL + "/address/" + _w3a)

    # ══ SWAP ════════════════════════════════════════════════
    elif _tab == "Swap":
        st.markdown(_panel("🔄 Swap", "Trade PROS and registry tokens on FaroSwap, "
                    "the native AMM + PMM DEX on Pharos."), unsafe_allow_html=True)
        if _gate("swap tokens"):
            _not_live(
                "Swaps execute on FaroSwap",
                "This hub does not hold a verified FaroSwap mainnet router address — "
                "Pharos does not publish one in its contract registry, so routing a swap "
                "from here would mean sending your funds to an unverified contract. "
                "Instead, open FaroSwap directly with the same wallet you have connected here. "
                "Your connection carries over.",
                FAROSWAP_URL, "Open FaroSwap ↗",
            )
            st.caption("When an official router address is published, swaps will execute "
                       "natively in this tab.")

    # ══ BRIDGE ══════════════════════════════════════════════
    elif _tab == "Bridge":
        st.markdown(_panel("🌉 Bridge",
                    "Move assets to and from Pharos. Pharos supports Chainlink CCIP, "
                    "Circle CCTP v2 and LayerZero."), unsafe_allow_html=True)
        if _gate("bridge assets"):
            _not_live(
                "Bridging runs through audited routers",
                "Bridge transactions must go through each protocol's own audited router. "
                "Jumper (LI.FI) aggregates the supported routes into Pharos and will use "
                "the wallet you already have connected.",
                "https://jumper.exchange", "Open Jumper (LI.FI) ↗",
            )
            _bc1, _bc2 = st.columns(2)
            with _bc1:
                st.link_button("Circle CCTP docs ↗",
                               "https://docs.pharos.xyz/tooling-and-infrastructure/cross-chain/circle-cctp",
                               use_container_width=True)
            with _bc2:
                st.link_button("Chainlink CCIP docs ↗",
                               "https://docs.pharos.xyz/tooling-and-infrastructure/cross-chain/chainlink-ccip",
                               use_container_width=True)

    # ══ STAKING ═════════════════════════════════════════════
    elif _tab == "Staking":
        st.markdown(_panel("⚡ PROS Staking",
                    "Stake PROS to help secure Pharos and earn protocol rewards."),
                    unsafe_allow_html=True)
        if _gate("stake PROS"):
            if PROS_STAKING_ADDR:
                st.info("Staking contract configured — native staking enabled.")
            else:
                st.markdown(
                    '<div class="defi-note">'
                    '<div class="defi-note-t">Native staking is not live yet</div>'
                    '<div class="defi-note-s">'
                    'Pharos has not published a PROS staking or stPROS contract address in its '
                    'official documentation, and stPROS native yield is publicly described as '
                    'not yet live. Rather than show you an invented APR or route funds to an '
                    'unverified contract, this tab stays honest until the real contract ships. '
                    'Follow the official channels for the launch announcement.'
                    '</div></div>',
                    unsafe_allow_html=True,
                )
                _sc1, _sc2 = st.columns(2)
                with _sc1:
                    st.link_button("Pharos announcements ↗", PHAROS_X_URL, use_container_width=True)
                with _sc2:
                    st.link_button("Ask in Pharos Discord ↗", PHAROS_DISCORD_URL, use_container_width=True)
                st.caption("Developer note: set PROS_STAKING_ADDR in this file once the "
                           "official address is published — the staking UI activates automatically.")

    # ══ WALLET SCORE ════════════════════════════════════════
    elif _tab == "Wallet Score":
        st.markdown(_panel("🧠 Wallet Analysis & Score",
                    "On-chain reputation, computed from real mainnet activity."),
                    unsafe_allow_html=True)
        if _gate("analyse your wallet"):
            if "defi_wa_data" not in st.session_state:
                with st.spinner("Reading on-chain activity…"):
                    st.session_state["defi_wa_data"] = fetch_pharos_onchain_data(_w3a)
            _d = st.session_state["defi_wa_data"]
            if not _d.get("available"):
                st.error("Could not read this address: " + esc(_d.get("error") or "RPC unreachable"))
                if st.button("Retry", key="defi_wa_retry"):
                    st.session_state.pop("defi_wa_data", None)
                    st.rerun()
            else:
                _txn = _d.get("tx_count") or 0
                _bal = _d.get("balance_pros") or 0.0
                # Transparent, deterministic scoring — no black box, no fake data.
                _act  = min(_txn, 200) / 200
                _hold = min(_bal, 500) / 500
                _eng  = 1.0 if (_txn > 0 and _bal > 0) else 0.0
                _score = int(min(100, round(10 + _act * 45 + _hold * 30 + _eng * 15)))
                _tier = ("Navigator" if _score >= 80 else "Voyager" if _score >= 55
                         else "Sailor" if _score >= 30 else "Newcomer")
                _col = ("#22C55E" if _score >= 80 else "#1A1AFF" if _score >= 55
                        else "#F59E0B" if _score >= 30 else "#9499A8")
                st.markdown(_stat_grid([
                    _stat_card("Wallet Score", f'<span style="color:{_col};">{_score} / 100</span>', _tier, _col),
                    _stat_card("PROS balance", f"{_bal:,.4f}",
                               (f"≈ ${_bal * _pros_usd:,.2f}" if _pros_usd else "")),
                    _stat_card("Transactions sent", f"{_txn:,}", "nonce"),
                    _stat_card("Account type", "Contract" if _d.get("is_contract") else "EOA wallet"),
                ]), unsafe_allow_html=True)
                _bh = ""
                for _bl, _bv in [("Activity", _act), ("Holdings", _hold), ("Engagement", _eng)]:
                    _bh += (
                        f'<div style="margin-bottom:9px;"><div style="display:flex;'
                        f'justify-content:space-between;font-size:11px;color:var(--t2);'
                        f'margin-bottom:3px;"><span>{_bl}</span><span>{int(_bv*100)}%</span></div>'
                        f'<div class="defi-bar"><div class="defi-bar-f" '
                        f'style="width:{_bv*100:.0f}%;background:{_col};"></div></div></div>'
                    )
                st.markdown('<div class="defi-panel-solid">'
                            '<div class="defi-panel-t" style="margin-bottom:10px;">Score breakdown</div>'
                            + _bh + '</div>', unsafe_allow_html=True)
                st.caption("Scoring is deterministic and computed from public on-chain data only.")

    # ══ HISTORY ═════════════════════════════════════════════
    elif _tab == "History":
        st.markdown(_panel("🧾 Transaction History",
                    "Your on-chain footprint on Pharos mainnet."), unsafe_allow_html=True)
        if _gate("view your transaction history"):
            if "defi_ha_data" not in st.session_state:
                with st.spinner("Reading on-chain data…"):
                    st.session_state["defi_ha_data"] = fetch_pharos_onchain_data(_w3a)
            _hd = st.session_state["defi_ha_data"]
            if _hd.get("available"):
                st.markdown(_stat_grid([
                    _stat_card("Transactions sent", f"{(_hd.get('tx_count') or 0):,}", "account nonce"),
                    _stat_card("PROS balance", f"{(_hd.get('balance_pros') or 0):,.4f}"),
                ]), unsafe_allow_html=True)
                st.markdown(
                    '<div class="defi-note"><div class="defi-note-s">'
                    'Pharos JSON-RPC exposes account state, not an indexed transaction list. '
                    'For a full itemised history, PharosScan indexes every transfer for this address.'
                    '</div></div>', unsafe_allow_html=True)
                st.link_button("Full history on PharosScan ↗",
                               PHAROS_EXPLORER_URL + "/address/" + _w3a)
            else:
                st.error("Could not read this address: " + esc(_hd.get("error") or "RPC unreachable"))

    # ══ RWA MARKET ══════════════════════════════════════════
    elif _tab == "RWA Market":
        st.markdown(_panel("📊 Live RWA Market",
                    "Live prices for leading real-world-asset tokens, alongside $PROS."),
                    unsafe_allow_html=True)
        with st.spinner("Loading live market data…"):
            _mk = fetch_rwa_market()
        if not _mk.get("rows"):
            st.error("Live RWA market data is temporarily unavailable — try again shortly.")
            if st.button("Retry", key="rwa_retry"):
                st.session_state.pop("rwa_market_cache", None)
                st.rerun()
        else:
            _cards = []
            for _r in _mk["rows"]:
                _chg = _r.get("chg")
                _cc  = "#22C55E" if (_chg or 0) >= 0 else "#E5484D"
                _cs  = (f"{_chg:+.2f}% · 24h" if _chg is not None else "—")
                _pv  = _r.get("price") or 0
                _ps  = f"${_pv:,.4f}" if _pv < 10 else f"${_pv:,.2f}"
                _cards.append(_stat_card(f"{_r['sym']} · {_r['name']}", _ps,
                                         f'<span style="color:{_cc};">{_cs}</span> · {esc(_r["tag"])}',
                                         _cc))
            st.markdown(_stat_grid(_cards), unsafe_allow_html=True)
            st.caption(f"Live market data · as of {esc(_mk.get('as_of',''))}")
            if st.button("🔄 Refresh market data", key="rwa_refresh"):
                st.session_state.pop("rwa_market_cache", None)
                st.rerun()

    # ══ EXPLORER ════════════════════════════════════════════
    elif _tab == "Explorer":
        st.markdown(_panel("🔍 Pharos Protocol Explorer",
                    "Inspect any transaction or address on Pharos mainnet. No wallet required."),
                    unsafe_allow_html=True)
        _q = st.text_input("Transaction hash or address", key="defi_exp_q",
                           placeholder="0x… (66-char tx hash or 42-char address)")
        if st.button("Inspect →", key="defi_exp_go"):
            _qs = (_q or "").strip()
            if valid_txhash(_qs):
                with st.spinner("Reading transaction…"):
                    st.session_state["defi_exp_res"] = ("tx", fetch_pharos_transaction(_qs))
            elif valid_addr(_qs):
                with st.spinner("Reading address…"):
                    st.session_state["defi_exp_res"] = ("addr", fetch_pharos_onchain_data(_qs))
            else:
                st.warning("Enter a valid transaction hash (0x + 64 hex) or address (0x + 40 hex).")
        _res = st.session_state.get("defi_exp_res")
        if _res:
            _kind, _rd = _res
            if not _rd.get("available"):
                st.error("Lookup failed: " + esc(_rd.get("error") or "not found / RPC unreachable"))
            elif _kind == "tx":
                _st = _rd.get("status")
                _sc = "#22C55E" if _st == "success" else "#E5484D" if _st == "failed" else "#F59E0B"
                st.markdown(_stat_grid([
                    _stat_card("Status", f'<span style="color:{_sc};">{esc((_st or "pending").title())}</span>'),
                    _stat_card("Value", f"{(_rd.get('value_pros') or 0):,.6f} PROS"),
                    _stat_card("Block", f"{_rd.get('block_number') or '—'}"),
                    _stat_card("Type", "Contract call" if _rd.get("is_contract_call") else "Transfer"),
                ]), unsafe_allow_html=True)
                st.markdown(
                    '<div style="font-size:11.5px;color:var(--t2);word-break:break-all;">'
                    f'<b>From</b> <code>{esc(_rd.get("from_addr") or "—")}</code><br>'
                    f'<b>To</b> <code>{esc(_rd.get("to_addr") or "—")}</code></div>',
                    unsafe_allow_html=True)
                st.link_button("Open in PharosScan ↗", PHAROS_EXPLORER_URL + "/tx/" + (_q or "").strip())
            else:
                st.markdown(_stat_grid([
                    _stat_card("PROS balance", f"{(_rd.get('balance_pros') or 0):,.4f}"),
                    _stat_card("Transactions", f"{(_rd.get('tx_count') or 0):,}"),
                    _stat_card("Type", "Contract" if _rd.get("is_contract") else "EOA wallet"),
                ]), unsafe_allow_html=True)
                st.link_button("Open in PharosScan ↗",
                               PHAROS_EXPLORER_URL + "/address/" + (_q or "").strip())

    # ── Ecosystem Integrations ───────────────────────────────
    st.markdown(
        '<div style="height:0.8rem;"></div>'
        '<div class="defi-eyebrow">Ecosystem Integrations</div>',
        unsafe_allow_html=True,
    )
    _integ_html = '<div class="defi-integ">'
    for _nm, _dom, _tagl, _url, _emo in DEFI_INTEGRATIONS:
        _fav = f"https://www.google.com/s2/favicons?domain={_dom}&sz=64"
        _integ_html += (
            f'<a href="{esc_url(_url)}" target="_blank" rel="noopener" class="defi-integ-c hover-lift">'
            f'<img src="{_fav}" width="28" height="28" loading="lazy" decoding="async" '
            f'style="border-radius:8px;" '
            f'onerror="this.outerHTML=\'<span style=&quot;font-size:22px;&quot;>{_emo}</span>\'"/>'
            f'<span class="defi-integ-n">{esc(_nm)}</span>'
            f'<span class="defi-integ-t">{esc(_tagl)}</span>'
            f'</a>'
        )
    _integ_html += '</div>'
    st.markdown(_integ_html, unsafe_allow_html=True)


elif st.session_state.page == "campaigns":

    st.markdown(
        '<div class="section-dark">'
        '<div style="position:relative;z-index:1;">'
        '<div class="section-eyebrow"><span class="drop">◆</span> LIVE</div>'
        '<h2 class="section-h">Active Campaigns</h2>'
        '<p class="section-sub">Real-time opportunities in the Pharos ecosystem. Join, build, and earn.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # Campaign cards — large news-feed rows: cover art on the left,
    # tag/title/summary/CTA on the right. Same component language as the
    # Updates feed, so both sections read consistently and scan easily.
    all_camp_html = '<div class="nf-list">'
    for c in CAMPAIGNS:
        _clogo = c.get("logo", "")
        _cover = (
            f'<img src="{esc_url(_clogo)}" loading="lazy" decoding="async" alt="" '
            f'class="nf-logo" onerror="this.style.display=\'none\';'
            f'this.parentNode.querySelector(\'.nf-emoji\').style.display=\'flex\';"/>'
            if _clogo else ''
        )
        all_camp_html += (
            f'<a class="nf-item" href="{esc_url(c["link"])}" target="_blank" rel="noopener">'
            f'<div class="nf-thumb nf-thumb-camp" style="background:{c["bg"]};">'
            f'{_cover}'
            f'<span class="nf-emoji"' + (' style="display:none;"' if _clogo else '') + f'>{c["icon"]}</span>'
            f'</div>'
            f'<div class="nf-body">'
            f'<div class="nf-meta">'
            f'<span class="nf-cat">{esc(c["tag"].strip())}</span>'
            f'<span class="nf-src">Pharos ecosystem</span>'
            f'</div>'
            f'<div class="nf-title">{esc(c["title"])}</div>'
            f'<div class="nf-summ">{esc(c["desc"])}</div>'
            f'<div class="nf-cta">{esc(c["cta"])} ↗</div>'
            f'</div></a>'
        )
    all_camp_html += '</div>'
    st.markdown(all_camp_html, unsafe_allow_html=True)

    # Hackathon timeline
    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div style="background:#FFFFFF;border:1px solid #E3E5EA;border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:0.8rem;">'
        '<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:700;color:#14141F;margin-bottom:0.8rem;">AI Agent Carnival — Phase Timeline</div>'
        '<div style="display:flex;flex-direction:column;gap:8px;">'
        '<div style="display:flex;align-items:flex-start;gap:10px;">'
        '<div style="width:60px;flex-shrink:0;font-size:10px;color:#1A1AFF;font-weight:700;padding-top:1px;">Pre-Season ✓</div>'
        '<div style="width:2px;background:#E3E5EA;flex-shrink:0;margin-top:4px;min-height:100%;"></div>'
        '<div><div style="font-size:12px;font-weight:600;color:#14141F;">May 25 – Jun 8</div>'
        '<div style="font-size:11px;color:#5B5F6E;">Discord Skill building warm-up · 5,000 PROS for 10 winners</div></div>'
        '</div>'
        '<div style="display:flex;align-items:flex-start;gap:10px;">'
        '<div style="width:60px;flex-shrink:0;font-size:10px;color:#1A1AFF;font-weight:700;padding-top:1px;">Phase 1 ✓</div>'
        '<div style="width:2px;background:#1A1AFF;flex-shrink:0;margin-top:4px;min-height:100%;"></div>'
        '<div><div style="font-size:12px;font-weight:600;color:#14141F;">Jun 8 – 22</div>'
        '<div style="font-size:11px;color:#5B5F6E;">Skill Hackathon · 20,000 PROS · Submit by Jun 15 · Judging Jun 16–22</div></div>'
        '</div>'
        '<div style="display:flex;align-items:flex-start;gap:10px;">'
        '<div style="width:60px;flex-shrink:0;font-size:10px;color:#9499A8;font-weight:600;padding-top:1px;">Phase 2</div>'
        '<div style="width:2px;background:#E3E5EA;flex-shrink:0;margin-top:4px;min-height:100%;"></div>'
        '<div><div style="font-size:12px;font-weight:600;color:#14141F;">Jun 22 – Jul 24</div>'
        '<div style="font-size:11px;color:#5B5F6E;">Agent Arena · 25,000 PROS · Phase 1 winners only · Submit by Jul 6</div></div>'
        '</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("Submit Agents here ↗", "https://dorahacks.io/hackathon/pharos-phase1", use_container_width=True)
    with col2:
        st.link_button("Join Pharos Discord ↗", PHAROS_DISCORD_URL, use_container_width=True)


# ═════════════════════════════════════════════
# PAGE: UPDATES (Pharos News)
# ═════════════════════════════════════════════
elif st.session_state.page == "updates":

    st.markdown(
        '<div class="section-dark">'
        '<div style="position:relative;z-index:1;">'
        '<div class="section-eyebrow"><span style="font-size:12px;">📋</span>&nbsp;PHAROS NEWS</div>'
        '<h2 class="section-h">Active Updates</h2>'
        '<p class="section-sub">Direct from <a href="' + PHAROS_X_URL + '" target="_blank">@pharos_network</a>. '
        'Live feed of the latest official posts — announcements, ecosystem launches, partnerships, campaigns and protocol updates. Refreshes automatically.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Live updates from the official Pharos Network X account ──
    # Same card grid + timeline design as before, now driven by real
    # posts (text, timestamp, media, direct link). Rendered inside a
    # fragment (where supported) so the feed re-fetches on a schedule
    # without a full page rerun — users always see the newest posts.
    def _render_x_feed():
        posts = get_pharos_x_posts()
        _live = st.session_state.get("pharos_x_cache", {}).get("live", False)

        st.markdown(
            '<div style="display:flex;align-items:center;gap:7px;font-size:11px;'
            'color:#9499A8;margin-bottom:0.6rem;">'
            + ('<span style="width:7px;height:7px;border-radius:50%;background:#22C55E;'
               'display:inline-block;box-shadow:0 0 0 3px rgba(34,197,94,0.18);"></span>'
               'Live from <b>@pharos_network</b> · refreshes automatically'
               if _live else
               '<span style="width:7px;height:7px;border-radius:50%;background:#F59E0B;'
               'display:inline-block;"></span>'
               'Live feed temporarily unreachable — showing the latest known official updates')
            + '</div>',
            unsafe_allow_html=True,
        )

        # ── News-feed layout ──────────────────────────────
        # Large, scannable rows: prominent cover image, title, summary
        # and metadata. Collapses to a stacked card on mobile.
        _feed = '<div class="nf-list">'
        for _n in posts[:8]:
            _text = (_n.get("text") or "").strip()
            # First sentence/line becomes the headline; the rest is summary.
            _parts = re.split(r"(?<=[.!?])\s+|\n+", _text, maxsplit=1)
            _title = (_parts[0] or _text)[:120]
            _summ  = (_parts[1].strip() if len(_parts) > 1 else "")[:200]
            _link  = esc_url(_n.get("url", PHAROS_X_URL))
            _media = _n.get("media") or ""
            _rel   = esc(_n.get("rel") or "")
            # Category inferred from the post's own words — no invention.
            _tl = _text.lower()
            if   any(k in _tl for k in ("partner", "collab")):        _cat = "Partnership"
            elif any(k in _tl for k in ("launch", "live", "mainnet")): _cat = "Launch"
            elif any(k in _tl for k in ("campaign", "quest", "reward", "expedition")): _cat = "Campaign"
            elif any(k in _tl for k in ("upgrade", "protocol", "release")): _cat = "Protocol"
            elif any(k in _tl for k in ("incubator", "ecosystem")):   _cat = "Ecosystem"
            else:                                                     _cat = "Announcement"

            _thumb = (
                f'<img src="{esc_url(_media)}" loading="lazy" decoding="async" alt="" '
                f'onerror="this.onerror=null;this.src=\'{esc_url(PHAROS_X_AVATAR)}\';"/>'
                if _media else
                f'<img src="{esc_url(PHAROS_X_AVATAR)}" loading="lazy" decoding="async" alt=""/>'
            )
            _feed += (
                f'<a class="nf-item" href="{_link}" target="_blank" rel="noopener">'
                f'<div class="nf-thumb">{_thumb}</div>'
                f'<div class="nf-body">'
                f'<div class="nf-meta">'
                f'<span class="nf-cat">{esc(_cat)}</span>'
                f'<span class="nf-src">@pharos_network</span>'
                + (f'<span class="nf-dot">·</span><span class="nf-time">{_rel}</span>' if _rel else '')
                + '</div>'
                f'<div class="nf-title">{esc(_title)}</div>'
                + (f'<div class="nf-summ">{esc(_summ)}</div>' if _summ else '')
                + '<div class="nf-cta">View post on X ↗</div>'
                '</div></a>'
            )
        _feed += '</div>'
        st.markdown(_feed, unsafe_allow_html=True)

    # Periodic auto-refresh where the Streamlit runtime supports
    # fragments; otherwise the short feed cache refreshes on rerun.
    if hasattr(st, "fragment"):
        _render_x_feed = st.fragment(run_every=X_FEED_CACHE)(_render_x_feed)
    _render_x_feed()

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("Follow @pharos_network on X ↗", PHAROS_X_URL, use_container_width=True)
    with col2:
        if st.button("🔄 Refresh feed", key="refresh_news"):
            st.session_state.pop("pharos_x_cache", None)
            st.rerun()


# ═════════════════════════════════════════════
# PAGE: TRADE
# ═════════════════════════════════════════════
elif st.session_state.page == "trade":
    st.markdown(
        '<div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:#14141F;margin-bottom:0.3rem;">📊 Trade $PROS</div>'
        '<div style="font-size:13px;color:#5B5F6E;margin-bottom:1.2rem;">Available on multiple CEX platforms. Choose your preferred exchange to trade PROS/USDT.</div>',
        unsafe_allow_html=True,
        )

    # Live price bar
    p = price_data
    if p.get("available") and p.get("price_usd"):
        chg = p.get("change_24h") or 0
        chg_cls = "green" if chg >= 0 else "red"
        st.markdown(f'''
<div class="price-ticker" style="margin-bottom:1.2rem;">
    <div class="ticker-cell"><div class="ticker-label">$PROS Price</div>
        <div class="ticker-value">${p["price_usd"]:.4f}</div></div>
    <div class="ticker-cell"><div class="ticker-label">24h Change</div>
        <div class="ticker-value {chg_cls}">{'▲' if chg>=0 else '▼'}{abs(chg):.2f}%</div></div>
    <div class="ticker-cell"><div class="ticker-label">Market Cap</div>
        <div class="ticker-value">{('$' + f'{p["market_cap_usd"]:,.0f}') if p.get('market_cap_usd') else '—'}</div></div>
    <div class="ticker-cell"><div class="ticker-label">24h Volume</div>
        <div class="ticker-value">{('$' + f'{p["volume_24h"]:,.0f}') if p.get('volume_24h') else '—'}</div></div>
</div>
<div class="ticker-source">CoinGecko · Updated {p.get('last_updated','—')}</div>
''', unsafe_allow_html=True)

    # Chart
    with st.container(border=True):
        RANGE_OPTIONS = {"1D":"1","7D":"7","30D":"30","90D":"90","1Y":"365","All":"max"}
        RANGE_LABELS  = {"1":"24H","7":"7D","30":"30D","90":"90D","365":"1Y","max":"ALL"}
        if "trade_chart_range" not in st.session_state:
            st.session_state["trade_chart_range"] = "1"

        lc, bc = st.columns([2, 4])
        with lc:
            st.markdown(
                '<div class="chart-card-label">$PROS · ' + RANGE_LABELS.get(st.session_state["trade_chart_range"],"24H") + ' PRICE</div>',
                unsafe_allow_html=True,
            )
        with bc:
            rcols = st.columns(len(RANGE_OPTIONS))
            for (rl, dv), rc in zip(RANGE_OPTIONS.items(), rcols):
                is_a = st.session_state["trade_chart_range"] == dv
                if rc.button(("● " if is_a else "") + rl, key="tr_rng_" + dv, use_container_width=True):
                    st.session_state["trade_chart_range"] = dv; st.rerun()

        sd = st.session_state["trade_chart_range"]
        if "trade_chart_loaded" not in st.session_state:
            st.session_state["trade_chart_loaded"] = False
        if not st.session_state["trade_chart_loaded"]:
            if st.button("📈 Load chart", key="tr_load"):
                st.session_state["trade_chart_loaded"] = True; st.rerun()
        else:
            render_price_chart(get_price_chart_df(days=sd), chart_key="trade_chart_" + sd, days=sd)

    # CEX grid
    st.markdown(
        '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:700;color:#14141F;margin:1rem 0 0.6rem 0;">Trade on CEX</div>',
        unsafe_allow_html=True,
    )
    cex_cols = st.columns(len(CEX_LINKS))
    for i, cex in enumerate(CEX_LINKS):
        with cex_cols[i]:
            logo_html = (
                f'<img src="{cex["logo"]}" alt="{cex["name"]}" width="32" height="32" '
                f'style="border-radius:8px;margin-bottom:6px;box-shadow:0 2px 8px rgba(20,20,60,0.1);" '
                f'onerror="this.outerHTML=\'<div style=&quot;width:32px;height:32px;border-radius:8px;'
                f'background:linear-gradient(135deg,#1414E8,#0C0C1A);display:flex;align-items:center;'
                f'justify-content:center;font-size:14px;font-weight:800;color:#fff;margin:0 auto 6px auto;&quot;>'
                f'{cex["name"][0]}</div>\'"/>'
            )
            st.markdown(
                '<div class="cex-card">'
                + logo_html +
                '<div class="cex-name">' + cex["name"] + '</div>'
                '<div class="cex-pair">' + cex["desc"] + '</div>'
                '<a class="cex-btn" href="' + cex["url"] + '" target="_blank">Trade ↗</a>'
                '</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div style="font-size:13px;font-weight:600;color:#B94A48;margin-top:0.8rem;padding:0.6rem 0.8rem;'
'background:#FFF6F6;border-radius:8px;border:1px solid #E8CACA;">'
'⚠ Trading involves risk. Prices are indicative. Always verify on the exchange before trading. '
'OctoBot is not a financial advisor.</div>',
        unsafe_allow_html=True,
        
    )


# ═════════════════════════════════════════════
# PAGE: ECOSYSTEM (DApps)
# ═════════════════════════════════════════════
elif st.session_state.page == "ecosystem":

    st.markdown(
        '<div class="dapp-section-hdr">'
        '<div style="position:relative;z-index:1;">'
        '<div style="display:inline-flex;align-items:center;gap:6px;font-size:9px;font-weight:700;'
        'letter-spacing:0.15em;text-transform:uppercase;color:#64BFFF;margin-bottom:0.6rem;">'
        '🧩 PHAROS ECOSYSTEM</div>'
        '<h2 style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:#FFFFFF;'
        'letter-spacing:-0.02em;margin:0 0 0.5rem 0;">DApps on Pharos</h2>'
        '<p style="font-size:0.9rem;color:rgba(255,255,255,0.55);line-height:1.5;max-width:520px;margin:0 auto;">'
        'Explore the full suite of decentralised applications building on Pharos — '
        'DeFi, RWA, bridges, NFTs, prediction markets and more.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # Category filter pills
    all_cats = sorted(set(t for d in PHAROS_DAPPS for t in d["cat"]))
    if "dapp_filter" not in st.session_state:
        st.session_state["dapp_filter"] = "All"

    filter_cols = st.columns(min(len(all_cats) + 1, 9))
    with filter_cols[0]:
        if st.button("All", key="df_all", use_container_width=True):
            st.session_state["dapp_filter"] = "All"; st.rerun()
    for fi, cat in enumerate(all_cats[:8]):
        with filter_cols[fi + 1]:
            if st.button(cat, key="df_" + cat, use_container_width=True):
                st.session_state["dapp_filter"] = cat; st.rerun()

    active_filter = st.session_state["dapp_filter"]
    filtered_dapps = (
        PHAROS_DAPPS if active_filter == "All"
        else [d for d in PHAROS_DAPPS if active_filter in d["cat"]]
    )

    # DApp grid — all cards in ONE st.markdown call so CSS grid works
    cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px;margin-bottom:1.4rem;">'
    for dapp in filtered_dapps:
        tags_html = "".join(
            f'<span class="eco-tag">{t}</span>'
            for t in dapp["cat"]
        )
        logo_html = (
            f'<img src="{dapp["logo"]}" width="48" height="48" '
            f'style="border-radius:50%;object-fit:cover;background:{dapp.get("bg","#EEF0FF")};'
            f'border:1px solid #ECEEF4;" '
            f'onerror="this.outerHTML=\'<div style=&quot;width:48px;height:48px;border-radius:50%;'
            f'background:{dapp.get("bg","#EEF0FF")};display:flex;align-items:center;'
            f'justify-content:center;font-size:22px;&quot;></div>\'"/>'
        )
        cards_html += (
            f'<a href="{dapp["url"]}" target="_blank" class="eco-card hover-lift">'
            f'<div style="margin-bottom:0.75rem;">{logo_html}</div>'
            f'<div class="eco-name">{dapp["name"]}</div>'
            f'<div class="eco-desc">{dapp["desc"]}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px;justify-content:center;">{tags_html}</div>'
            f'</a>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    st.link_button(
        "View all dApps on Pharos Testnet ↗",
        "https://testnet.pharosnetwork.xyz",
        use_container_width=False,
    )




# ═════════════════════════════════════════════
# PAGE: OCTOBOT PAYMENT AGENT
# ═════════════════════════════════════════════
elif st.session_state.page == "pay":

    inject_redesign_css("pay rd-hero-compact")

    # ════════════════════════════════════════════════════════
    # HELPERS — intent parsers
    # ════════════════════════════════════════════════════════

    def _classify_intent(text: str) -> str:
        """Return: 'send' | 'batch' | 'approve'"""
        t = text.lower()
        # batch: multiple addresses in the text
        addrs = re.findall(r"0x[0-9a-fA-F]{40}", text)
        if len(addrs) >= 2:
            return "batch"
        if any(w in t for w in ["approve", "allow", "authorise", "authorize", "permission", "spend"]):
            return "approve"
        return "send"

    def _parse_gemini(text: str, intent: str) -> dict | None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return None
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1,
                                          google_api_key=api_key)
            if intent == "batch":
                prompt = (
                    "Extract a batch payment intent from the following message.\n"
                    "Return ONLY valid JSON, no markdown:\n"
                    '{"recipients":["0x...","0x..."],"amount_each":1.0,"reason":""}\n\n'
                    "Rules:\n"
                    "- recipients: list of ALL valid 0x Ethereum addresses found.\n"
                    "- amount_each: the amount to send TO EACH address (positive number).\n"
                    "- reason: short description or empty string.\n\n"
                    f"Message: {text}"
                )
            elif intent == "approve":
                prompt = (
                    "Extract a token approval intent from the following message.\n"
                    "Return ONLY valid JSON, no markdown:\n"
                    '{"spender":"0x...","amount":100.0,"reason":""}\n\n'
                    "Rules:\n"
                    "- spender: the contract address being approved (0x, 42 chars). If none found, use null.\n"
                    "- amount: the amount to approve (positive number). If 'unlimited' or 'max', use -1.\n"
                    "- reason: short description or empty string.\n\n"
                    f"Message: {text}"
                )
            else:
                prompt = (
                    "Extract the payment intent from the following message.\n"
                    "Return ONLY valid JSON, no markdown:\n"
                    '{"recipient":"0x...","amount":1.5,"reason":""}\n\n'
                    "Rules:\n"
                    "- recipient: valid Ethereum address (0x, 42 chars). null if none.\n"
                    "- amount: positive number. null if none.\n"
                    "- reason: short description or empty string.\n\n"
                    f"Message: {text}"
                )
            resp = llm.invoke([HumanMessage(content=prompt)])
            raw  = resp.content.strip()
            raw  = re.sub(r"^```(?:json)?\n?", "", raw, flags=re.IGNORECASE)
            raw  = re.sub(r"\n?```$", "", raw)
            return json.loads(raw)
        except Exception:
            return None

    def _parse_regex(text: str, intent: str) -> dict | None:
        addrs  = re.findall(r"0x[0-9a-fA-F]{40}", text)
        amt_m  = re.search(r"(\d+(?:\.\d+)?)", text)
        reason = ""
        rm     = re.search(r"(?:for|reason[:\s]+)([\w\s]+)", text, re.IGNORECASE)
        if rm:
            reason = rm.group(1).strip()
        if intent == "batch" and len(addrs) >= 2 and amt_m:
            return {"recipients": addrs, "amount_each": float(amt_m.group(1)), "reason": reason}
        if intent == "approve" and addrs and amt_m:
            return {"spender": addrs[0], "amount": float(amt_m.group(1)), "reason": reason}
        if intent == "send" and addrs and amt_m:
            return {"recipient": addrs[0], "amount": float(amt_m.group(1)), "reason": reason}
        return None

    def _pay_net_config(network: str) -> dict:
        if network == "testnet":
            return {
                "label":        "Pharos Atlantic",
                "chain_id":     PHAROS_TESTNET_CHAIN_ID_HEX,
                "rpc":          PHAROS_TESTNET_RPC_URL,
                "explorer":     PHAROS_TESTNET_EXPLORER_URL,
                "chain_id_dec": PHAROS_TESTNET_CHAIN_ID_DEC,
                "symbol":       "PHRS",
            }
        return {
            "label":        "Pharos Mainnet",
            "chain_id":     PHAROS_CHAIN_ID_HEX,
            "rpc":          PHAROS_RPC_URL,
            "explorer":     PHAROS_EXPLORER_URL,
            "chain_id_dec": PHAROS_CHAIN_ID_DEC,
            "symbol":       "PROS",
        }

    def _tx_widget(chain_id, chain_name, rpc_url, explorer, net_symbol,
                   recipient, amount_hex, pay_net_ss,
                   amount_display, mode="send",
                   recipients_json="[]", approve_amount_hex="0x0", spender=""):
        """Render the components.html transaction widget for any tx type."""
        # ── Security: constrain every value that gets interpolated into the
        # signing JavaScript to a strict, breakout-proof shape. Legitimate
        # values (addresses, hex amounts, chain ids) already match these.
        _hex_re  = re.compile(r"^0x[0-9a-fA-F]+$")

        def _safe_hex(h, default="0x0"):
            h = str(h or "")
            return h if _hex_re.match(h) else default

        def _safe_num(n):
            try:
                return str(float(n))
            except (TypeError, ValueError):
                return "0"

        recipient          = valid_addr(recipient) or ""
        spender            = valid_addr(spender) or ""
        amount_hex         = _safe_hex(amount_hex)
        approve_amount_hex = _safe_hex(approve_amount_hex)
        chain_id           = chain_id if _hex_re.match(str(chain_id or "")) else ""
        amount_display     = _safe_num(amount_display)
        pay_net_ss         = pay_net_ss if pay_net_ss in ("mainnet", "testnet") else "mainnet"
        mode               = mode if mode in ("send", "batch", "approve") else "send"
        explorer           = esc_url(explorer)

        # recipients_json may be a JSON list of addresses — keep only valid ones
        try:
            _rlist = json.loads(recipients_json) if recipients_json else []
            _rlist = [a for a in _rlist if valid_addr(a)]
        except Exception:
            _rlist = []
        recipients_json = json.dumps(_rlist)

        # For non-batch modes the destination must be a valid address.
        if mode != "batch" and not recipient and not (mode == "approve" and spender):
            st.error("Invalid recipient address — transaction aborted.")
            return

        _tid = hashlib.md5(f"{recipient}{amount_hex}{chain_id}{mode}".encode()).hexdigest()[:8]

        if mode == "batch":
            js_send_block = f"""
    // BATCH SEND — fire one tx per recipient in sequence
    var recipients = {recipients_json};
    var txHashes   = [];
    for (var bi = 0; bi < recipients.length; bi++) {{
      status('⏳ Sending tx ' + (bi+1) + ' of ' + recipients.length + '…', '#5B5F6E', '#F5C842');
      var bHash = await provider.request({{
        method: 'eth_sendTransaction',
        params: [{{ from: accounts[0], to: recipients[bi],
                    value: '{amount_hex}', gas: '0x5208', chainId: '{chain_id}' }}]
      }});
      txHashes.push(bHash);
    }}
    var txHash = txHashes.join(',');
    var resHtml = '🎉 Batch complete! ' + txHashes.length + ' transactions sent.<br>';
    txHashes.forEach(function(h, i) {{
      resHtml += '<a href="{explorer}/tx/' + h + '" target="_blank" style="color:#1A1AFF;font-weight:600;font-size:11px;">Tx ' + (i+1) + ' ↗</a>&nbsp; ';
    }});
    res.innerHTML = resHtml;
"""
        elif mode == "approve":
            # ERC-20 approve(address spender, uint256 amount) selector = 0x095ea7b3
            js_send_block = f"""
    // APPROVE — encode approve(spender, amount) calldata
    var spender = '{spender}';
    var approveHex = '{approve_amount_hex}';
    // ABI encode: 4-byte selector + 32-byte padded spender + 32-byte padded amount
    var sel = '095ea7b3';
    var paddedSpender = spender.replace('0x','').toLowerCase().padStart(64,'0');
    var paddedAmount  = approveHex.replace('0x','').toLowerCase().padStart(64,'0');
    var data = '0x' + sel + paddedSpender + paddedAmount;
    status('⏳ Waiting for approval signature…', '#5B5F6E', '#F5C842');
    var txHash = await provider.request({{
      method: 'eth_sendTransaction',
      params: [{{ from: accounts[0], to: '{recipient}',
                  value: '0x0', data: data, gas: '0xF424', chainId: '{chain_id}' }}]
    }});
    res.innerHTML = '✅ Approval granted!<br><strong>Spender:</strong> {spender}<br>' +
      '🎉 <strong>Tx Hash:</strong> ' + txHash + '<br>' +
      '<a href="{explorer}/tx/' + txHash + '" target="_blank" style="color:#1A1AFF;font-weight:600;">View on Pharosscan ↗</a>';
"""
        else:
            js_send_block = f"""
    // STANDARD SEND
    status('⏳ Waiting for your signature in the wallet popup…', '#5B5F6E', '#F5C842');
    var txHash = await provider.request({{
      method: 'eth_sendTransaction',
      params: [{{ from: accounts[0], to: '{recipient}',
                  value: '{amount_hex}', gas: '0x5208', chainId: '{chain_id}' }}]
    }});
    res.innerHTML = '🎉 <strong>Tx Hash:</strong> ' + txHash + '<br>' +
      '<a href="{explorer}/tx/' + txHash + '" target="_blank" style="color:#1A1AFF;font-weight:600;">View on Pharosscan ↗</a>';
"""

        html = f"""<!DOCTYPE html>
<html><head>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;font-family:'DM Sans',sans-serif;}}
  body{{background:transparent;overflow:hidden;padding:8px 0;}}
  #status-box{{display:flex;align-items:center;gap:10px;background:#F4F5FF;border-radius:10px;
    padding:10px 14px;font-size:13px;color:#5B5F6E;min-height:42px;}}
  #dot{{width:9px;height:9px;border-radius:50%;background:#9499A8;flex-shrink:0;transition:background 0.3s;}}
  #msg{{flex:1;line-height:1.4;}}
  #tx-result{{display:none;margin-top:8px;background:#F0FFF4;border:1.5px solid #22C55E;
    border-radius:10px;padding:10px 14px;font-size:12px;color:#15803D;word-break:break-all;line-height:1.8;}}
</style>
</head><body>
<div id="status-box"><div id="dot"></div><div id="msg">⏳ Starting…</div></div>
<div id="tx-result"></div>
<script>
(async function() {{
  var dot = document.getElementById('dot');
  var msg = document.getElementById('msg');
  var res = document.getElementById('tx-result');
  function status(text, color, dotColor) {{
    msg.textContent = text; msg.style.color = color||'#5B5F6E';
    dot.style.background = dotColor||'#9499A8';
  }}
  function resolveProvider() {{
    if (typeof window.ethereum !== 'undefined')        return window.ethereum;
    if (typeof window.okxwallet !== 'undefined')       return window.okxwallet;
    try {{ if (typeof window.parent.ethereum !== 'undefined')  return window.parent.ethereum; }} catch(e) {{}}
    try {{ if (typeof window.parent.okxwallet !== 'undefined') return window.parent.okxwallet; }} catch(e) {{}}
    try {{ if (typeof window.top.ethereum !== 'undefined')     return window.top.ethereum; }} catch(e) {{}}
    try {{ if (typeof window.top.okxwallet !== 'undefined')    return window.top.okxwallet; }} catch(e) {{}}
    return null;
  }}
  status('⏳ Looking for wallet…', '#5B5F6E', '#F5C842');
  var provider = null;
  for (var i=0; i<15; i++) {{
    provider = resolveProvider();
    if (provider) break;
    await new Promise(function(r){{ setTimeout(r,100); }});
  }}
  if (!provider) {{
    status('❌ No Web3 wallet found. Unlock your wallet extension and try again.','#B91C1C','#E5484D');
    return;
  }}
  try {{
    status('⏳ Requesting account access…','#5B5F6E','#F5C842');
    var accounts = await provider.request({{method:'eth_requestAccounts'}});
    if (!accounts||accounts.length===0) {{
      status('❌ No accounts returned. Unlock your wallet.','#B91C1C','#E5484D'); return;
    }}
    status('⏳ Switching to {chain_name}…','#5B5F6E','#F5C842');
    try {{
      await provider.request({{method:'wallet_switchEthereumChain',params:[{{chainId:'{chain_id}'}}]}});
    }} catch(swErr) {{
      if (swErr.code===4902||swErr.code===-32603) {{
        status('⏳ Adding {chain_name} to your wallet…','#5B5F6E','#F5C842');
        await provider.request({{method:'wallet_addEthereumChain',params:[{{
          chainId:'{chain_id}',chainName:'{chain_name}',
          nativeCurrency:{{name:'{net_symbol}',symbol:'{net_symbol}',decimals:18}},
          rpcUrls:['{rpc_url}'],blockExplorerUrls:['{explorer}']
        }}]}});
        await provider.request({{method:'wallet_switchEthereumChain',params:[{{chainId:'{chain_id}'}}]}});
      }} else {{ throw swErr; }}
    }}
    {js_send_block}
    status('✅ Done!','#15803D','#22C55E');
    res.style.display='block';
    setTimeout(function(){{
      try {{
        var target=window.parent||window.top||window;
        var url=new URL(target.location.href);
        url.searchParams.set('pay_tx', typeof txHash!=='undefined'?txHash:'batch');
        url.searchParams.set('pay_to', '{recipient}');
        url.searchParams.set('pay_amt','{amount_display}');
        url.searchParams.set('pay_net','{pay_net_ss}');
        url.searchParams.set('pay_mode','{mode}');
        target.history.pushState({{}},'',url.toString());
        target.location.reload();
      }} catch(e) {{}}
    }},2200);
  }} catch(err) {{
    if (err.code===4001) {{ status('❌ Rejected — you cancelled in the wallet.','#B91C1C','#E5484D'); }}
    else {{ status('❌ '+( err.message||JSON.stringify(err)),'#B91C1C','#E5484D'); }}
  }}
}})();
</script></body></html>"""
        components.html(html, height=140, scrolling=False)

    # ════════════════════════════════════════════════════════
    # PAGE HEADER
    # ════════════════════════════════════════════════════════
    st.markdown(
        '<div style="background:linear-gradient(135deg,#0A2A0A 0%,#145214 100%);'
        'border-radius:20px;padding:2.2rem 2.4rem 1.8rem 2.4rem;margin-bottom:1.4rem;'
        'box-shadow:0 8px 32px rgba(10,60,20,0.2);position:relative;overflow:hidden;">'
        '<div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,0.06) 1px,transparent 1px);background-size:16px 16px;pointer-events:none;"></div>'
        '<div style="position:relative;z-index:1;">'
        '<div style="display:inline-flex;align-items:center;gap:6px;font-size:9px;font-weight:700;'
        'letter-spacing:0.15em;text-transform:uppercase;color:#8BFFB0;margin-bottom:0.7rem;">'
        '💸 PAYMENT AGENT · PHAROS NETWORK</div>'
        '<h2 style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:#FFFFFF;'
        'letter-spacing:-0.02em;margin:0 0 0.5rem 0;">Send PROS with Plain English</h2>'
        '<p style="font-size:0.92rem;color:rgba(255,255,255,0.6);line-height:1.55;max-width:620px;margin:0;">'
        'Send tokens, batch-pay multiple addresses, or approve a contract — just describe what you want '
        'and OctoBot builds the transaction. Nothing moves without your wallet signature.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Slim network toolbar ──────────────────────
    st.markdown('<div class="rd-toolbarrow"></div>', unsafe_allow_html=True)
    tb_lbl, tb_n1, tb_n2, tb_badge = st.columns([0.7, 0.9, 0.9, 2.2])
    with tb_lbl:
        st.markdown('<div style="font-size:10px;font-weight:700;letter-spacing:0.08em;'
                    'text-transform:uppercase;color:#7A7F96;padding-top:0.7rem;">Network</div>',
                    unsafe_allow_html=True)
    with tb_n1:
        mainnet_active = st.session_state.pay_network == "mainnet"
        if st.button(("● " if mainnet_active else "") + "🌐 Mainnet", key="pay_net_mainnet",
                     use_container_width=True, type="primary" if mainnet_active else "secondary"):
            if st.session_state.pay_network != "mainnet":
                st.session_state.pay_network = "mainnet"
                st.session_state.pay_parsed  = None
                st.session_state.pay_result  = None
                st.rerun()
    with tb_n2:
        testnet_active = st.session_state.pay_network == "testnet"
        if st.button(("● " if testnet_active else "") + "🧪 Testnet", key="pay_net_testnet",
                     use_container_width=True, type="primary" if testnet_active else "secondary"):
            if st.session_state.pay_network != "testnet":
                st.session_state.pay_network = "testnet"
                st.session_state.pay_parsed  = None
                st.session_state.pay_result  = None
                st.session_state.wallet_data = None
                st.rerun()

    _net = _pay_net_config(st.session_state.pay_network)
    net_badge_color = "#1414E8" if st.session_state.pay_network == "mainnet" else "#166016"
    net_badge_bg    = "#EEF0FF" if st.session_state.pay_network == "mainnet" else "#F0FFF4"
    with tb_badge:
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:7px;background:{net_badge_bg};'
            f'border:1px solid {net_badge_color}33;border-radius:10px;padding:7px 12px;margin-top:0.35rem;'
            f'font-size:11.5px;font-weight:600;color:{net_badge_color};white-space:nowrap;overflow:hidden;'
            f'text-overflow:ellipsis;max-width:100%;">'
            f'{"🌐" if st.session_state.pay_network == "mainnet" else "🧪"} '
            f'{_net["label"]} · Chain {_net["chain_id_dec"]} · {_net.get("symbol","PROS")}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:0.4rem;"></div>', unsafe_allow_html=True)

    # ── Command center: prompt (left) + wallet rail (right) ──
    wallet_addr = st.session_state.get("wallet_address", "")
    cmd_col, side_col = st.columns([1.65, 1], gap="medium")

    # ----- RIGHT: compact wallet side panel + utilities -----
    with side_col:
        with st.container(border=True):
            if not wallet_addr:
                st.markdown(
                    '<div style="padding:0.4rem 0.5rem 0.2rem 0.6rem;">'
                    '<span class="rd-eyebrow">🔑 Wallet</span>'
                    '<div class="rd-panel-title" style="font-size:14px;color:#000000;">Connect wallet</div>'
                    '<div class="rd-panel-sub" style="color:#000000;">Paste your address — read-only, no signing.</div></div>',
                    unsafe_allow_html=True,
                )
                _pwi = st.text_input("Your wallet address", placeholder="0x1234…your Pharos address",
                                     key="pay_inline_wallet_input", label_visibility="collapsed")
                if st.button("🔗 Connect Wallet", key="pay_inline_wallet_btn",
                             use_container_width=True, type="primary"):
                    if valid_addr(_pwi):
                        st.session_state.wallet_address = _pwi.strip()
                        st.session_state.wallet_data    = None
                        st.session_state.wallet_profile = None
                        st.rerun()
                    else:
                        st.error("Enter a valid 0x… wallet address (42 characters).")
            else:
                _wa = wallet_addr; _ws = _wa[:6] + "…" + _wa[-4:]
                st.markdown(
                    '<div style="padding:0.4rem 0.5rem 0.2rem 0.6rem;">'
                    '<span class="rd-eyebrow">🔗 Connected</span>'
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'background:linear-gradient(90deg,#0C0C1A,#1414E8);'
                    f'border-radius:12px;padding:0.65rem 0.9rem;margin:0.2rem 0 0.2rem 0;">'
                    f'<span style="font-size:15px;">👛</span><div style="min-width:0;">'
                    f'<div style="font-size:9px;color:rgba(255,255,255,0.5);font-weight:600;'
                    f'letter-spacing:0.07em;text-transform:uppercase;">Connected wallet</div>'
                    f'<div style="font-size:13px;color:#fff;font-weight:700;font-family:DM Mono,monospace;">{_ws}</div>'
                    f'</div></div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("✕ Disconnect", key="pay_disconnect_wallet", use_container_width=True):
                    st.session_state.wallet_address = ""
                    st.session_state.wallet_data    = None
                    st.session_state.wallet_profile = None
                    st.session_state.pay_parsed     = None
                    st.session_state.pay_result     = None
                    st.rerun()

            st.markdown('<hr class="rd-divider"/>', unsafe_allow_html=True)
            st.markdown('<div class="rd-util" style="margin-bottom:0.4rem;color:#FFFFFF;">🧰 Utilities</div>', unsafe_allow_html=True)
            if st.button("🧠 Memory Ledger", key="pay_go_memory", use_container_width=True):
                st.session_state.page = "memory"; st.rerun()
            st.markdown(
                '<div style="font-size:10.5px;color:#000000;line-height:1.5;margin-top:0.5rem;'
                'padding:0 0.3rem;">Describe a payment in plain English — Send, Batch, or Approve. '
                'Nothing moves without your signature.</div>',
                unsafe_allow_html=True,
            )

    # ----- LEFT: the AI command card (hero element of the page) -----
    EXAMPLE_PROMPTS = [
        ("➡️ Send",    "Send 10 PROS to 0xAbCd1234567890AbCd1234567890AbCd12345678"),
        ("📦 Batch",   "Send 1 PROS each to 0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA, 0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB, 0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"),
        ("✅ Approve", "Approve 0xFaroswap1111111111111111111111111111111111 to spend 100 PROS"),
    ]
    with cmd_col:
        with st.container(border=True):
            st.markdown(
                '<div class="rd-command" style="padding:0.5rem 0.7rem 0.2rem 0.7rem;">'
                '<span class="rd-eyebrow">🤖 AI Command</span>'
                '<div class="rd-panel-title" style="font-size:17px;">What payment can I build for you?</div>'
                '<div class="rd-panel-sub">Type an instruction in plain English, or start from an example.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
            # Example suggestion chips
            st.markdown('<div class="rd-chiprow"></div>', unsafe_allow_html=True)
            ep_cols = st.columns(3)
            for i, (ep_label, ep_text) in enumerate(EXAMPLE_PROMPTS):
                with ep_cols[i]:
                    if st.button(ep_label, key=f"pay_ep_{i}", use_container_width=True):
                        st.session_state.pay_intent_raw = ep_text
                        st.session_state.pay_parsed     = None
                        st.session_state.pay_confirmed  = False
                        st.session_state.pay_result     = None
                        st.rerun()

            pay_input = st.text_area(
                "Payment instruction in plain English",
                value=st.session_state.pay_intent_raw,
                placeholder='e.g. "Send 5 PROS to 0xAbCd…" or "Approve 0xContract to spend 100 PROS"',
                key="pay_text_input",
                label_visibility="collapsed",
                height=120,
            )
            parse_col, clear_col = st.columns([2, 1])
            with parse_col:
                parse_clicked = st.button("🔍 Parse Payment Intent", key="pay_parse_btn", use_container_width=True, type="primary")
            with clear_col:
                if st.button("✕ Clear", key="pay_clear_btn", use_container_width=True):
                    st.session_state.pay_intent_raw = ""
                    st.session_state.pay_parsed     = None
                    st.session_state.pay_confirmed  = False
                    st.session_state.pay_result     = None
                    st.rerun()

    if parse_clicked and pay_input.strip():
        st.session_state.pay_intent_raw = pay_input.strip()
        st.session_state.pay_confirmed  = False
        st.session_state.pay_result     = None
        with st.spinner("Parsing intent with AI…"):
            _intent = _classify_intent(pay_input.strip())
            parsed  = _parse_gemini(pay_input.strip(), _intent)
            if not parsed:
                parsed = _parse_regex(pay_input.strip(), _intent)
        if parsed:
            # Security: only trust addresses the user literally typed, and
            # validate amounts. Blocks prompt-injection from redirecting funds.
            _typed = set(re.findall(r"0x[0-9a-fA-F]{40}", pay_input))
            if parsed.get("recipient") and parsed["recipient"] not in _typed:
                parsed["recipient"] = None
            if parsed.get("spender") and parsed["spender"] not in _typed:
                parsed["spender"] = None
            if isinstance(parsed.get("recipients"), list):
                parsed["recipients"] = [a for a in parsed["recipients"] if a in _typed]
            parsed["_intent"] = _intent
            st.session_state.pay_parsed = parsed
        else:
            st.session_state.pay_parsed = None
            st.error('Could not parse intent. Try: "Send 5 PROS to 0x…" or "Approve 0x… to spend 100 PROS" or list multiple addresses for batch.')

    # ══════════════════════════════════════════════
    # CONFIRMATION CARDS (intent-aware)
    # ══════════════════════════════════════════════
    if st.session_state.pay_parsed and not st.session_state.pay_result:
        p_data  = st.session_state.pay_parsed
        _intent = p_data.get("_intent", "send")
        _sym    = _net.get("symbol", "PROS")

        price_info = get_pros_price()
        _pros_price = price_info.get("price_usd") if price_info.get("available") else None

        # ── Fetch sender balance ──────────────────
        sender_balance = None
        if wallet_addr:
            try:
                onchain = fetch_pharos_onchain_data(wallet_addr, rpc_override=_net["rpc"])
                if onchain.get("available"):
                    sender_balance = onchain.get("balance_pros")
            except Exception:
                pass
        if st.session_state.pay_network == "mainnet" and sender_balance is not None:
            if st.session_state.get("wallet_data") is None:
                st.session_state.wallet_data = {"available": True, "balance_pros": sender_balance}

        st.markdown('<div style="margin-top:1rem;"></div>', unsafe_allow_html=True)

        # ══════════════════════════
        # SEND — single recipient
        # ══════════════════════════
        if _intent == "send":
            recipient = p_data.get("recipient", "")
            amount    = float(p_data.get("amount", 0))
            reason    = p_data.get("reason", "")
            usd_val   = (amount * _pros_price) if _pros_price and st.session_state.pay_network == "mainnet" else None
            insufficient = sender_balance is not None and sender_balance < amount

            st.markdown(
                f'<div style="background:#FFFFFF;border:1.5px solid {"#E5484D" if insufficient else "#C8D0FF"};'
                'border-radius:16px;padding:1.4rem 1.6rem;box-shadow:0 4px 20px rgba(26,26,255,0.08);margin-bottom:1rem;">'
                '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#0C0C1A;'
                'margin-bottom:1rem;display:flex;align-items:center;gap:8px;"><span>📋</span> Transaction Preview · Send</div>'
                '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:0.9rem;">'
                '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Amount</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:18px;font-weight:800;color:#0C0C1A;">{amount:,.4f} {_sym}</div>'
                + (f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">≈ ${usd_val:,.4f} USD</div>' if usd_val else '') +
                '</div>'
                '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Network</div>'
                f'<div style="font-size:14px;font-weight:700;color:#0C0C1A;">{_net["label"]}</div>'
                f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">Chain ID {_net["chain_id_dec"]} · {_sym}</div>'
                '</div></div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:6px;">From</div>'
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{esc(wallet_addr) or "⚠️ Not connected"}</div>'
                + (f'<div style="font-size:11px;color:{"#E5484D" if insufficient else "#7A7F96"};margin-top:3px;">Balance: {sender_balance:,.4f} {_sym}' + (' — <strong style="color:#E5484D;">Insufficient</strong>' if insufficient else '') + '</div>' if sender_balance is not None else '') +
                '</div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:6px;">To</div>'
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{esc(recipient)}</div>'
                '</div>'
                + (f'<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                   f'<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Reason</div>'
                   f'<div style="font-size:12px;color:#0C0C1A;">{esc(reason)}</div></div>' if reason else '') +
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Estimated Gas</div>'
                '<div style="font-size:12px;color:#0C0C1A;">21,000 gas units</div>'
                '</div></div>',
                unsafe_allow_html=True,
            )
            if insufficient:
                st.markdown(f'<div style="background:#FFF0F0;border:1.5px solid #E5484D;border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.8rem;font-size:13px;font-weight:600;color:#B91C1C;">⚠️ Insufficient funds: balance {sender_balance:,.4f} {_sym} &lt; {amount:,.4f} {_sym}.</div>', unsafe_allow_html=True)
            if not wallet_addr:
                st.info("Connect your wallet above to proceed.")
            elif not insufficient:
                if st.button("✅ Confirm & Sign — Send", key="pay_confirm_btn", use_container_width=True, type="primary"):
                    _tx_widget(
                        chain_id=_net["chain_id"], chain_name=_net["label"],
                        rpc_url=_net["rpc"], explorer=_net["explorer"], net_symbol=_sym,
                        recipient=recipient, amount_hex=hex(int(amount * 1e18)),
                        pay_net_ss=st.session_state.pay_network,
                        amount_display=str(amount), mode="send",
                    )

        # ══════════════════════════
        # BATCH SEND
        # ══════════════════════════
        elif _intent == "batch":
            recipients   = p_data.get("recipients", [])
            amount_each  = float(p_data.get("amount_each", 0))
            reason       = p_data.get("reason", "")
            total_amount = amount_each * len(recipients)
            usd_each     = (amount_each * _pros_price) if _pros_price and st.session_state.pay_network == "mainnet" else None
            usd_total    = (total_amount * _pros_price) if _pros_price and st.session_state.pay_network == "mainnet" else None
            insufficient = sender_balance is not None and sender_balance < total_amount

            st.markdown(
                f'<div style="background:#FFFFFF;border:1.5px solid {"#E5484D" if insufficient else "#C7D2FE"};'
                'border-radius:16px;padding:1.4rem 1.6rem;box-shadow:0 4px 20px rgba(26,26,255,0.08);margin-bottom:1rem;">'
                '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#0C0C1A;'
                'margin-bottom:1rem;display:flex;align-items:center;gap:8px;"><span>📦</span> Transaction Preview · Batch Send</div>'
                '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:0.9rem;">'
                '<div style="background:#EEF0FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Each Address</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;color:#0C0C1A;">{amount_each:,.4f} {_sym}</div>'
                + (f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">≈ ${usd_each:,.4f}</div>' if usd_each else '') +
                '</div>'
                '<div style="background:#EEF0FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Recipients</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;color:#1414E8;">{len(recipients)}</div>'
                '</div>'
                '<div style="background:#EEF0FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Total</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;color:#0C0C1A;">{total_amount:,.4f} {_sym}</div>'
                + (f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">≈ ${usd_total:,.4f}</div>' if usd_total else '') +
                '</div></div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:6px;">From</div>'
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{esc(wallet_addr) or "⚠️ Not connected"}</div>'
                + (f'<div style="font-size:11px;color:{"#E5484D" if insufficient else "#7A7F96"};margin-top:3px;">Balance: {sender_balance:,.4f} {_sym}' + (' — <strong style="color:#E5484D;">Insufficient</strong>' if insufficient else '') + '</div>' if sender_balance is not None else '') +
                '</div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:8px;">Recipients</div>' +
                "".join([f'<div style="font-size:11.5px;font-weight:600;color:#0C0C1A;word-break:break-all;padding:4px 0;border-bottom:1px solid #ECEEF4;">'
                         f'<span style="color:#1414E8;font-weight:700;">{i+1}.</span> {esc(addr)} '
                         f'<span style="color:#7A7F96;">({amount_each:,.4f} {_sym})</span></div>'
                         for i, addr in enumerate(recipients)]) +
                '</div>'
                + (f'<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                   f'<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Reason</div>'
                   f'<div style="font-size:12px;color:#0C0C1A;">{esc(reason)}</div></div>' if reason else '') +
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Estimated Gas</div>'
                f'<div style="font-size:12px;color:#0C0C1A;">21,000 × {len(recipients)} = {21000*len(recipients):,} gas units ({len(recipients)} separate transactions)</div>'
                '</div></div>',
                unsafe_allow_html=True,
            )
            if insufficient:
                st.markdown(f'<div style="background:#FFF0F0;border:1.5px solid #E5484D;border-radius:10px;padding:0.75rem 1rem;margin-bottom:0.8rem;font-size:13px;font-weight:600;color:#B91C1C;">⚠️ Insufficient funds: balance {sender_balance:,.4f} {_sym} &lt; total {total_amount:,.4f} {_sym}.</div>', unsafe_allow_html=True)
            if not wallet_addr:
                st.info("Connect your wallet above to proceed.")
            elif not insufficient:
                if st.button(f"✅ Confirm & Sign — Send to {len(recipients)} addresses", key="pay_confirm_btn", use_container_width=True, type="primary"):
                    import json as _json
                    _tx_widget(
                        chain_id=_net["chain_id"], chain_name=_net["label"],
                        rpc_url=_net["rpc"], explorer=_net["explorer"], net_symbol=_sym,
                        recipient=recipients[0] if recipients else "",
                        amount_hex=hex(int(amount_each * 1e18)),
                        pay_net_ss=st.session_state.pay_network,
                        amount_display=str(amount_each),
                        mode="batch",
                        recipients_json=_json.dumps(recipients),
                    )

        # ══════════════════════════
        # APPROVE
        # ══════════════════════════
        elif _intent == "approve":
            spender      = p_data.get("spender", "")
            raw_amount   = p_data.get("amount", 0)
            reason       = p_data.get("reason", "")
            is_unlimited = raw_amount == -1
            approve_amt  = float(raw_amount) if not is_unlimited else 0
            # Max uint256 for unlimited approval
            MAX_UINT256  = 2**256 - 1
            approve_hex  = hex(MAX_UINT256) if is_unlimited else hex(int(approve_amt * 1e18))
            amt_display  = "Unlimited" if is_unlimited else f"{approve_amt:,.4f} {_sym}"

            st.markdown(
                '<div style="background:#FFFFFF;border:1.5px solid #FDE68A;'
                'border-radius:16px;padding:1.4rem 1.6rem;box-shadow:0 4px 20px rgba(250,200,0,0.08);margin-bottom:1rem;">'
                '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#0C0C1A;'
                'margin-bottom:1rem;display:flex;align-items:center;gap:8px;"><span>✅</span> Transaction Preview · Token Approval</div>'
                '<div style="background:#FFFBEB;border-radius:10px;padding:0.85rem 1rem;margin-bottom:0.9rem;'
                'border:1px solid #FDE68A;display:flex;align-items:flex-start;gap:8px;">'
                '<span style="font-size:16px;flex-shrink:0;">⚠️</span>'
                '<div style="font-size:12px;color:#7A5800;line-height:1.55;">'
                '<strong>Approval grants a contract permission to spend your tokens.</strong> '
                'Always verify the spender address before confirming. You can revoke approvals later.</div>'
                '</div>'
                '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:0.9rem;">'
                '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Allowance</div>'
                f'<div style="font-family:Syne,sans-serif;font-size:{"15" if is_unlimited else "18"}px;font-weight:800;color:{"#E5484D" if is_unlimited else "#0C0C1A"};">{amt_display}</div>'
                '</div>'
                '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Network</div>'
                f'<div style="font-size:14px;font-weight:700;color:#0C0C1A;">{_net["label"]}</div>'
                f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">Chain ID {_net["chain_id_dec"]}</div>'
                '</div></div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:6px;">Owner (Your Wallet)</div>'
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{esc(wallet_addr) or "⚠️ Not connected"}</div>'
                + (f'<div style="font-size:11px;color:#7A7F96;margin-top:3px;">Balance: {sender_balance:,.4f} {_sym}</div>' if sender_balance is not None else '') +
                '</div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:6px;">Spender (Contract being approved)</div>'
                f'<div style="font-size:12px;font-weight:600;color:#1414E8;word-break:break-all;">{esc(spender)}</div>'
                '</div>'
                + (f'<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                   f'<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Note</div>'
                   f'<div style="font-size:12px;color:#0C0C1A;">{esc(reason)}</div></div>' if reason else '') +
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Estimated Gas</div>'
                '<div style="font-size:12px;color:#0C0C1A;">~62,000 gas units (ERC-20 approve)</div>'
                '</div></div>',
                unsafe_allow_html=True,
            )
            if not wallet_addr:
                st.info("Connect your wallet above to proceed.")
            elif not spender:
                st.error("No valid spender contract address found. Try: \"Approve 0xContractAddress to spend 100 PROS\"")
            else:
                if st.button("✅ Confirm & Sign — Approve", key="pay_confirm_btn", use_container_width=True, type="primary"):
                    _tx_widget(
                        chain_id=_net["chain_id"], chain_name=_net["label"],
                        rpc_url=_net["rpc"], explorer=_net["explorer"], net_symbol=_sym,
                        recipient=spender,
                        amount_hex="0x0",
                        pay_net_ss=st.session_state.pay_network,
                        amount_display=str(approve_amt),
                        mode="approve",
                        approve_amount_hex=approve_hex,
                        spender=spender,
                    )

        if st.button("✕ Cancel", key="pay_cancel_btn", use_container_width=False):
            st.session_state.pay_parsed    = None
            st.session_state.pay_confirmed = False
            st.session_state.pay_result    = None
            st.rerun()

    # ── Handle tx hash returned via query param ───
    _pay_tx   = valid_txhash(st.query_params.get("pay_tx", "")) or ("batch" if st.query_params.get("pay_tx", "") == "batch" else "")
    _pay_to   = valid_addr(st.query_params.get("pay_to", "")) or ""
    _pay_amt  = valid_amount(st.query_params.get("pay_amt", ""))
    _pay_net  = st.query_params.get("pay_net", "mainnet")
    if _pay_net not in ("mainnet", "testnet"):
        _pay_net = "mainnet"
    _pay_mode = st.query_params.get("pay_mode", "send")
    if _pay_mode not in ("send", "batch", "approve"):
        _pay_mode = "send"
    if _pay_tx and _pay_to and _pay_amt is not None:
        try:
            amt_float = float(_pay_amt)
        except Exception:
            amt_float = 0.0
        _net_cfg = _pay_net_config(_pay_net)
        _mode_label = {"send": "Send", "batch": "Batch Send", "approve": "Approve"}.get(_pay_mode, "Send")
        entry = {
            "tx_hash":   _pay_tx,
            "recipient": _pay_to,
            "amount":    amt_float,
            "network":   _net_cfg["label"],
            "explorer":  _net_cfg["explorer"],
            "symbol":    _net_cfg.get("symbol", "PROS"),
            "mode":      _mode_label,
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        existing = [h.get("tx_hash") for h in st.session_state.pay_history]
        if _pay_tx not in existing:
            st.session_state.pay_history.insert(0, entry)
        st.session_state.pay_result    = entry
        st.session_state.pay_parsed    = None
        st.session_state.pay_confirmed = True
        st.query_params.clear()
        st.rerun()

    # ── Success card ─────────────────────────────
    if st.session_state.pay_result:
        r    = st.session_state.pay_result
        _exp = r.get("explorer", PHAROS_EXPLORER_URL)
        _sym = r.get("symbol", "PROS")
        _m   = r.get("mode", "Send")
        st.markdown(
            '<div style="background:#F0FFF4;border:1.5px solid #22C55E;border-radius:16px;'
            'padding:1.2rem 1.5rem;margin:1rem 0;box-shadow:0 4px 16px rgba(34,197,94,0.12);">'
            '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;color:#15803D;margin-bottom:0.5rem;">'
            f'🎉 {_m} Complete!</div>'
            f'<div style="font-size:12.5px;color:#166534;margin-bottom:4px;"><strong>Type:</strong> {_m}</div>'
            f'<div style="font-size:12.5px;color:#166534;margin-bottom:4px;"><strong>Amount:</strong> {r["amount"]:,.4f} {_sym}</div>'
            f'<div style="font-size:12.5px;color:#166534;margin-bottom:4px;"><strong>Address:</strong> {esc(r["recipient"])}</div>'
            f'<div style="font-size:12.5px;color:#166534;margin-bottom:4px;"><strong>Network:</strong> {esc(r.get("network","Pharos"))}</div>'
            f'<div style="font-size:12px;color:#15803D;word-break:break-all;margin-bottom:4px;"><strong>Tx Hash:</strong> {esc(r["tx_hash"])}</div>'
            f'<a href="{esc_url(_exp)}/tx/{esc(r["tx_hash"])}" target="_blank" rel="noopener noreferrer" '
            'style="display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;'
            'color:#1A1AFF;margin-top:4px;text-decoration:none;">View on Pharosscan ↗</a>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("💸 New Transaction", key="pay_again_btn"):
            st.session_state.pay_result     = None
            st.session_state.pay_parsed     = None
            st.session_state.pay_confirmed  = False
            st.session_state.pay_intent_raw = ""
            st.rerun()

    # ── Payment History ───────────────────────────
    if st.session_state.pay_history:
        st.markdown(
            '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;'
            'color:#0C0C1A;margin:1.5rem 0 0.6rem 0;">📜 Recent Transactions</div>',
            unsafe_allow_html=True,
        )
        for h in st.session_state.pay_history[:10]:
            tx_short = h["tx_hash"][:14] + "…" + h["tx_hash"][-8:]
            _h_exp   = h.get("explorer", PHAROS_EXPLORER_URL)
            _h_net   = h.get("network", "Pharos")
            _h_sym   = h.get("symbol", "PROS")
            _h_mode  = h.get("mode", "Send")
            _mode_icon = {"Send": "➡️", "Batch Send": "📦", "Approve": "✅"}.get(_h_mode, "➡️")
            st.markdown(
                '<div style="background:#FFFFFF;border:1px solid #ECEEF4;border-radius:12px;'
                'padding:0.75rem 1rem;margin-bottom:0.5rem;display:flex;align-items:center;'
                'justify-content:space-between;gap:12px;flex-wrap:wrap;">'
                f'<div><div style="font-size:13px;font-weight:700;color:#0C0C1A;">'
                f'{_mode_icon} {_h_mode} · {h["amount"]:,.4f} {_h_sym} → {esc(h["recipient"][:16])}…</div>'
                f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">{esc(h.get("timestamp",""))} · {esc(_h_net)} · {esc(tx_short)}</div></div>'
                f'<a href="{esc_url(_h_exp)}/tx/{esc(h["tx_hash"])}" target="_blank" rel="noopener noreferrer" '
                'style="font-size:11.5px;font-weight:600;color:#1A1AFF;white-space:nowrap;text-decoration:none;">View ↗</a>'
                '</div>',
                unsafe_allow_html=True,
            )



# ═════════════════════════════════════════════════════════════
# PAGE: REQUEST PROS  (on-chain payment requests / invoicing)
# ═════════════════════════════════════════════════════════════
elif st.session_state.page == "request":


    inject_redesign_css("request rd-hero-compact rd-wide")

    def _req_net_config(network: str) -> dict:
        if network == "testnet":
            return {
                "label":        "Pharos Atlantic",
                "chain_id":     PHAROS_TESTNET_CHAIN_ID_HEX,
                "rpc":          PHAROS_TESTNET_RPC_URL,
                "explorer":     PHAROS_TESTNET_EXPLORER_URL,
                "chain_id_dec": PHAROS_TESTNET_CHAIN_ID_DEC,
                "symbol":       "PHRS",
            }
        return {
            "label":        "Pharos Mainnet",
            "chain_id":     PHAROS_CHAIN_ID_HEX,
            "rpc":          PHAROS_RPC_URL,
            "explorer":     PHAROS_EXPLORER_URL,
            "chain_id_dec": PHAROS_CHAIN_ID_DEC,
            "symbol":       "PROS",
        }

    def _build_invoice_url(base_url: str, to: str, amount: str,
                           note: str, sender: str, network: str) -> str:
        params = {"req_to": to, "req_amt": amount,
                  "req_for": note, "req_from": sender, "req_net": network}
        return base_url.rstrip("/") + "/?" + urllib.parse.urlencode(params)

    def _pay_invoice_widget(chain_id, chain_name, rpc_url, explorer,
                            net_symbol, recipient, amount_hex, pay_net_ss, amount_display):
        # Security: constrain every value interpolated into the signing JS.
        _hex_re = re.compile(r"^0x[0-9a-fA-F]+$")
        recipient      = valid_addr(recipient) or ""
        amount_hex     = amount_hex if _hex_re.match(str(amount_hex or "")) else "0x0"
        chain_id       = chain_id if _hex_re.match(str(chain_id or "")) else ""
        pay_net_ss     = pay_net_ss if pay_net_ss in ("mainnet", "testnet") else "mainnet"
        explorer       = esc_url(explorer)
        rpc_url        = esc_url(rpc_url)
        try:
            amount_display = str(float(amount_display))
        except (TypeError, ValueError):
            amount_display = "0"
        if not recipient:
            st.error("Invalid recipient address — payment aborted.")
            return
        _tid = hashlib.md5(f"req{recipient}{amount_hex}{chain_id}".encode()).hexdigest()[:8]
        html = f"""<!DOCTYPE html>
<html><head>
<style>
  *{{margin:0;padding:0;box-sizing:border-box;font-family:'DM Sans',sans-serif;}}
  body{{background:transparent;overflow:hidden;padding:8px 0;}}
  #sb{{display:flex;align-items:center;gap:10px;background:#F4F5FF;border-radius:10px;
       padding:10px 14px;font-size:13px;color:#5B5F6E;min-height:42px;}}
  #dot{{width:9px;height:9px;border-radius:50%;background:#9499A8;flex-shrink:0;transition:background 0.3s;}}
  #msg{{flex:1;line-height:1.4;}}
  #res{{display:none;margin-top:8px;background:#F0FFF4;border:1.5px solid #22C55E;
        border-radius:10px;padding:10px 14px;font-size:12px;color:#15803D;
        word-break:break-all;line-height:1.8;}}
</style></head><body>
<div id="sb"><div id="dot"></div><div id="msg">⏳ Starting…</div></div>
<div id="res"></div>
<script>
(async function(){{
  var dot=document.getElementById('dot'),msg=document.getElementById('msg'),res=document.getElementById('res');
  function st(t,c,d){{msg.textContent=t;msg.style.color=c||'#5B5F6E';dot.style.background=d||'#9499A8';}}
  function rp(){{
    if(typeof window.ethereum!=='undefined') return window.ethereum;
    if(typeof window.okxwallet!=='undefined') return window.okxwallet;
    try{{if(typeof window.parent.ethereum!=='undefined') return window.parent.ethereum;}}catch(e){{}}
    try{{if(typeof window.parent.okxwallet!=='undefined') return window.parent.okxwallet;}}catch(e){{}}
    try{{if(typeof window.top.ethereum!=='undefined') return window.top.ethereum;}}catch(e){{}}
    return null;
  }}
  st('⏳ Looking for wallet…','#5B5F6E','#F5C842');
  var p=null;
  for(var i=0;i<15;i++){{p=rp();if(p)break;await new Promise(r=>setTimeout(r,100));}}
  if(!p){{st('❌ No Web3 wallet found. Unlock your wallet extension and try again.','#B91C1C','#E5484D');return;}}
  try{{
    st('⏳ Requesting account access…','#5B5F6E','#F5C842');
    var acc=await p.request({{method:'eth_requestAccounts'}});
    if(!acc||!acc.length){{st('❌ No accounts returned.','#B91C1C','#E5484D');return;}}
    st('⏳ Switching to {chain_name}…','#5B5F6E','#F5C842');
    try{{
      await p.request({{method:'wallet_switchEthereumChain',params:[{{chainId:'{chain_id}'}}]}});
    }}catch(sw){{
      if(sw.code===4902||sw.code===-32603){{
        await p.request({{method:'wallet_addEthereumChain',params:[{{
          chainId:'{chain_id}',chainName:'{chain_name}',
          nativeCurrency:{{name:'{net_symbol}',symbol:'{net_symbol}',decimals:18}},
          rpcUrls:['{rpc_url}'],blockExplorerUrls:['{explorer}']
        }}]}});
        await p.request({{method:'wallet_switchEthereumChain',params:[{{chainId:'{chain_id}'}}]}});
      }}else{{throw sw;}}
    }}
    st('⏳ Waiting for your signature…','#5B5F6E','#F5C842');
    var tx=await p.request({{method:'eth_sendTransaction',params:[{{
      from:acc[0],to:'{recipient}',value:'{amount_hex}',gas:'0x5208',chainId:'{chain_id}'
    }}]}});
    st('✅ Payment sent!','#15803D','#22C55E');
    res.style.display='block';
    res.innerHTML='🎉 <strong>Tx Hash:</strong> '+tx+'<br>'
      +'<a href="{explorer}/tx/'+tx+'" target="_blank" style="color:#1A1AFF;font-weight:600;">View on Pharosscan ↗</a>';
    setTimeout(function(){{
      try{{
        var tgt=window.parent||window.top||window;
        var url=new URL(tgt.location.href);
        url.searchParams.set('req_paid_tx',tx);
        url.searchParams.set('req_paid_to','{recipient}');
        url.searchParams.set('req_paid_amt','{amount_display}');
        url.searchParams.set('req_paid_net','{pay_net_ss}');
        tgt.history.pushState({{}},'',url.toString());
        tgt.location.reload();
      }}catch(e){{}}
    }},2200);
  }}catch(err){{
    if(err.code===4001){{st('❌ Rejected — you cancelled.','#B91C1C','#E5484D');}}
    else{{st('❌ '+(err.message||JSON.stringify(err)),'#B91C1C','#E5484D');}}
  }}
}})();
</script></body></html>"""
        components.html(html, height=140, scrolling=False)

    # ── Handle paid-invoice return from wallet ──
    _rpaid_tx  = valid_txhash(st.query_params.get("req_paid_tx", "")) or ""
    _rpaid_to  = valid_addr(st.query_params.get("req_paid_to", "")) or ""
    _rpaid_amt = valid_amount(st.query_params.get("req_paid_amt", ""))
    _rpaid_net = st.query_params.get("req_paid_net", "mainnet")
    if _rpaid_net not in ("mainnet", "testnet"):
        _rpaid_net = "mainnet"
    if _rpaid_tx and _rpaid_to:
        _rn_cfg = _req_net_config(_rpaid_net)
        _paid_entry = {
            "type":      "paid",
            "tx_hash":   _rpaid_tx,
            "to":        _rpaid_to,
            "amount":    str(_rpaid_amt) if _rpaid_amt is not None else "0",
            "network":   _rn_cfg["label"],
            "explorer":  _rn_cfg["explorer"],
            "symbol":    _rn_cfg.get("symbol", "PROS"),
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        existing = [e.get("tx_hash") for e in st.session_state.req_invoices]
        if _rpaid_tx not in existing:
            st.session_state.req_invoices.insert(0, _paid_entry)
        st.session_state.req_draft = {"mode": "paid_success", "entry": _paid_entry}
        st.query_params.clear()
        st.rerun()

    _draft = st.session_state.get("req_draft") or {}
    _mode  = _draft.get("mode", "create")
    wallet_addr = st.session_state.get("wallet_address", "")

    # ── Header ───────────────────────────────────
    _hdr_map = {
        "pay_invoice":  ("🧾", "You've Received a Payment Request",
                         "Review the invoice below and pay with one click — your wallet handles the rest."),
        "paid_success": ("🎉", "Payment Sent!", "The invoice has been paid on-chain."),
        "create":       ("🧾", "Request PROS",
                         "Create a payment request, generate a shareable link, and send it to whoever owes you — they open it and pay with one click."),
    }
    _hdr_icon, _hdr_title, _hdr_sub = _hdr_map.get(_mode, _hdr_map["create"])
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#0C0C1A 0%,#1414E8 100%);'
        f'border-radius:20px;padding:2.2rem 2.4rem 1.8rem 2.4rem;margin-bottom:1.4rem;'
        f'box-shadow:0 8px 32px rgba(20,20,90,0.22);position:relative;overflow:hidden;">'
        f'<div style="position:absolute;inset:0;background-image:radial-gradient(circle,rgba(255,255,255,0.05) 1px,transparent 1px);background-size:16px 16px;pointer-events:none;"></div>'
        f'<div style="position:relative;z-index:1;">'
        f'<div style="display:inline-flex;align-items:center;gap:6px;font-size:9px;font-weight:700;'
        f'letter-spacing:0.15em;text-transform:uppercase;color:#9FB4FF;margin-bottom:0.7rem;">'
        f'{_hdr_icon} REQUEST PROS · PHAROS NETWORK</div>'
        f'<h2 style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:#FFFFFF;'
        f'letter-spacing:-0.02em;margin:0 0 0.5rem 0;">{_hdr_title}</h2>'
        f'<p style="font-size:0.92rem;color:rgba(255,255,255,0.6);line-height:1.55;max-width:600px;margin:0;">'
        f'{_hdr_sub}</p></div></div>',
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════
    # MODE A — PAY INVOICE (recipient opened link)
    # ══════════════════════════════════════════════
    if _mode == "pay_invoice":
        inv_to    = _draft.get("to", "")
        inv_amt   = _draft.get("amount", "0")
        inv_note  = _draft.get("note", "")
        inv_from  = _draft.get("from", "")
        inv_net   = _draft.get("network", "mainnet")
        _n        = _req_net_config(inv_net)
        _sym      = _n.get("symbol", "PROS")
        try:
            inv_amt_f = float(inv_amt)
        except Exception:
            inv_amt_f = 0.0

        price_info = get_pros_price()
        usd_val    = None
        if price_info.get("available") and price_info.get("price_usd") and inv_net == "mainnet":
            usd_val = inv_amt_f * price_info["price_usd"]

        st.markdown(
            '<div style="background:#FFFFFF;border:2px solid #1414E8;border-radius:20px;'
            'padding:1.8rem 2rem;box-shadow:0 8px 32px rgba(26,26,255,0.10);'
            'max-width:680px;margin:0 auto 1.2rem auto;">'
            '<div style="display:flex;align-items:center;justify-content:space-between;'
            'margin-bottom:1.2rem;flex-wrap:wrap;gap:10px;">'
            '<div style="display:flex;align-items:center;gap:10px;">'
            '<div style="width:44px;height:44px;border-radius:12px;'
            'background:linear-gradient(135deg,#0C0C1A,#1414E8);'
            'display:flex;align-items:center;justify-content:center;font-size:22px;">🧾</div>'
            '<div><div style="font-family:Syne,sans-serif;font-size:16px;font-weight:800;color:#0C0C1A;">Invoice</div>'
            '<div style="font-size:11px;color:#7A7F96;">Powered by OctoBot · Pharos Network</div></div>'
            '</div>'
            f'<div style="background:#EEF0FF;border-radius:10px;padding:5px 14px;'
            f'font-size:12px;font-weight:700;color:#1414E8;">🌐 {_n["label"]}</div>'
            '</div>'
            '<div style="background:linear-gradient(135deg,#EEF0FF,#E4E8FF);'
            'border-radius:14px;padding:1.2rem 1.4rem;margin-bottom:1rem;text-align:center;">'
            '<div style="font-size:11px;font-weight:600;letter-spacing:0.08em;'
            'text-transform:uppercase;color:#7A7F96;margin-bottom:4px;">Amount Requested</div>'
            f'<div style="font-family:Syne,sans-serif;font-size:2.4rem;font-weight:800;'
            f'color:#0C0C1A;letter-spacing:-0.02em;">{inv_amt_f:,.4f} {_sym}</div>'
            + (f'<div style="font-size:13px;color:#7A7F96;margin-top:3px;">≈ ${usd_val:,.4f} USD</div>' if usd_val else '') +
            '</div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:0.9rem;">'
            + (
                '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:4px;">Requested by</div>'
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{inv_from}</div>'
                '</div>' if inv_from else ''
            ) +
            '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
            '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:4px;">Pay to</div>'
            f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{esc(inv_to)}</div>'
            '</div></div>'
            + (
                '<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;'
                'padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:4px;">Note / For</div>'
                f'<div style="font-size:13px;color:#0C0C1A;font-weight:500;">{inv_note}</div>'
                '</div>' if inv_note else ''
            ) +
            '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;">'
            '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Estimated Gas</div>'
            '<div style="font-size:12px;color:#0C0C1A;">21,000 gas units (standard transfer)</div>'
            '</div></div>',
            unsafe_allow_html=True,
        )

        if not wallet_addr:
            st.markdown(
                '<div style="background:#FFFFFF;border:1.5px solid rgba(26,26,255,0.2);'
                'border-radius:14px;padding:1.2rem 1.4rem;margin-bottom:0.9rem;">'
                '<div style="font-size:13px;font-weight:700;color:#0C0C1A;margin-bottom:0.5rem;">🔑 Connect your wallet to pay</div>'
                '<div style="font-size:12px;color:#FFFFFF;margin-bottom:0.8rem;">Paste your wallet address — read-only, no signing required just to connect.</div>',
                unsafe_allow_html=True,
            )
            _ri = st.text_input("Your wallet address", placeholder="0x…",
                                key="req_pay_wallet_input", label_visibility="collapsed")
            rw1, rw2 = st.columns([2, 1])
            with rw1:
                if st.button("🔗 Connect Wallet", key="req_pay_wallet_btn",
                             use_container_width=True, type="primary"):
                    if valid_addr(_ri):
                        st.session_state.wallet_address = _ri.strip()
                        st.rerun()
                    else:
                        st.error("Enter a valid 0x… address (42 chars).")
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            _wa = wallet_addr
            _ws = _wa[:6] + "…" + _wa[-4:]
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;'
                f'background:linear-gradient(90deg,#0C0C1A,#1414E8);'
                f'border-radius:12px;padding:0.7rem 1.1rem;margin-bottom:0.8rem;">'
                f'<span style="font-size:16px;">🔗</span><div>'
                f'<div style="font-size:9.5px;color:rgba(255,255,255,0.5);font-weight:600;'
                f'letter-spacing:0.07em;text-transform:uppercase;">Paying from</div>'
                f'<div style="font-size:13px;color:#fff;font-weight:700;font-family:monospace;">{_ws}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
            if st.button(
                f"✅ Pay {inv_amt_f:,.4f} {_sym} → {inv_to[:10]}…",
                key="req_pay_confirm_btn",
                use_container_width=True,
                type="primary",
            ):
                _pay_invoice_widget(
                    chain_id=_n["chain_id"], chain_name=_n["label"],
                    rpc_url=_n["rpc"], explorer=_n["explorer"], net_symbol=_sym,
                    recipient=inv_to, amount_hex=hex(int(inv_amt_f * 1e18)),
                    pay_net_ss=inv_net, amount_display=str(inv_amt_f),
                )

        if st.button("✕ Cancel / Close invoice", key="req_cancel_invoice"):
            st.session_state.req_draft = None
            st.rerun()

    # ══════════════════════════════════════════════
    # MODE B — PAID SUCCESS
    # ══════════════════════════════════════════════
    elif _mode == "paid_success":
        entry = _draft.get("entry", {})
        _exp  = entry.get("explorer", PHAROS_EXPLORER_URL)
        _sym  = entry.get("symbol", "PROS")
        st.markdown(
            '<div style="background:#F0FFF4;border:2px solid #22C55E;border-radius:16px;'
            'padding:1.5rem 1.8rem;margin-bottom:1.2rem;box-shadow:0 4px 20px rgba(34,197,94,0.12);">'
            '<div style="font-family:Syne,sans-serif;font-size:18px;font-weight:800;color:#15803D;margin-bottom:0.6rem;">🎉 Invoice Paid!</div>'
            f'<div style="font-size:13px;color:#166534;margin-bottom:4px;"><strong>Amount:</strong> {entry.get("amount","?")} {_sym}</div>'
            f'<div style="font-size:13px;color:#166534;margin-bottom:4px;"><strong>Paid to:</strong> {entry.get("to",entry.get("recipient","?"))}</div>'
            f'<div style="font-size:13px;color:#166534;margin-bottom:4px;"><strong>Network:</strong> {entry.get("network","Pharos")}</div>'
            f'<div style="font-size:12px;color:#15803D;word-break:break-all;margin-bottom:6px;"><strong>Tx Hash:</strong> {entry.get("tx_hash","?")}</div>'
            f'<a href="{_exp}/tx/{entry.get("tx_hash","")}" target="_blank" '
            'style="font-size:12px;font-weight:600;color:#1A1AFF;text-decoration:none;">View on Pharosscan ↗</a>'
            '</div>',
            unsafe_allow_html=True,
        )
        if st.button("🧾 Create a New Request", key="req_new_after_pay"):
            st.session_state.req_draft = None
            st.rerun()

    # ══════════════════════════════════════════════
    # MODE C — CREATE REQUEST (default)
    # ══════════════════════════════════════════════
    else:
        # ── Slim network toolbar ──────────────
        st.markdown('<div class="rd-toolbarrow"></div>', unsafe_allow_html=True)
        st.markdown('<span class="rd-tb-lbl" style="display:block;margin-bottom:4px;">Network</span>', unsafe_allow_html=True)
        rn1, rn2, rn_sp = st.columns([1, 1, 3])
        with rn1:
            _mn_active = st.session_state.pay_network == "mainnet"
            if st.button(("● " if _mn_active else "") + "🌐 Mainnet",
                         key="req_net_mainnet", use_container_width=True,
                         type="primary" if _mn_active else "secondary"):
                if not _mn_active:
                    st.session_state.pay_network = "mainnet"; st.rerun()
        with rn2:
            _tn_active = st.session_state.pay_network == "testnet"
            if st.button(("● " if _tn_active else "") + "🧪 Testnet",
                         key="req_net_testnet", use_container_width=True,
                         type="primary" if _tn_active else "secondary"):
                if not _tn_active:
                    st.session_state.pay_network = "testnet"; st.rerun()

        _rn   = _req_net_config(st.session_state.pay_network)
        _rsym = _rn.get("symbol", "PROS")
        nb_color = "#1414E8" if st.session_state.pay_network == "mainnet" else "#166016"
        nb_bg    = "#EEF0FF" if st.session_state.pay_network == "mainnet" else "#F0FFF4"
        st.markdown(
            f'<div style="display:inline-flex;align-items:center;gap:7px;background:{nb_bg};'
            f'border:1px solid {nb_color}33;border-radius:10px;padding:5px 12px;margin-bottom:0.8rem;'
            f'font-size:12px;font-weight:600;color:{nb_color};">'
            f'{"🌐" if st.session_state.pay_network=="mainnet" else "🧪"} '
            f'{_rn["label"]} · {_rsym} · Chain ID {_rn["chain_id_dec"]}</div>',
            unsafe_allow_html=True,
        )

        # ── Wallet setup (top of workspace) ───
        if not wallet_addr:
            st.markdown(
                '<div style="background:#FFFFFF;border:1.5px solid rgba(26,26,255,0.2);'
                'border-radius:14px;padding:1.2rem 1.4rem;margin-bottom:1rem;">'
                '<div style="font-size:13px;font-weight:700;color:#0C0C1A;margin-bottom:4px;">'
                '🔑 Your wallet address (where you will receive payment)</div>'
                '<div style="font-size:12px;color:#5B5F6E;margin-bottom:0.7rem;">'
                'Read-only — no signing, no extension needed.</div>',
                unsafe_allow_html=True,
            )
            _cwi = st.text_input("Your wallet address", placeholder="0x… your receiving address",
                                 key="req_create_wallet_input", label_visibility="collapsed")
            cw1, cw2 = st.columns([2, 1])
            with cw1:
                if st.button("🔗 Set My Address", key="req_create_wallet_btn",
                             use_container_width=True, type="primary"):
                    if valid_addr(_cwi):
                        st.session_state.wallet_address = _cwi.strip()
                        st.rerun()
                    else:
                        st.error("Enter a valid 0x… address (42 chars).")
            with cw2:
                if st.button("🧠 Memory Ledger", key="req_go_memory", use_container_width=True):
                    st.session_state.page = "memory"; st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            _wa  = wallet_addr
            _ws  = _wa[:6] + "…" + _wa[-4:]
            rcol1, rcol2 = st.columns([4, 1])
            with rcol1:
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px;'
                    f'background:linear-gradient(90deg,#0C0C1A,#1414E8);'
                    f'border-radius:12px;padding:0.7rem 1.1rem;margin-bottom:0.8rem;">'
                    f'<span style="font-size:16px;">🔗</span><div>'
                    f'<div style="font-size:9.5px;color:rgba(255,255,255,0.5);font-weight:600;'
                    f'letter-spacing:0.07em;text-transform:uppercase;">Receiving wallet</div>'
                    f'<div style="font-size:13px;color:#fff;font-weight:700;font-family:monospace;">{_ws}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
            with rcol2:
                if st.button("✕ Change", key="req_disconnect", use_container_width=True):
                    st.session_state.wallet_address = ""
                    st.rerun()

        # ── Workspace body: Request Card (left) + summary rail (right) ──
        form_col, sum_col = st.columns([1.5, 1], gap="medium")

        with form_col:
            with st.container(border=True):
                st.markdown(
                    '<div style="padding:0.4rem 0.6rem 0.2rem 0.7rem;">'
                    '<span class="rd-eyebrow">🧾 New request</span>'
                    '<div class="rd-panel-title">Create payment request</div>'
                    '<div class="rd-panel-sub">Fill in the details, then generate a shareable link.</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                fc1, fc2 = st.columns([1, 1])
                with fc1:
                    req_amount = st.text_input(f"Amount ({_rsym})", placeholder="e.g. 10", key="req_amount_input")
                with fc2:
                    st.text_input("Token", value=_rsym, disabled=True, key="req_token_display")
                req_payer = st.text_input("Payer wallet address (optional)",
                                          placeholder="0x… leave blank for anyone",
                                          key="req_payer_input")
                req_note = st.text_input("Note / What is this for?",
                                         placeholder='"Design work", "Hackathon bounty", "Invoice #001"',
                                         key="req_note_input")
                gen_clicked = st.button("🔗 Generate Payment Link", key="req_generate_btn",
                                        use_container_width=True, type="primary")

        with sum_col:
            with st.container(border=True):
                _amt_prev = (st.session_state.get("req_amount_input") or "").strip()
                _note_prev = (st.session_state.get("req_note_input") or "").strip()
                _to_prev = (wallet_addr[:6] + "…" + wallet_addr[-4:]) if wallet_addr else "Not set"
                st.markdown(
                    '<div style="padding:0.4rem 0.6rem 0.3rem 0.7rem;">'
                    '<span class="rd-eyebrow">👁 Summary</span>'
                    '<div class="rd-panel-title">Request summary</div>'
                    '<hr class="rd-divider"/>'
                    '<div style="display:flex;flex-direction:column;gap:0.7rem;">'
                    '<div><div style="font-size:10px;font-weight:700;letter-spacing:0.06em;'
                    'text-transform:uppercase;color:#FFFFFF;margin-bottom:2px;">Amount</div>'
                    f'<div style="font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;color:#0B1020;">'
                    f'{esc(_amt_prev) if _amt_prev else "—"} <span style="font-size:0.8rem;color:#68738C;">{_rsym}</span></div></div>'
                    '<div><div style="font-size:10px;font-weight:700;letter-spacing:0.06em;'
                    'text-transform:uppercase;color:#FFFFFF;margin-bottom:2px;">Receive to</div>'
                    f'<div style="font-family:DM Mono,monospace;font-size:12.5px;font-weight:600;color:#2B3656;">{esc(_to_prev)}</div></div>'
                    '<div><div style="font-size:10px;font-weight:700;letter-spacing:0.06em;'
                    'text-transform:uppercase;color:#FFFFFF;margin-bottom:2px;">Network</div>'
                    f'<div style="font-size:12.5px;font-weight:600;color:#2B3656;">{_rn["label"]}</div></div>'
                    + (f'<div><div style="font-size:10px;font-weight:700;letter-spacing:0.06em;'
                       f'text-transform:uppercase;color:#FFFFFF;margin-bottom:2px;">Note</div>'
                       f'<div style="font-size:12.5px;color:#2B3656;">{esc(_note_prev)}</div></div>' if _note_prev else '')
                    + '</div></div>',
                    unsafe_allow_html=True,
                )

        if gen_clicked:
            _err = None
            if not wallet_addr:
                _err = "Set your wallet address first — that's where the PROS will be sent."
            elif not req_amount.strip():
                _err = "Enter an amount."
            else:
                try:
                    _amt_f = float(req_amount.strip())
                    if _amt_f <= 0:
                        _err = "Amount must be greater than zero."
                except ValueError:
                    _err = "Amount must be a number."
            if _err:
                st.error(_err)
            else:
                _amt_f = float(req_amount.strip())
                _invoice = {
                    "type":      "created",
                    "to":        wallet_addr,
                    "amount":    str(_amt_f),
                    "note":      req_note.strip(),
                    "payer":     req_payer.strip(),
                    "network":   st.session_state.pay_network,
                    "net_label": _rn["label"],
                    "symbol":    _rsym,
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                }
                st.session_state.req_invoices.insert(0, _invoice)

                _base_url = "http://localhost:8501"
                try:
                    _base_url = st.context.headers.get("origin", _base_url)
                except Exception:
                    pass
                _link = _build_invoice_url(
                    base_url=_base_url, to=wallet_addr, amount=str(_amt_f),
                    note=req_note.strip(), sender=req_payer.strip(),
                    network=st.session_state.pay_network,
                )

                price_info = get_pros_price()
                usd_val    = None
                if price_info.get("available") and price_info.get("price_usd") and st.session_state.pay_network == "mainnet":
                    usd_val = _amt_f * price_info["price_usd"]

                # ── Generated request card (result) ──
                st.markdown('<div style="margin-top:1.1rem;"></div>', unsafe_allow_html=True)
                st.markdown(
                    '<div style="display:inline-flex;align-items:center;gap:7px;background:#F0FFF4;'
                    'border:1px solid #86EFAC;border-radius:999px;padding:4px 12px;font-size:11px;'
                    'font-weight:700;color:#15803D;margin-bottom:0.6rem;">✓ Request created · ready to share</div>',
                    unsafe_allow_html=True,
                )
                res_main, res_qr = st.columns([1.5, 1], gap="medium")

                with res_main:
                    st.markdown(
                        '<div style="background:#FFFFFF;border:2px solid #1414E8;border-radius:20px;'
                        'padding:1.5rem 1.7rem;box-shadow:0 8px 32px rgba(26,26,255,0.10);">'
                        '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;'
                        'color:#0C0C1A;margin-bottom:1rem;">🧾 Payment Request</div>'
                        '<div style="background:linear-gradient(135deg,#EEF0FF,#E4E8FF);'
                        'border-radius:14px;padding:1rem 1.2rem;margin-bottom:0.9rem;text-align:center;">'
                        '<div style="font-size:10px;font-weight:600;letter-spacing:0.08em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Amount</div>'
                        f'<div style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:#0C0C1A;">{_amt_f:,.4f} {_rsym}</div>'
                        + (f'<div style="font-size:12px;color:#7A7F96;margin-top:3px;">≈ ${usd_val:,.4f} USD</div>' if usd_val else '') +
                        '</div>'
                        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:0.9rem;">'
                        '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                        '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:4px;">Receive to</div>'
                        f'<div style="font-size:11.5px;font-weight:600;color:#0C0C1A;word-break:break-all;">{esc(wallet_addr)}</div>'
                        '</div>'
                        '<div style="background:#F4F5FF;border-radius:10px;padding:0.75rem 0.9rem;">'
                        '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:4px;">Network</div>'
                        f'<div style="font-size:13px;font-weight:700;color:#0C0C1A;">{_rn["label"]}</div>'
                        f'<div style="font-size:11px;color:#7A7F96;margin-top:1px;">Chain ID {_rn["chain_id_dec"]}</div>'
                        '</div></div>'
                        + (
                            '<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;'
                            'padding:0.75rem 0.9rem;">'
                            '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">For</div>'
                            f'<div style="font-size:13px;font-weight:500;color:#0C0C1A;">{esc(req_note.strip())}</div>'
                            '</div>' if req_note.strip() else ''
                        ) +
                        '</div>',
                        unsafe_allow_html=True,
                    )

                with res_qr:
                    st.markdown(
                        '<div style="text-align:center;margin-bottom:0.4rem;">'
                        '<div style="font-size:10px;font-weight:700;letter-spacing:0.07em;'
                        'text-transform:uppercase;color:#7A7F96;margin-bottom:0.5rem;">Scan to pay</div></div>',
                        unsafe_allow_html=True,
                    )
                    render_qr_code(_link, size=168, key="req_qr")

                st.markdown(
                    '<div style="background:#F0FFF4;border:1.5px solid #22C55E;border-radius:14px;'
                    'padding:1rem 1.2rem;margin:0.8rem 0 0.4rem 0;">'
                    '<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:700;'
                    'color:#15803D;margin-bottom:0.5rem;">🔗 Shareable Payment Link</div>'
                    '<div style="font-size:11px;color:#166534;margin-bottom:0.6rem;">'
                    'Send this link to the payer. They open it, see the invoice, and pay with one click.</div>'
                    f'<div style="background:#FFFFFF;border:1px solid #86EFAC;border-radius:8px;'
                    f'padding:8px 12px;font-size:11px;font-family:monospace;color:#0C0C1A;'
                    f'word-break:break-all;line-height:1.6;">{esc(_link)}</div>'
                    '</div>',
                    unsafe_allow_html=True,
                )
                st.code(_link, language=None)
                st.caption("👆 Copy the link above and send it via Telegram, Discord, or email.")


    # ── Invoice History ───────────────────────────
    if _mode == "create" and st.session_state.req_invoices:
        st.markdown(
            '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;'
            'color:#0C0C1A;margin:1.6rem 0 0.6rem 0;">📋 Invoice History</div>',
            unsafe_allow_html=True,
        )
        for _inv in st.session_state.req_invoices[:10]:
            _it    = _inv.get("type", "created")
            _i_sym = _inv.get("symbol", "PROS")
            _i_net = _inv.get("net_label", _inv.get("network", "Pharos"))
            _icon  = "🧾" if _it == "created" else "✅"
            _label = "Created" if _it == "created" else "Paid"
            _addr  = _inv.get("to", _inv.get("recipient", "?"))
            st.markdown(
                '<div style="background:#FFFFFF;border:1px solid #ECEEF4;border-radius:12px;'
                'padding:0.75rem 1rem;margin-bottom:0.5rem;display:flex;align-items:center;'
                'justify-content:space-between;gap:12px;flex-wrap:wrap;">'
                f'<div><div style="font-size:13px;font-weight:700;color:#0C0C1A;">'
                f'{_icon} {_label} · {esc(_inv.get("amount","?"))} {esc(_i_sym)}'
                + (f' · {esc(_inv.get("note",""))}' if _inv.get("note") else '') +
                f'</div>'
                f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">'
                f'{esc(_inv.get("timestamp",""))} · {esc(_i_net)} · {esc(_addr[:16])}…</div></div>'
                + (
                    f'<a href="{esc_url(_inv.get("explorer",PHAROS_EXPLORER_URL))}/tx/{esc(_inv.get("tx_hash",""))}" '
                    f'target="_blank" rel="noopener noreferrer" style="font-size:11.5px;font-weight:600;color:#1A1AFF;'
                    f'white-space:nowrap;text-decoration:none;">Tx ↗</a>'
                    if _it == "paid" and _inv.get("tx_hash") else ''
                ) +
                '</div>',
                unsafe_allow_html=True,
            )




# ═════════════════════════════════════════════
# PAGE: NETWORK DASHBOARD
# ═════════════════════════════════════════════
elif st.session_state.page == "network":

    inject_redesign_css("network rd-hero-compact rd-wide")

    # ── Live RPC stats fetcher ────────────────
    def _fetch_net_stats() -> dict:
        now    = time.time()
        cached = st.session_state.get("net_stats_cache", {})
        if cached and now - cached.get("fetched_at", 0) < 15:
            return cached
        res = {"available": False, "fetched_at": now,
               "block_number": None, "block_time_s": None,
               "tx_count": None, "gas_price_gwei": None,
               "chain_id": None, "peer_count": None, "error": None}
        def rpc(method, params=None):
            r = requests.post(PHAROS_RPC_URL,
                json={"jsonrpc":"2.0","id":1,"method":method,"params":params or []},
                timeout=6, headers={"Content-Type":"application/json"})
            r.raise_for_status()
            d = r.json()
            if "error" in d: raise ValueError(d["error"])
            return d.get("result")
        try:
            bn_hex = rpc("eth_blockNumber")
            bn = int(bn_hex, 16)
            res["block_number"] = bn
            blk = rpc("eth_getBlockByNumber", [bn_hex, False])
            if blk:
                res["tx_count"] = len(blk.get("transactions", []))
                ts = int(blk.get("timestamp","0x0"), 16)
                par = rpc("eth_getBlockByNumber", [hex(bn-1), False])
                if par:
                    res["block_time_s"] = max(0, ts - int(par.get("timestamp","0x0"), 16))
            gp = rpc("eth_gasPrice")
            if gp: res["gas_price_gwei"] = round(int(gp, 16) / 1e9, 6)
            cid = rpc("eth_chainId")
            if cid: res["chain_id"] = int(cid, 16)
            try:
                pc = rpc("net_peerCount")
                if pc: res["peer_count"] = int(pc, 16)
            except Exception:
                pass
            res["available"] = True
        except Exception as e:
            res["error"] = str(e)
        st.session_state["net_stats_cache"] = res
        return res

    # ── Header ────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#0C0C1A 0%,#0A1A6E 100%);'
        'border-radius:20px;padding:2rem 2.4rem 1.6rem 2.4rem;margin-bottom:1.4rem;'
        'box-shadow:0 8px 32px rgba(10,26,110,0.28);position:relative;overflow:hidden;">'
        '<div style="position:absolute;inset:0;background-image:radial-gradient(circle,'
        'rgba(255,255,255,0.05) 1px,transparent 1px);background-size:18px 18px;pointer-events:none;"></div>'
        '<div style="position:relative;z-index:1;">'
        '<div style="font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;'
        'color:rgba(255,255,255,0.5);margin-bottom:0.6rem;">🌐 PHAROS NETWORK · LIVE STATS</div>'
        '<h2 style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:#FFFFFF;'
        'letter-spacing:-0.02em;margin:0 0 0.5rem 0;">Network Dashboard</h2>'
        '<p style="font-size:0.9rem;color:rgba(255,255,255,0.55);line-height:1.55;max-width:560px;margin:0;">'
        'Live Pharos mainnet stats fetched directly from the RPC — block height, block time, '
        'gas price and more. Auto-refreshes every 15 seconds.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Refresh controls (integrated with hero, right-aligned) ──
    rc_sp, rc1, rc2 = st.columns([5, 1.5, 1.6])
    with rc1:
        if st.button("🔄 Refresh", key="net_refresh", use_container_width=True, type="primary"):
            st.session_state["net_stats_cache"] = {}
            st.rerun()
    with rc2:
        st.markdown('<div style="font-size:11px;color:#39445D;padding:0.7rem 0;text-align:left;">🟢 Live · auto 15s</div>',
                    unsafe_allow_html=True)

    ns = _fetch_net_stats()

    if not ns["available"]:
        st.markdown(
            f'<div style="background:#FFF0F0;border:1.5px solid #E5484D;border-radius:14px;'
            f'padding:1rem 1.4rem;font-size:13px;color:#B91C1C;margin-bottom:1rem;">'
            f'⚠️ RPC unreachable: {ns.get("error","Unknown error")}</div>',
            unsafe_allow_html=True,
        )
    else:
        bts  = f'{ns["block_time_s"]}s'  if ns["block_time_s"]     is not None else "—"
        gwei = f'{ns["gas_price_gwei"]} Gwei' if ns["gas_price_gwei"] is not None else "—"
        blkn = f'{ns["block_number"]:,}' if ns["block_number"]      is not None else "—"
        txct = str(ns["tx_count"])        if ns["tx_count"]          is not None else "—"
        cid  = str(ns["chain_id"])        if ns["chain_id"]          is not None else "—"
        pc   = str(ns["peer_count"])      if ns["peer_count"]        is not None else "N/A"

        def _stat_tile(label, value, sub, icon, c, bg):
          return (
               f'<div class="rd-stat" style="margin-bottom:18px;">'
               f'<div class="rd-stat-top">'
               f'<div class="rd-stat-ic" style="background:{bg};">{icon}</div>'
               f'<div class="rd-stat-lbl">{label}</div></div>'
               f'<div class="rd-stat-val" style="color:{c};">{value}</div>'
               f'<div class="rd-stat-sub">{sub}</div></div>'
    )

        _tiles = [
            _stat_tile("Block Height", blkn, "Latest confirmed block",          "📦", "#1414E8", "#EEF0FF"),
            _stat_tile("Block Time",   bts,  "Between last two blocks",          "⏱️", "#166016", "#F0FFF4"),
            _stat_tile("Txs in Block", txct, "Transactions in latest block",     "📋", "#7A5800", "#FFFBEB"),
            _stat_tile("Gas Price",    gwei, "Current network gas price",        "⛽", "#5B2D8C", "#F3EEFF"),
            _stat_tile("Chain ID",     cid,  "Pacific Mainnet identifier",       "🔗", "#0C6E8A", "#E8F8FF"),
            _stat_tile("Peer Count",   pc,   "Connected RPC peers",              "🤝", "#B94A00", "#FFF4EE"),
        ]
        # Large responsive metrics grid — two rows of three equal tiles.
        for _row in (0, 3):
            mc = st.columns(3, gap="large")
            for _i, _col in enumerate(mc):
                with _col:
                    st.markdown(_tiles[_row + _i], unsafe_allow_html=True)
        st.markdown('<div style="height:0.6rem;"></div>', unsafe_allow_html=True)

    # ── Featured Mainnet status card + Available Networks (side by side) ──
    st.markdown('<div style="height:0.8rem;"></div>', unsafe_allow_html=True)
    feat_col, side_col = st.columns([1.45, 1], gap="large")

    with feat_col:
        with st.container(border=True):
            st.markdown(
                '<div style="padding:0.4rem 0.5rem 0.2rem 0.7rem;">'
                '<span class="rd-eyebrow">⭐ Featured · Mainnet</span>'
                '<div class="rd-panel-title">Pharos Pacific Mainnet</div>'
                '<div class="rd-panel-sub">Primary production network · live and online.</div>'
                '<hr class="rd-divider"/>'
                '<div style="display:grid;grid-template-columns:repeat(2,1fr);gap:12px 18px;">'
                + "".join([
                    f'<div style="min-width:0;"><div style="font-size:10px;font-weight:700;letter-spacing:0.07em;'
                    f'text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">{k}</div>'
                    f'<div style="font-size:13px;font-weight:600;color:#0B1020;word-break:break-all;'
                    f'font-family:{"DM Mono,monospace" if "RPC" in k else "Inter,sans-serif"};">{v}</div></div>'
                    for k, v in [
                        ("Chain ID", str(PHAROS_CHAIN_ID_DEC)),
                        ("Symbol",   "PROS"),
                        ("RPC URL",  PHAROS_RPC_URL),
                        ("Status",   "🟢 Online"),
                    ]
                ])
                + '</div><hr class="rd-divider"/>'
                '<div style="display:flex;gap:10px;flex-wrap:wrap;padding-bottom:0.3rem;margin-top:-9px;margin-left:-6px;">'
                f'<a href="{PHAROS_EXPLORER_URL}" target="_blank" '
                f'style="display:inline-flex;align-items:center;gap:6px;background:#0C0C1A;color:#FFFFFF;'
                f'border-radius:10px;padding:0.55rem 1.1rem;font-size:12.5px;font-weight:700;text-decoration:none;">'
                f'🔍 Explorer ↗</a>'
                f'<a href="{PHAROS_DOCS_URL}" target="_blank" '
                f'style="display:inline-flex;align-items:center;gap:6px;background:#EEF0FF;color:#1414E8;'
                f'border-radius:10px;padding:0.55rem 1.1rem;font-size:12.5px;font-weight:700;text-decoration:none;">'
                f'📖 Documentation ↗</a>'
                '</div></div>',
                unsafe_allow_html=True,
            )

    with side_col:
        with st.container(border=True):
            st.markdown(
                '<div style="padding:0.4rem 0.5rem 0.2rem 0.7rem;">'
                '<span class="rd-eyebrow">🧪 Available · Testnet</span>'
                '<div class="rd-panel-title">Pharos Atlantic</div>'
                '<div class="rd-panel-sub">Public testnet for development.</div>'
                '<hr class="rd-divider"/>'
                '<div style="display:grid;grid-template-columns:1fr;gap:10px;">'
                + "".join([
                    f'<div style="min-width:0;"><div style="font-size:10px;font-weight:700;letter-spacing:0.07em;'
                    f'text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">{k}</div>'
                    f'<div style="font-size:13px;font-weight:600;color:#0B1020;word-break:break-all;'
                    f'font-family:{"DM Mono,monospace" if "RPC" in k else "Inter,sans-serif"};">{v}</div></div>'
                    for k, v in [
                        ("Chain ID", str(PHAROS_TESTNET_CHAIN_ID_DEC)),
                        ("Symbol",   "PHRS"),
                        ("RPC URL",  PHAROS_TESTNET_RPC_URL),
                        ("Status",   "🟢 Online"),
                    ]
                ])
                + '</div><hr class="rd-divider"/>'
                f'<a href="{PHAROS_TESTNET_EXPLORER_URL}" target="_blank" '
                f'style="display:inline-flex;align-items:center;gap:6px;background:#0C0C1A;color:#FFFFFF;'
                f'border-radius:10px;padding:0.55rem 1.1rem;font-size:12.5px;font-weight:700;'
                f'text-decoration:none;margin-left:-18px;margin-top:-20px;">'
                f'🔍 Explorer ↗</a>'
                '</div>',
                unsafe_allow_html=True,
            )




# ═════════════════════════════════════════════
# PAGE: SPN EXPLORER
# ═════════════════════════════════════════════
elif st.session_state.page == "spns":

    inject_redesign_css("spns rd-hero-compact rd-wide")

    # ── SPN data — sourced strictly from official Pharos docs and pharos.xyz ──
    # Source: https://docs.pharos.xyz (About Pharos, SPN docs)
    # Source: https://www.pharos.xyz (homepage SPN section)
    # Only confirmed use cases: HFT, ZKML, AI models, AIoT, privacy computation,
    # RWA/compliance, PayFi. No invented specs, no unconfirmed names.
    PHAROS_SPNS = [
        {
            "name":     "High-Frequency Trading (HFT)",
            "emoji":    "📈",
            "category": "Finance",
            "color":    "#1414E8",
            "bg":       "linear-gradient(135deg,#EEF0FF,#E4E8FF)",
            "tagbg":    "rgba(26,26,255,0.08)",
            "tagcol":   "#1414E8",
            "desc":     (
                "SPNs can be configured as dedicated execution environments for high-frequency "
                "trading applications. The SPN runs semi-independently with its own execution engine "
                "and validator set, removing shared congestion from the main chain for latency-sensitive workloads."
            ),
            "features": [
                "Custom execution engine per SPN",
                "Independent validator set",
                "Cross-SPN interoperability",
                "Shared security via restaking",
            ],
            "source":   "pharos.xyz — L1-Extension, SPN use cases",
        },
        {
            "name":     "AI & ZKML",
            "emoji":    "🤖",
            "category": "AI",
            "color":    "#7A5800",
            "bg":       "linear-gradient(135deg,#FFF8E8,#FFF0CC)",
            "tagbg":    "rgba(122,88,0,0.08)",
            "tagcol":   "#7A5800",
            "desc":     (
                "SPNs support running AI models and zero-knowledge machine learning (ZKML) workloads "
                "on-chain. Lightweight SPNs can be configured with access to specialised hardware "
                "such as TEEs for secure AI inference and confidential computation."
            ),
            "features": [
                "Specialised hardware support (TEE)",
                "ZKML execution environments",
                "Non-blockchain application support",
                "Decentralised Data Exchange Protocol",
            ],
            "source":   "docs.pharos.xyz — About Pharos, L1-Extension",
        },
        {
            "name":     "AIoT & Private Networks",
            "emoji":    "📡",
            "category": "IoT / Privacy",
            "color":    "#1A6B5A",
            "bg":       "linear-gradient(135deg,#E8FFF8,#D0F5EC)",
            "tagbg":    "rgba(26,107,90,0.08)",
            "tagcol":   "#1A6B5A",
            "desc":     (
                "SPNs are explicitly designed to support AIoT (AI + IoT) private networks and "
                "multi-party privacy-enhancing computations. Validators can create dedicated SPNs "
                "using their excess compute power for these specialised environments."
            ),
            "features": [
                "AIoT private network support",
                "Multi-party privacy computation",
                "Lightweight SPN configuration",
                "Validator restaking incentives",
            ],
            "source":   "docs.pharos.xyz — Pharos SPNs (confirmed use case)",
        },
        {
            "name":     "RWA & Compliance (PayFi)",
            "emoji":    "🏦",
            "category": "Finance / RWA",
            "color":    "#166016",
            "bg":       "linear-gradient(135deg,#F0FFF4,#E0F8E8)",
            "tagbg":    "rgba(22,96,22,0.08)",
            "tagcol":   "#166016",
            "desc":     (
                "Pharos SPNs support financial innovations including RWA tokenisation and PayFi. "
                "The protocol includes integrated ZK-KYC and AML modules at the protocol layer, "
                "enabling compliance-ready SPNs for regulated finance while preserving composability."
            ),
            "features": [
                "Built-in ZK-KYC / AML modules",
                "Programmable compliance hooks",
                "Cross-SPN asset transfers",
                "PayFi and monthly payment support",
            ],
            "source":   "pharos.xyz homepage + docs.pharos.xyz SPN vision",
        },
        {
            "name":     "MEV Optimisation",
            "emoji":    "⚡",
            "category": "Infra",
            "color":    "#5B2D8C",
            "bg":       "linear-gradient(135deg,#F3EEFF,#EAE0FF)",
            "tagbg":    "rgba(91,45,140,0.08)",
            "tagcol":   "#5B2D8C",
            "desc":     (
                "Lightweight SPNs can be configured with access to specialised hardware for "
                "MEV (Maximal Extractable Value) optimisation. This is one of the confirmed SPN "
                "hardware-acceleration use cases from the official Pharos documentation."
            ),
            "features": [
                "Specialised hardware access",
                "TEE for transaction confidentiality",
                "Configurable consensus per SPN",
                "SPN Manager for lifecycle control",
            ],
            "source":   "docs.pharos.xyz — Pharos SPNs (lightweight SPN hardware use cases)",
        },
    ]

    # ── Hero (compacted via CSS) ──────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#0A0A28 0%,#1414E8 100%);'
        'border-radius:20px;padding:2rem 2.4rem 1.6rem 2.4rem;margin-bottom:1.4rem;'
        'box-shadow:0 8px 32px rgba(20,20,232,0.25);position:relative;overflow:hidden;">'
        '<div style="position:absolute;inset:0;background-image:radial-gradient(circle,'
        'rgba(255,255,255,0.06) 1px,transparent 1px);background-size:16px 16px;pointer-events:none;"></div>'
        '<div style="position:relative;z-index:1;">'
        '<div style="font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;'
        'color:rgba(255,255,255,0.5);margin-bottom:0.6rem;">⚡ SPECIAL PROCESSING NETWORKS · PHAROS</div>'
        '<h2 style="font-family:Syne,sans-serif;font-size:2rem;font-weight:800;color:#FFFFFF;'
        'letter-spacing:-0.02em;margin:0 0 0.5rem 0;">SPN Explorer</h2>'
        '<p style="font-size:0.9rem;color:rgba(255,255,255,0.60);line-height:1.6;max-width:660px;margin:0;">'
        'Special Processing Networks (SPNs) are the core innovation of Pharos — customisable, '
        'application-specific execution environments that run semi-independently on top of the '
        'Pharos mainnet, each with its own execution engine, validator set, restaking incentives, '
        'and governance. All information on this page is sourced directly from official Pharos documentation.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Console toolbar strip ─────────────────
    st.markdown(
        '<div class="rd-toolbar" style="justify-content:space-between;">'
        '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">'
        '<span class="rd-tb-lbl">Console</span>'
        '<span style="font-family:DM Mono,monospace;font-size:12px;color:#2B3656;">spn://pharos-mainnet</span>'
        '<span style="display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:600;'
        'color:#166016;background:#F0FFF4;border:1px solid #86EFAC;border-radius:999px;padding:2px 10px;">'
        '● docs synced</span>'
        '</div>'
        f'<a href="{PHAROS_DOCS_URL}" target="_blank" style="font-family:Inter,sans-serif;font-size:12px;'
        'font-weight:700;color:#1414E8;text-decoration:none;">SDK Docs ↗</a>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Two-column: protocol readout + architecture registry ──
    _arch_facts = [
        ("SPN Manager",    "Manages SPN creation, destruction, message communication, and asset transfer"),
        ("Registry",       "Responsible for SPN registration and management on the Primary Network"),
        ("Mailbox",        "Records all SPN messages and events for cross-SPN communication"),
        ("Bridge",         "Manages asset transfers between SPNs and the Primary Network"),
        ("SPN Network Hub","Facilitates message and event communication across all SPNs"),
        ("SPN Adapter",    "Handles incoming messages from the Primary Network within each SPN"),
    ]

    spn_left, spn_right = st.columns([1, 1], gap="large")

    with spn_left:
        with st.container(border=True):
            st.markdown(
                '<div style="padding:0.4rem 0.6rem 0.3rem 0.7rem;">'
                '<span class="rd-eyebrow">📖 Protocol</span>'
                '<div class="rd-panel-title">How SPNs work</div>'
                '<div class="rd-panel-sub">Sourced from the official Pharos documentation.</div>'
                '<div class="rd-console" style="margin-top:0.5rem;">'
                '<div class="rd-con-bar">'
                '<span class="rd-dot" style="background:#FF5F56;"></span>'
                '<span class="rd-dot" style="background:#FFBD2E;"></span>'
                '<span class="rd-dot" style="background:#27C93F;"></span>'
                '<span style="margin-left:6px;font-size:11px;color:#7C8BB8;">staking-and-restaking.md</span>'
                '</div>'
                '<div style="margin-bottom:0.7rem;"><span class="rd-k"># </span>'
                'Validators stake P Tokens on the Primary Network. Each staked token generates a '
                'certificate (<span class="rd-v">stP</span>) which can be restaked into an SPN for '
                'additional rewards. SPNs set their own validator requirements, hardware needs, and '
                'soft/hard caps on stP. The Primary Network automatically initiates SPN creation once '
                'conditions are met.</div>'
                '<div><span class="rd-k"># </span>'
                'Cross-SPN communication uses the <span class="rd-v">Cross-SPN Interoperability '
                'Protocol</span>: transactions are initiated in one SPN, relayed via the Primary '
                'Network Mailbox, verified, then executed in the destination SPN — enabling atomic '
                'cross-SPN interactions.</div>'
                '</div></div>',
                unsafe_allow_html=True,
            )

    with spn_right:
        with st.container(border=True):
            st.markdown(
                '<div style="padding:0.4rem 0.6rem 0.4rem 0.7rem;">'
                '<span class="rd-eyebrow">🧩 Architecture</span>'
                '<div class="rd-panel-title">Core components</div>'
                '<div class="rd-panel-sub">The registry of SPN system contracts.</div>'
                '<div style="display:flex;flex-direction:column;gap:8px;margin-top:0.5rem;">'
                + "".join([
                    f'<div style="display:flex;gap:10px;align-items:flex-start;background:#F4F5FF;'
                    f'border:1px solid #E4E8F2;border-radius:10px;padding:0.6rem 0.8rem;">'
                    f'<div style="font-family:DM Mono,monospace;font-size:10px;font-weight:700;color:#1414E8;'
                    f'background:#FFFFFF;border:1px solid #C7D2FE;border-radius:6px;padding:2px 6px;'
                    f'white-space:nowrap;margin-top:1px;">{i:02d}</div>'
                    f'<div style="min-width:0;"><div style="font-size:12px;font-weight:800;color:#0B1020;">{k}</div>'
                    f'<div style="font-size:11px;color:#5B5F6E;line-height:1.5;">{v}</div></div></div>'
                    for i, (k, v) in enumerate(_arch_facts, start=1)
                ])
                + '</div></div>',
                unsafe_allow_html=True,
            )

    # ── Builder catalog: confirmed use cases (2-col grid) ──
    st.markdown(
    '<div style="margin-top:0.2rem;"><span class="rd-eyebrow">⚙️ Templates</span>'
    '<div class="rd-panel-title" style="font-size:16px;margin-top:-5.5px;">Confirmed SPN use cases</div>'
    '<div class="rd-panel-sub">Deployment patterns validators can build on excess compute.</div></div>',
    unsafe_allow_html=True,
)

    def _spn_card_html(spn):
        _feats = "".join([
            f'<span style="display:inline-flex;align-items:center;gap:4px;font-size:11px;'
            f'font-weight:600;color:{spn["tagcol"]};background:{spn["tagbg"]};'
            f'border-radius:20px;padding:3px 10px;margin-right:5px;margin-bottom:5px;">✓ {f}</span>'
            for f in spn["features"]
        ])
        return (
            f'<div class="rd-fillcard" style="background:#FFFFFF;border:1px solid #E4E8F2;border-radius:16px;'
            f'padding:1.2rem 1.3rem;height:100%;box-shadow:0 3px 14px rgba(20,20,60,0.06);'
            f'position:relative;overflow:hidden;box-sizing:border-box;margin-bottom:18px;">'
            f'<div style="position:absolute;left:0;top:0;bottom:0;width:4px;background:{spn["color"]};"></div>'
            f'<div style="padding-left:0.4rem;">'
            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:0.7rem;flex-wrap:wrap;">'
            f'<div style="width:42px;height:42px;border-radius:11px;background:{spn["bg"]};'
            f'display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">'
            f'{spn["emoji"]}</div>'
            f'<div><div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#0C0C1A;">'
            f'{spn["name"]}</div>'
            f'<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;'
            f'color:{spn["tagcol"]};margin-top:2px;">{spn["category"]}</div></div></div>'
            f'<div style="font-size:12px;color:#5B5F6E;line-height:1.6;margin-bottom:0.7rem;">'
            f'{spn["desc"]}</div>'
            f'<div style="margin-bottom:0.6rem;">{_feats}</div>'
            f'<div style="font-size:10.5px;color:#9499A8;border-top:1px solid #ECEEF4;padding-top:0.5rem;">'
            f'📄 {spn["source"]}</div>'
            f'</div></div>'
        )

    for _i in range(0, len(PHAROS_SPNS), 2):
        _pair = PHAROS_SPNS[_i:_i+2]
        _cols = st.columns(2, gap="large")
        for _c, _spn in zip(_cols, _pair):
            with _c:
                st.markdown(_spn_card_html(_spn), unsafe_allow_html=True)

    # ── CTA ───────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,#0A0A28,#1414E8);border-radius:16px;'
        'padding:1.4rem 1.8rem;display:flex;align-items:center;justify-content:space-between;'
        'flex-wrap:wrap;gap:12px;margin-top:1rem;">'
        '<div>'
        '<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:800;'
        'color:#FFFFFF;margin-bottom:4px;">Build your own SPN on Pharos</div>'
        '<div style="font-size:12.5px;color:rgba(255,255,255,0.60);">'
        'Validators can deploy custom SPNs using excess compute. Read the official docs to get started.</div>'
        '</div>'
        f'<a href="{PHAROS_DOCS_URL}" target="_blank" '
        'style="display:inline-flex;align-items:center;gap:6px;background:#FFFFFF;'
        'color:#1414E8;border-radius:10px;padding:0.65rem 1.3rem;font-size:13px;'
        'font-weight:700;text-decoration:none;white-space:nowrap;">📖 Pharos Docs ↗</a>'
        '</div>',
        unsafe_allow_html=True,
    )




# ═════════════════════════════════════════════
# PAGE: MARKET & COMMUNITY PULSE
# ═════════════════════════════════════════════
elif st.session_state.page == "pulse":

    _mp   = fetch_market_pulse()
    _pn   = get_pharos_news()
    _cp   = compute_community_pulse(_mp, _pn)

    # ── Hero ──────────────────────────────────
    st.markdown(
        '<div class="section-dark">'
        '<div style="display:inline-flex;align-items:center;gap:8px;font-size:11px;font-weight:700;'
        'letter-spacing:0.1em;text-transform:uppercase;color:rgba(255,255,255,0.85);'
        'background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);'
        'border-radius:20px;padding:5px 13px;margin-bottom:0.9rem;">'
        '<span style="width:6px;height:6px;border-radius:50%;background:#2BE080;'
        'box-shadow:0 0 6px #2BE080;display:inline-block;"></span>📡 Live · updates every 5 min</div>'
        '<h2 style="font-family:Syne,sans-serif;font-size:1.9rem;font-weight:800;color:#FFFFFF;'
        'margin:0 0 0.4rem 0;letter-spacing:-0.01em;">Market &amp; Community Pulse</h2>'
        '<div style="font-size:13px;color:rgba(255,255,255,0.65);max-width:560px;line-height:1.6;">'
        'Live $PROS market data, AI-read community sentiment, trending topics and the latest '
        'official Pharos announcements — in one glance.</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Live market stat cards ────────────────
    def _pulse_stat_card(label, value, sub="", sub_color="#7A7F96"):
        return (
            '<div style="background:rgba(255,255,255,0.92);border:1px solid #E7E8EE;border-radius:16px;'
            'padding:1rem 1.1rem;box-shadow:0 2px 10px rgba(20,20,60,0.05);height:100%;box-sizing:border-box;">'
            '<div style="font-size:10.5px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
            'color:#9499A8;margin-bottom:6px;">' + label + '</div>'
            '<div style="font-family:Syne,sans-serif;font-size:20px;font-weight:800;color:#0C0C1A;'
            'line-height:1.15;">' + value + '</div>'
            + ('<div style="font-size:11.5px;font-weight:600;color:' + sub_color + ';margin-top:4px;">' + sub + '</div>' if sub else '')
            + '</div>'
        )

    if _mp.get("available"):
        _p24  = _mp.get("chg24") or 0
        _p7   = _mp.get("chg7d") or 0
        _c24  = "#1FA855" if _p24 >= 0 else "#E5484D"
        _c7   = "#1FA855" if _p7 >= 0 else "#E5484D"
        _s24  = ("▲ " if _p24 >= 0 else "▼ ") + f"{abs(_p24):.2f}% · 24h"
        _s7   = ("▲ " if _p7 >= 0 else "▼ ") + f"{abs(_p7):.2f}% · 7d"
        _mcap = _mp.get("mcap")
        _vol  = _mp.get("vol24")
        _rank = _mp.get("rank")
        _sc1, _sc2, _sc3, _sc4 = st.columns(4, gap="small")
        with _sc1:
            st.markdown(_pulse_stat_card(
                "$PROS Price",
                (f"${_mp['price']:,.4f}" if _mp.get("price") else "—"),
                _s24, _c24), unsafe_allow_html=True)
        with _sc2:
            st.markdown(_pulse_stat_card(
                "7-Day Move",
                f"{_p7:+.2f}%",
                _s7, _c7), unsafe_allow_html=True)
        with _sc3:
            st.markdown(_pulse_stat_card(
                "Market Cap",
                (f"${_mcap/1e6:,.1f}M" if _mcap else "—"),
                (("Rank #" + str(_rank)) if _rank else "")), unsafe_allow_html=True)
        with _sc4:
            st.markdown(_pulse_stat_card(
                "24h Volume",
                (f"${_vol/1e6:,.1f}M" if _vol else "—"),
                "via " + esc(_mp.get("source", ""))), unsafe_allow_html=True)
    else:
        st.markdown(
            '<div style="background:rgba(255,255,255,0.92);border:1px dashed #D0D3E0;border-radius:16px;'
            'padding:1rem 1.2rem;font-size:12.5px;color:#7A7F96;">Live market data is temporarily '
            'unavailable — the pulse below is computed from the most recent cached figures.</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="margin-bottom:0.9rem;"></div>', unsafe_allow_html=True)

    # ── Chart + sentiment side by side ────────
    _pc_left, _pc_right = st.columns([1.45, 1], gap="medium")

    with _pc_left:
        st.markdown(
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:0.2rem;">'
            '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#FFFFFF;">'
            '📈 $PROS · Interactive chart</div></div>',
            unsafe_allow_html=True,
        )
        _pulse_range = st.radio(
            "Chart range", ["24H", "7D", "30D", "1Y"],
            horizontal=True, key="pulse_range", label_visibility="collapsed",
        )
        _pulse_days = {"24H": "1", "7D": "7", "30D": "30", "1Y": "365"}[_pulse_range]
        render_price_chart(get_price_chart_df(_pulse_days), chart_key="pulse_chart", days=_pulse_days)

    with _pc_right:
        _lbl   = _cp.get("label", "Neutral")
        _score = int(_cp.get("score", 50))
        _lcol  = {"Bullish": "#1FA855", "Neutral": "#B58A1F", "Bearish": "#E5484D"}.get(_lbl, "#B58A1F")
        _lico  = {"Bullish": "🐂", "Neutral": "⚖️", "Bearish": "🐻"}.get(_lbl, "⚖️")
        st.markdown(
            '<div style="background:rgba(255,255,255,0.92);border:1px solid #E7E8EE;border-radius:18px;'
            'padding:1.2rem 1.3rem;box-shadow:0 2px 12px rgba(20,20,60,0.06);">'
            '<div style="font-size:10.5px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
            'color:#9499A8;margin-bottom:8px;">Community sentiment</div>'
            '<div style="display:flex;align-items:baseline;gap:10px;margin-bottom:10px;">'
            '<span style="font-size:24px;line-height:1;">' + _lico + '</span>'
            '<span style="font-family:Syne,sans-serif;font-size:24px;font-weight:800;color:' + _lcol + ';">'
            + esc(_lbl) + '</span>'
            '<span style="font-size:12px;font-weight:700;color:#9499A8;">' + str(_score) + '/100</span>'
            '</div>'
            # gradient meter with needle
            '<div style="position:relative;height:8px;border-radius:6px;'
            'background:linear-gradient(90deg,#E5484D 0%,#E8C34A 50%,#1FA855 100%);'
            'box-shadow:inset 0 1px 2px rgba(20,20,60,0.18);margin-bottom:14px;">'
            '<div style="position:absolute;top:-4px;left:' + str(_score) + '%;width:4px;height:16px;'
            'transform:translateX(-50%);border-radius:3px;background:#0C0C1A;'
            'box-shadow:0 1px 4px rgba(12,12,26,0.4);"></div>'
            '</div>'
            '<div style="font-size:10.5px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;'
            'color:#9499A8;margin-bottom:6px;">'
            + ("🤖 AI discussion summary" if _cp.get("ai") else "Discussion summary") + '</div>'
            '<div style="font-size:12.5px;color:#39445D;line-height:1.65;">'
            + esc(_cp.get("summary", "")) + '</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="margin-bottom:1rem;"></div>', unsafe_allow_html=True)

    # ── Trending topics ───────────────────────
    _chips = ""
    for _tp in _cp.get("topics", []):
        _chips += (
            '<span style="display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;'
            'color:#1414E8;background:rgba(26,26,255,0.07);border:1px solid rgba(26,26,255,0.18);'
            'border-radius:20px;padding:6px 14px;">🔥 ' + esc(_tp) + '</span>'
        )
    st.markdown(
        '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#0C0C1A;'
        'margin-bottom:0.6rem;">🔥 Trending topics</div>'
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1.3rem;">' + _chips + '</div>',
        unsafe_allow_html=True,
    )

    # ── Latest official announcements ─────────
    st.markdown(
        '<div style="font-family:Syne,sans-serif;font-size:14px;font-weight:800;color:#0C0C1A;'
        'margin-bottom:0.6rem;">📰 Latest announcements</div>',
        unsafe_allow_html=True,
    )
    if _pn:
        for _art in _pn[:4]:
            st.markdown(
                '<a href="' + esc_url(_art.get("url")) + '" target="_blank" style="text-decoration:none;display:block;">'
                '<div style="background:rgba(255,255,255,0.92);border:1px solid #E7E8EE;border-radius:14px;'
                'padding:0.85rem 1.1rem;margin-bottom:8px;display:flex;align-items:center;gap:12px;'
                'transition:border-color 150ms ease,box-shadow 150ms ease;">'
                '<span style="font-size:16px;flex-shrink:0;">🗞️</span>'
                '<div style="min-width:0;">'
                '<div style="font-size:13px;font-weight:700;color:#0C0C1A;line-height:1.4;overflow:hidden;'
                'text-overflow:ellipsis;white-space:nowrap;">' + esc(_art.get("title", "")) + '</div>'
                '<div style="font-size:11px;color:#9499A8;margin-top:2px;">'
                + esc(_art.get("source", "")) + '</div>'
                '</div></div></a>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div style="display:flex;gap:10px;flex-wrap:wrap;">'
            '<a href="' + PHAROS_X_URL + '" target="_blank" style="text-decoration:none;flex:1;min-width:180px;">'
            '<div style="background:rgba(255,255,255,0.92);border:1px solid #E7E8EE;border-radius:14px;'
            'padding:0.9rem 1.1rem;font-size:12.5px;font-weight:700;color:#0C0C1A;">𝕏 Official X updates ↗</div></a>'
            '<a href="' + PHAROS_DISCORD_URL + '" target="_blank" style="text-decoration:none;flex:1;min-width:180px;">'
            '<div style="background:rgba(255,255,255,0.92);border:1px solid #E7E8EE;border-radius:14px;'
            'padding:0.9rem 1.1rem;font-size:12.5px;font-weight:700;color:#0C0C1A;">💬 Discord announcements ↗</div></a>'
            '<a href="' + PHAROS_DOCS_URL + '" target="_blank" style="text-decoration:none;flex:1;min-width:180px;">'
            '<div style="background:rgba(255,255,255,0.92);border:1px solid #E7E8EE;border-radius:14px;'
            'padding:0.9rem 1.1rem;font-size:12.5px;font-weight:700;color:#0C0C1A;">📖 Pharos docs ↗</div></a>'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="margin-bottom:0.6rem;"></div>', unsafe_allow_html=True)
    if st.button("↻ Refresh pulse", key="pulse_refresh"):
        st.session_state.pop("pulse_market_cache", None)
        st.session_state.pop("pulse_ai_cache", None)
        st.session_state.pop("pharos_news_cache", None)
        st.rerun()


st.markdown('<div style="margin-top:2rem;"></div>', unsafe_allow_html=True)
st.markdown(
    
    '<div style="text-align:center;padding:1rem 0 0.5rem 0;'
    'border-top:1px solid #D0D3E0;margin-top:1rem;">'
    '<span style="font-size:15px;color:#FFFFFF;">Built by&nbsp;</span>'
    '<strong style="font-size:15px;color:#0C0C1A;">Echo</strong>'
    '<span style="font-size:15px;color:#FFFFFF;">&nbsp;·&nbsp;</span>'
    '<span style="font-size:15px;color:#FFFFFF;">Discord:&nbsp;</span>'
    '<strong style="font-size:15px;color:#0C0C1A;">@echoplex99</strong>'
    '<span style="font-size:15px;color:#7A7F96;">&nbsp;·&nbsp;</span>'
    '<a href="https://x.com/isharik99" target="_blank" '
    'style="font-size:15px;font-weight:600;color:#1A1AFF;text-decoration:none;">@isharik99 on X ↗</a>'
    '<span style="font-size:15px;color:#7A7F96;">&nbsp;·&nbsp;</span>'
    '<a href="https://github.com/isharik/Pharos-Octobot" target="_blank" '
    'style="font-size:15px;font-weight:600;color:#1A1AFF;text-decoration:none;">'
    'GitHub ↗</a>'
    '</div>',
    unsafe_allow_html=True,
)