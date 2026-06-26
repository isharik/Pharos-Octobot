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

import os, time, base64, json, re
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

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
        "title": "AI Agent Carnival — Phase 1",
        "tag":   "LIVE · Skill Hackathon",
        "desc":  "Build reusable Skill modules on Pharos and win from a 150,000 PROS prize pool. Phase 1 closes Jun 15.",
        "link":  "https://dorahacks.io/hackathon/pharos-phase1",
        "cta":   "Submit your Skill",
        "color": "#1A1AFF",
        "logo":  "https://www.google.com/s2/favicons?domain=dorahacks.io&sz=64",
        "icon":  "🏆",
        "bg":    "linear-gradient(135deg,#EEF0FF,#E4E8FF)",
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
        "bg":    "linear-gradient(135deg,#E8F4FF,#DCEEff)",
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
        "bg":    "linear-gradient(135deg,#F0FFF4,#E0F8E8)",
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

# Logo assistant bubble → navigate to chat
_goto = st.query_params.get("goto", "")
if _goto == "chat":
    st.session_state.page = "chat"
    st.query_params.clear()

# Wallet connect widget → navigate back with address
_wallet = st.query_params.get("wallet", "")
if _wallet and _wallet.lower() != st.session_state.wallet_address.lower():
    st.session_state.wallet_address = _wallet
    st.session_state.wallet_data    = None
    st.session_state.wallet_profile = None
    st.session_state.page = "memory"
    st.query_params.clear()
    

# Voice query from mic widget
_voice_q = st.query_params.get("voice_q", "")
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
        f'<div class="source-item-title">{s["title"]}</div>'
        f'<a class="source-item-url" href="{s["url"]}" target="_blank">{s["url"]}</a>'
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
    width:100%;height:220px;position:relative;
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
  function draw(){
    requestAnimationFrame(draw);
    t++;
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
  setTimeout(()=>{ lastPulse=performance.now(); draw(); }, 100);

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
        height=220,
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


@st.cache_resource(show_spinner=False)
def load_octobot():
    try:
        from octobot import OctoBot
        return OctoBot(), None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800'
    '&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# CSS — unified across all pages
# ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --blue:    #1A1AFF;
    --blue2:   #2D2DE0;
    --light:   #6B8CFF;
    --glow:    rgba(26,26,255,0.15);
    --subtle:  rgba(26,26,255,0.06);
    --bg:   #C9D4E8;
--bg1:  #D9E2F0;
--bg2:  #D0DBEB;
    --glass:   rgba(244,245,248,0.82);
    --border:  #D0D3E0;
    --border2: #C4C8D8;
    --t1:      #0C0C1A;
    --t2:      #42475A;
    --t3:      #7A7F96;
    --green:   #1FA855;
    --red:     #E5484D;
    --fd:      'Syne', sans-serif;
    --fb:      'DM Sans', sans-serif;
    --rad:     12px;
    --rad-lg:  18px;
    --shadow:  0 2px 12px rgba(20,20,60,0.07);
    --shadow-md: 0 6px 24px rgba(20,20,60,0.1);
    --shadow-blue: 0 4px 20px rgba(26,26,255,0.12);
}
html,body,[class*="css"]{font-family:var(--fb)!important;background-color:var(--bg)!important;color:var(--t1)!important;font-size:14px!important;}
.stApp{
    background-color: #D7DCE6!important;
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
        /* Ambient light source — top right, moves slowly */
        radial-gradient(ellipse 65% 50% at 78% 8%,  rgba(220,228,255,0.55) 0%, transparent 65%),
        /* Secondary light — bottom left */
        radial-gradient(ellipse 50% 40% at 12% 88%, rgba(200,215,255,0.30) 0%, transparent 60%),
        /* Mid tone depth */
        radial-gradient(ellipse 80% 60% at 50% 50%, rgba(185,200,240,0.12) 0%, transparent 70%),
        /* Wave band 1 — diagonal flow */
        repeating-linear-gradient(
            -28deg,
            transparent 0px,
            transparent 38px,
            rgba(160,180,225,0.09) 38px,
            rgba(160,180,225,0.09) 40px,
            transparent 40px,
            transparent 78px
        ),
        /* Wave band 2 — counter diagonal */
        repeating-linear-gradient(
            62deg,
            transparent 0px,
            transparent 55px,
            rgba(140,165,215,0.06) 55px,
            rgba(140,165,215,0.06) 57px,
            transparent 57px,
            transparent 114px
        ),
        /* Wave band 3 — shallow angle */
        repeating-linear-gradient(
            -12deg,
            transparent 0px,
            transparent 80px,
            rgba(170,190,230,0.05) 80px,
            rgba(170,190,230,0.05) 82px,
            transparent 82px,
            transparent 160px
        );
    animation: wave-shift 22s cubic-bezier(0.4,0,0.2,1) infinite;
}

 /* Snappy global baseline — overrides Streamlit's slower defaults */
*, *::before, *::after {
    transition-duration: 120ms !important;
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
    0%,100%{ transform:translate(0,0) scale(1); }
    50%{ transform:translate(46px,-34px) scale(1.16); }
}
@keyframes auraDrift2{
    0%,100%{ transform:translate(0,0) scale(1); }
    50%{ transform:translate(-54px,42px) scale(1.12); }
}
@keyframes auraDrift3{
    0%,100%{ transform:translate(0,0) scale(1); }
    50%{ transform:translate(34px,32px) scale(1.2); }
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
        radial-gradient(circle 620px at 14% 10%, rgba(8,8,80,0.45) 0%, transparent 72%),
        radial-gradient(circle 560px at 88% 22%, rgba(10,10,100,0.38) 0%, transparent 72%),
        radial-gradient(circle 640px at 46% 90%, rgba(6,6,70,0.35) 0%, transparent 72%),
        radial-gradient(circle 480px at 70% 60%, rgba(12,12,90,0.28) 0%, transparent 70%);
    animation:
        auraDrift1 16s ease-in-out infinite,
        auraDrift2 20s ease-in-out infinite,
        auraDrift3 24s ease-in-out infinite;
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
    animation: dotsFloat 56s linear infinite;
}

/* Keep every real Streamlit block above both background layers */
[data-testid="stAppViewContainer"] > .main,
[data-testid="stHeader"],
section[data-testid="stSidebar"]{
    position:relative;
    z-index:1;
}

#MainMenu,footer,header,.stDeployButton{display:none!important;}
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

/* Force Streamlit main block to allow true centering */
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
    margin-top: -2rem !important;
}
/* Center markdown blocks that contain hero */
[data-testid="stMarkdownContainer"] {
    width: 100%;
}

/* ── TOP NAV ─── */
.octo-nav{
    display:flex;align-items:center;gap:0;
    background:#F3F4F7;
    border:1px solid #E7E9EF;
    border-radius:16px;
    padding:0 1.4rem;
    height:60px;
    margin:14px auto 0 auto;
    max-width:1180px;
    position:sticky;top:14px;z-index:100;
    box-shadow:0 1px 2px rgba(20,20,60,0.04);
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

/* nav buttons handled via Streamlit — clean text-link style like reference */
.nav-wrap .stButton>button{
    background:transparent!important;
    border:none!important;
    border-radius:9px!important;
    font-family:var(--fb)!important;
    font-size:16px!important;
    font-weight:700!important;
    color:#2B2E38!important;
    opacity:1!important;
    letter-spacing:-0.003em!important;
    padding:0.5rem 0.85rem!important;
    height:auto!important;
    text-align:center!important;
    box-shadow:none!important;
    transition:background 200ms cubic-bezier(0.4,0,0.2,1),
               color 200ms cubic-bezier(0.4,0,0.2,1)!important;
}
.nav-wrap .stButton>button:hover{
    background:rgba(20,20,60,0.05)!important;
    color:#0C0C1A!important;
    box-shadow:none!important;
}
.nav-wrap.active .stButton>button{
    background:#0C0C1A!important;
    color:#FFFFFF!important;
    font-weight:600!important;
    box-shadow:none!important;
}
.nav-cta .stButton>button{
    background:var(--blue)!important;
    color:#fff!important;
    border-radius:30px!important;
    font-size:13.5px!important;
    font-weight:600!important;
    padding:0.55rem 1.2rem!important;
    letter-spacing:0.01em!important;
    box-shadow:0 4px 14px rgba(26,26,255,0.25)!important;
    transition:background 200ms cubic-bezier(0.4,0,0.2,1),
               transform 200ms cubic-bezier(0.4,0,0.2,1),
               box-shadow 200ms cubic-bezier(0.4,0,0.2,1)!important;
}
.nav-cta .stButton>button:hover{
    background:var(--blue2)!important;
    transform:translateY(-1px)!important;
    box-shadow:0 6px 20px rgba(26,26,255,0.35)!important;
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
    display:inline-flex;align-items:center;gap:7px;
    font-size:16px;font-weight:700;letter-spacing:0.02em;
    color:#FFFFFF;background:#0C0C1A;border:none;
    border-radius:30px;padding:7px 16px;margin-bottom:0.1rem;margin-top:2rem;
    align-self:center;
    box-shadow:0 4px 14px rgba(12,12,26,0.18);
}
.hero-eyebrow .live-dot{
    width:6px;height:6px;border-radius:50%;background:var(--green);
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
    background:rgba(255,255,255,0.92);border:1px solid rgba(20,20,60,0.07);
    border-radius:18px;padding:1.5rem 1.6rem;
    transition:transform 240ms cubic-bezier(0.34,1.4,0.64,1),
               box-shadow 240ms cubic-bezier(0.4,0,0.2,1),
               border-color 200ms ease;
    box-shadow:0 2px 10px rgba(20,20,60,0.05);
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
    background:rgba(255,255,255,0.92);
    border:1px solid rgba(20,20,60,0.07);
    border-radius:18px;
    overflow:hidden;
    box-shadow:0 2px 10px rgba(20,20,60,0.05);
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
    transition:
        background 150ms cubic-bezier(0.4,0,0.2,1),
        color 150ms cubic-bezier(0.4,0,0.2,1),
        transform 140ms cubic-bezier(0.4,0,0.2,1),
        box-shadow 150ms cubic-bezier(0.4,0,0.2,1)
    !important;
}
.nav-wrap .stButton > button:hover{
    transform:translateY(-1px)!important;
}
.nav-wrap .stButton > button:active{
    transform:scale(0.97)!important;
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
   PREMIUM MOTION SYSTEM — scroll reveal + stagger
   Apple × Linear × Arc quality, GPU accelerated
═══════════════════════════════════════════ */

/* Momentum-feel smooth scrolling on the main scroll container */
section[data-testid="stMain"]{
    scroll-behavior:smooth!important;
    -webkit-overflow-scrolling:touch!important;
    overscroll-behavior-y:contain!important;
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
</style>
""", unsafe_allow_html=True)

_sailor = st.query_params.get("sailor", "")
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
    ("🚀", "Campaigns", "campaigns"),
    ("📰", "Updates",   "updates"),
    ("📊", "Trade",     "trade"),
    ("🧩", "Ecosystem", "ecosystem"),
    ("💸", "Pay",       "pay"),
]

st.markdown('<div style="display:flex;justify-content:center;margin-bottom:0.5rem;">', unsafe_allow_html=True)
nav_cols = st.columns([1.2, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.1, 1.1])

st.markdown(
    '<div style="display:flex;justify-content:center;margin-bottom:0.6rem;">'
    '<div style="display:inline-flex;align-items:center;gap:2px;'
    'background:#0C0C1A;border-radius:40px;padding:5px 6px;'
    'box-shadow:0 2px 12px rgba(0,0,0,0.15);">'
    '</div></div>',
    unsafe_allow_html=True,
)
with nav_cols[0]:
    if logo_b64:
        logo_html = (
            '<div style="display:flex;align-items:center;gap:7px;padding:8px 0;">'
            '<div style="position:relative;width:26px;height:26px;flex-shrink:0;">'
            '<img src="' + logo_b64 + '" style="width:26px;height:26px;border-radius:50%;position:relative;z-index:2;" />'
            '<div style="position:absolute;inset:-5px;border-radius:50%;border:1.5px solid rgba(26,26,255,0.3);animation:orbit-spin 8s linear infinite;">'
            '<div style="position:absolute;width:5px;height:5px;border-radius:50%;background:#1A1AFF;top:-2px;left:50%;transform:translateX(-50%);"></div>'
            '</div></div>'
            '<span style="font-family:Syne,sans-serif;font-size:15px;font-weight:700;color:#14141F;">OctoBot</span>'
            '</div>'
        )
    else:
        logo_html = (
            '<div style="display:flex;align-items:center;gap:6px;padding:8px 0;">'
            '<span style="font-size:20px;">🐙</span>'
            '<span style="font-family:Syne,sans-serif;font-size:15px;font-weight:700;color:#14141F;">OctoBot</span>'
            '</div>'
        )
    st.markdown(logo_html, unsafe_allow_html=True)

for col_idx, (icon, label, page_key) in enumerate(NAV_PAGES):
    with nav_cols[col_idx + 1]:
        is_active = st.session_state.page == page_key
        prefix    = "● " if is_active else ""
        st.markdown('<div class="nav-wrap' + (" active" if is_active else "") + '">', unsafe_allow_html=True)
        if st.button(prefix + icon + " " + label, key="nav_" + page_key, use_container_width=True):
            st.session_state.page = page_key
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

with nav_cols[9]:
    st.markdown('<div class="nav-cta">', unsafe_allow_html=True)
    st.link_button("↗ Pharos Network", PHAROS_MAIN_URL, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)
st.markdown('<hr style="border:none;border-top:1px solid #E3E5EA;margin:0 0 1rem 0;">', unsafe_allow_html=True)

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
            f'<span style="font-size:11px;color:#9499A8;">$PROS&nbsp;</span>'
            f'<span style="font-size:13px;font-weight:700;color:#14141F;font-family:Syne,sans-serif;">${p["price_usd"]:.4f}</span>'
            f'<span style="font-size:11px;color:{cc};margin-left:4px;">{sym}{abs(chg):.2f}%</span>'
        )
    else:
        price_pill = '<span style="font-size:11px;color:#9499A8;">$PROS loading…</span>'

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
        </style>

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
                if manual_addr.strip().startswith("0x") and len(manual_addr.strip()) == 42:
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
                    f'<div style="font-size:15px;color:#fff;font-weight:700;font-family:monospace;letter-spacing:0.01em;">{short_addr}</div>'
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
                f'font-weight:700;">{t}</span>'
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
                f'"{profile.get("summary", "")}"</div>'
                f'<div style="margin-bottom:0.9rem;position:relative;z-index:1;">{tags_html}'
                f'<span class="tag" style="background:rgba(31,168,85,0.12);border-color:rgba(31,168,85,0.35);'
                f'color:#1FA855;display:inline-block;font-weight:700;">Risk: {profile.get("risk", "Unknown")}</span></div>'
                f'<div style="font-size:13px;color:#42475A;background:rgba(255,255,255,0.7);'
                f'border-radius:12px;padding:0.8rem 1rem;position:relative;z-index:1;">'
                f'💡 <strong>Suggested next step:</strong> {profile.get("insight", "")}</div>'
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
            if cleaned.startswith("0x") and len(cleaned) == 66:
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
                    f'<span style="color:#1A1AFF;flex-shrink:0;">→</span><span>{s}</span></div>'
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
                    f'"{explanation.get("summary", "")}"</div>'
                    f'<span class="tag" style="display:inline-block;margin-bottom:0.9rem;position:relative;z-index:1;">'
                    f'{explanation.get("category", "Transaction")}</span>'
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

    bot, load_error = load_octobot()
    _lp.empty()

    if load_error:
        st.error("OctoBot could not start: " + load_error + " — Run `python build_vectorstore.py` then refresh.")
        st.stop()

    # ── Settings moved to sidebar — just get chunk count here ──
    chunk_count = bot.vectorstore._collection.count()

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

    # ── Language selector ─────────────────────────────────────────
    LANG_OPTIONS = {
        "English":    "🇬🇧",
        "Hindi":      "🇮🇳",
        "Spanish":    "🇪🇸",
        "Arabic":     "🇸🇦",
        "Chinese":    "🇨🇳",
        "Japanese":   "🇯🇵",
    }
    cur_lang   = st.session_state.octobot_lang
    cur_flag   = LANG_OPTIONS.get(cur_lang, "🌐")
    lang_pills = "".join([
        f'<span style="display:inline-flex;align-items:center;gap:4px;'
        f'font-size:12px;font-weight:{"700" if lang==cur_lang else "500"};'
        f'padding:4px 11px;border-radius:20px;cursor:pointer;'
        f'background:{"#1A1AFF" if lang==cur_lang else "#FFFFFF"};'
        f'color:{"#FFFFFF" if lang==cur_lang else "#42475A"};'
        f'border:1px solid {"#1A1AFF" if lang==cur_lang else "#D0D3E0"};'
        f'margin-right:4px;">{flag} {lang}</span>'
        for lang, flag in LANG_OPTIONS.items()
    ])
    st.markdown(
        '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;'
        'margin-bottom:0.7rem;padding:0.6rem 0.9rem;'
        'background:#F4F5F8;border:1px solid #D0D3E0;border-radius:10px;">'
        '<span style="font-size:11px;font-weight:700;color:#0C0C1A;'
        'letter-spacing:0.05em;text-transform:uppercase;white-space:nowrap;'
        'margin-right:4px;">🌐 Language:</span>'
        + lang_pills +
        '</div>',
        unsafe_allow_html=True,
    )
    lang_cols = st.columns(len(LANG_OPTIONS))
    for li, (lang, flag) in enumerate(LANG_OPTIONS.items()):
        with lang_cols[li]:
            if st.button(
                flag + " " + lang,
                key="lang_" + lang,
                use_container_width=True,
            ):
                st.session_state.octobot_lang = lang
                st.rerun()

    # ── Mode toggle — big, visible, above chat ──────────────────
    current_mode = st.session_state.chat_mode
    is_general   = current_mode == "general"
    mode_desc    = (
        "🌐 Docs + General — answers from docs, falls back to Gemini for anything else"
        if is_general else
        "📚 Docs Only — answers strictly from verified Pharos documentation"
    )
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.8rem;'
        'background:#F0F1F8;border:1.5px solid #D0D3E0;border-radius:10px;padding:0.65rem 1rem;">'
        '<span style="font-size:13px;font-weight:800;color:#0C0C1A;white-space:nowrap;">Mode:</span>'
        '<span style="font-size:12px;font-weight:500;color:#42475A;">' + mode_desc + '</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    mc1, mc2, mc3 = st.columns([1, 1, 4])
    with mc1:
        if st.button("📚 Docs Only",      key="mode_docs",    use_container_width=True):
            st.session_state.chat_mode = "docs";    st.rerun()
    with mc2:
        if st.button("🌐 Docs + General", key="mode_general", use_container_width=True):
            st.session_state.chat_mode = "general"; st.rerun()

    # ── Name gate — blocks chat until name entered ──
    if not st.session_state.sailor_done:
        st.markdown("""
        <style>
        section[data-testid="stSidebar"]{display:none!important;}
        div[data-testid="stDecoration"]{display:none!important;}
        .gate-wrap{
            display:flex;flex-direction:column;align-items:center;
            justify-content:center;min-height:30vh;padding:2rem 1rem 0 1rem;
        }
        .gate-card{
            background:#FFFFFF;
            border:1.5px solid rgba(26,26,255,0.15);
            border-radius:28px;
            padding:2.8rem 2.8rem 2rem 2.8rem;
            width:100%;max-width:400px;
            text-align:center;
            box-shadow:0 32px 80px rgba(26,26,255,0.14),
                       0 8px 24px rgba(0,0,0,0.08);
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
            font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
            color:#0C0C1A;margin-bottom:0.4rem;letter-spacing:-0.025em;
            animation:rise 0.5s cubic-bezier(0.16,1,0.3,1) 0.65s both;
        }
        .gate-sub{
            font-size:13.5px;color:#7A7F96;line-height:1.65;margin-bottom:0.5rem;
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
            '<h3>Hi ' + name + '! 👋 Welcome aboard</h3>'
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


    # ── Chat input + answer ────────────────────
    pending    = st.session_state.pop("pending_q", None)
    sel_lang   = st.session_state.get("octobot_lang", "English")
    placeholder = (
        "Ask anything about Pharos — any language 🌐"
        if sel_lang == "English"
        else f"Ask OctoBot in {sel_lang} 🌐"
    )
    user_input = st.chat_input(placeholder)
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

        with st.chat_message("assistant", avatar="🐙"):
            # ── Thinking orb (feature 1) ──────────────
            orb_slot = st.empty()
            with orb_slot.container():
                render_thinking_orb("thinking")

            with st.spinner(""):
                try:
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
                    f'<div class="build-step-num">{s["num"]}</div>'
                    f'<div><div class="build-step-text">{s["title"]}</div>'
                    f'<div class="build-step-sub">{s["desc"]}</div></div>'
                    f'</div>'
                    for s in bp.get("steps", [])
                ])
                docs_html = " · ".join([
                    f'<a href="{d["url"]}" target="_blank" '
                    f'style="color:#1A1AFF;font-size:11px;font-weight:600;text-decoration:none;">'
                    f'{d["title"]} ↗</a>'
                    for d in bp.get("docs", [])
                ])
                actions_html = "".join([
                    f'<a class="build-action-btn" href="{a["url"]}" target="_blank">{a["label"]} ↗</a>'
                    for a in bp.get("actions", [])
                ])
                st.markdown(
                    f'<div class="build-path-card">'
                    f'<div class="build-path-title">Your Build Path</div>'
                    f'<div class="build-path-goal">{bp.get("goal","")}</div>'
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
                            f'<div style="font-size:13px;font-weight:600;color:#0C0C1A;margin-bottom:3px;">{s["title"]}</div>'
                            f'<a href="{s["url"]}" target="_blank" '
                            f'style="font-size:11px;color:#1A1AFF;text-decoration:none;word-break:break-all;">'
                            f'{s["url"]}</a>'
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

    # All campaign cards in ONE st.markdown — vertical grid cards, top media block (ref-3 style)
    all_camp_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-bottom:1.4rem;">'
    for c in CAMPAIGNS:
        all_camp_html += (
            f'<a href="{c["link"]}" target="_blank" '
            f'style="display:flex;flex-direction:column;'
            f'background:#FFFFFF;border:1px solid #E3E5EA;border-radius:18px;'
            f'overflow:hidden;text-decoration:none;'
            f'box-shadow:0 2px 10px rgba(20,20,60,0.05);'
            f'transition:transform 240ms cubic-bezier(0.34,1.4,0.64,1),box-shadow 240ms ease,border-color 180ms ease;"'
            f' onmouseover="this.style.transform=\'translateY(-6px)\';this.style.boxShadow=\'0 18px 44px rgba(26,26,255,0.16)\';"'
            f' onmouseout="this.style.transform=\'translateZ(0)\';this.style.boxShadow=\'0 2px 10px rgba(20,20,60,0.05)\';">'
            # Top media block — colored gradient with large icon
            f'<div style="background:{c["bg"]};height:140px;'
            f'display:flex;align-items:center;justify-content:center;position:relative;">'
            f'<span style="font-size:52px;line-height:1;filter:drop-shadow(0 4px 14px rgba(0,0,0,0.12));">{c["icon"]}</span>'
            f'<img src="{c["logo"]}" width="22" height="22" '
            f'style="position:absolute;bottom:12px;right:14px;border-radius:5px;opacity:0.7;" '
            f'onerror="this.style.display=\'none\'"/>'
            f'</div>'
            # Bottom text block
            f'<div style="padding:1.3rem 1.4rem 1.5rem 1.4rem;display:flex;flex-direction:column;gap:8px;">'
            f'<div class="camp-tag" style="align-self:flex-start;">{c["tag"]}</div>'
            f'<div class="camp-title">{c["title"]}</div>'
            f'<div class="camp-desc">{c["desc"]}</div>'
            f'<span style="font-size:11.5px;font-weight:600;color:#1A1AFF;margin-top:2px;">{c["cta"]} ↗</span>'
            f'</div>'
            f'</a>'
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
        '<div style="width:60px;flex-shrink:0;font-size:10px;color:#9499A8;font-weight:600;padding-top:1px;">Pre-Season</div>'
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
        st.link_button("Submit on DoraHacks ↗", "https://dorahacks.io/hackathon/pharos-phase1", use_container_width=True)
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
        'Only ongoing campaigns and initiatives — hackathons, stake events, and more.</p>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # ── Live news from CoinGecko ───────────────
    with st.spinner("Loading latest Pharos news…"):
        news_items = get_pharos_news()

    if news_items:
        cards_source = news_items[:6]
    else:
        cards_source = [
            {"title": "Cross-chain access is expanding on Pharos", "description": "@StargateFinance now supports Pharos, enabling users to transfer and swap assets across EVM chains", "url": "https://x.com/pharos_network/status/2067208187615576378?s=20", "thumb": "https://pbs.twimg.com/profile_images/1928147506699145217/n7-KQGNJ_400x400.png", "date": ""},
            {"title": "Pharos is partnering with @avalonfinance and @FunctionBTC", "description": " To expand Bitcoin utility within the Pharos ecosystem.", "url": "https://x.com/pharos_network/status/2066993885784822019?s=20", "thumb": "https://pbs.twimg.com/profile_images/1874986577774145536/Uvumm1eb_400x400.jpg", "date": ""},
            {"title": "AI Agent Carnival Phase 1 is LIVE", "description": "150,000 PROS prize pool · Submit Skills by June 15 on DoraHacks", "url": "https://dorahacks.io/hackathon/pharos-phase1", "thumb": "https://www.google.com/s2/favicons?domain=dorahacks.io&sz=64", "date": ""},
            {"title": "The Builders Harbor on Pharos has been upgraded", "description": "New tools, templates, and technical resources.", "url": "https://www.pharos.xyz/devhub", "thumb": "https://www.google.com/s2/favicons?domain=pharos.xyz&sz=64", "date": ""},
            {"title": "USDC + CCTP integration live", "description": "Pharos integrates Circle's USDC and CCTP for real-time RealFi settlement.", "url": PHAROS_MAIN_URL, "thumb": "https://www.google.com/s2/favicons?domain=circle.com&sz=64", "date": ""},
            {"title": "Expedition Season 2 ongoing", "description": "Particpate in the Ecosystem.", "url": "https://discord.gg/pharos", "thumb": "https://www.google.com/s2/favicons?domain=discord.com&sz=64", "date": ""},
            {"title": "Pharos x XLayer & OKX", "description": "Fellow partners in bringing World Cup outcomes onchain.", "url": "https://x.com/pharos_network/status/2065362220851335650", "thumb": "https://www.google.com/s2/favicons?domain=okx.com&sz=64", "date": ""},
            {"title": "Follow Pharos on X for more updates", "description": "Also join Discord for more insights.", "url": "https://x.com/pharos_network", "thumb": "https://pbs.twimg.com/profile_images/2005491865450430464/ta6znFqT_400x400.jpg", "date": ""},
        ]
        st.markdown(
            '<div style="font-size:11px;color:#9499A8;margin-bottom:0.6rem;">'
            'News could not be loaded from CoinGecko — showing latest known updates:</div>',
            unsafe_allow_html=True,
        )

    # All update cards in ONE st.markdown — same grid + top-media-block
    # style as the campaign cards, just driven by news data instead.
    UPDATE_BG = "linear-gradient(135deg,#EEF0FF,#E4E8FF)"
    all_updates_html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px;margin-bottom:1.4rem;">'
    for n in cards_source:
        title = n.get("title", "")
        desc  = (n.get("description", "") or "")[:140]
        link  = n.get("url", "#")
        thumb = n.get("thumb", "")
        date  = n.get("date", "")
        all_updates_html += (
            f'<a href="{link}" target="_blank" '
            f'style="display:flex;flex-direction:column;'
            f'background:#FFFFFF;border:1px solid #E3E5EA;border-radius:18px;'
            f'overflow:hidden;text-decoration:none;'
            f'box-shadow:0 2px 10px rgba(20,20,60,0.05);'
            f'transition:transform 240ms cubic-bezier(0.34,1.4,0.64,1),box-shadow 240ms ease,border-color 180ms ease;"'
            f' onmouseover="this.style.transform=\'translateY(-6px)\';this.style.boxShadow=\'0 18px 44px rgba(26,26,255,0.16)\';"'
            f' onmouseout="this.style.transform=\'translateZ(0)\';this.style.boxShadow=\'0 2px 10px rgba(20,20,60,0.05)\';">'
            # Top media block — same 140px height as campaign cards
            f'<div style="background:{UPDATE_BG};height:140px;'
            f'display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;">'
            + (
                f'<img src="{thumb}" style="max-width:72px;max-height:72px;object-fit:contain;'
                f'filter:drop-shadow(0 4px 14px rgba(0,0,0,0.12));" '
                f'onerror="this.outerHTML=\'<span style=&quot;font-size:44px;&quot;>📰</span>\'"/>'
                if thumb else
                '<span style="font-size:44px;">📰</span>'
            ) +
            f'</div>'
            # Bottom text block — same padding/tag/title/desc/cta as campaigns
            f'<div style="padding:1.3rem 1.4rem 1.5rem 1.4rem;display:flex;flex-direction:column;gap:8px;">'
            + (f'<div class="camp-tag" style="align-self:flex-start;">{date}</div>' if date else '<div class="camp-tag" style="align-self:flex-start;">LATEST</div>')
            + f'<div class="camp-title">{title}</div>'
            f'<div class="camp-desc">{desc}</div>'
            f'<span style="font-size:11.5px;font-weight:600;color:#1A1AFF;margin-top:2px;">Read more ↗</span>'
            f'</div>'
            f'</a>'
        )
    all_updates_html += '</div>'
    st.markdown(all_updates_html, unsafe_allow_html=True)

    # Quick Updates timeline — same visual language as the campaign
    # "Phase Timeline" card (white card, vertical connector line)
    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
    if news_items and len(news_items) > 6:
        timeline_html = (
            '<div style="background:#FFFFFF;border:1px solid #E3E5EA;border-radius:12px;padding:1.2rem 1.4rem;margin-bottom:0.8rem;">'
            '<div style="font-family:Syne,sans-serif;font-size:13px;font-weight:700;color:#14141F;margin-bottom:0.8rem;">Quick Updates</div>'
            '<div style="display:flex;flex-direction:column;gap:8px;">'
        )
        for n in news_items[6:9]:
            timeline_html += (
                '<div style="display:flex;align-items:flex-start;gap:10px;">'
                f'<div style="width:60px;flex-shrink:0;font-size:10px;color:#9499A8;font-weight:600;padding-top:1px;">{n.get("date","") or "—"}</div>'
                '<div style="width:2px;background:#E3E5EA;flex-shrink:0;margin-top:4px;min-height:100%;"></div>'
                f'<div><div style="font-size:12px;font-weight:600;color:#14141F;">{n.get("title","")}</div>'
                f'<div style="font-size:11px;color:#5B5F6E;">{(n.get("description","") or "")[:90]}</div></div>'
                '</div>'
            )
        timeline_html += '</div></div>'
        st.markdown(timeline_html, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.link_button("Follow @pharos_network on X ↗", PHAROS_X_URL, use_container_width=True)
    with col2:
        if st.button("🔄 Refresh news", key="refresh_news"):
            if "pharos_news_cache" in st.session_state:
                del st.session_state["pharos_news_cache"]
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
            f'<span style="display:inline-block;font-size:11px;font-weight:500;color:#42475A;'
            f'background:#F2F3F8;border:1px solid #E3E5EA;border-radius:6px;'
            f'padding:3px 9px;margin-right:4px;">{t}</span>'
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
            f'<a href="{dapp["url"]}" target="_blank" '
            f'style="background:#FFFFFF;border:1px solid #ECEEF4;border-radius:16px;'
            f'padding:1.2rem 1.3rem;display:flex;flex-direction:column;align-items:center;gap:0;'
            f'text-align:center;text-decoration:none;box-shadow:0 1px 4px rgba(20,20,60,0.05);'
            f'transition:transform 200ms cubic-bezier(0.34,1.4,0.64,1),box-shadow 200ms ease,border-color 180ms ease;cursor:pointer;"'
            f' onmouseover="this.style.transform=\'translateY(-5px) scale(1.010)\';this.style.boxShadow=\'0 14px 40px rgba(26,26,255,0.13),0 0 0 1.5px rgba(26,26,255,0.22)\';"'
            f' onmouseout="this.style.transform=\'translateZ(0)\';this.style.boxShadow=\'0 1px 4px rgba(20,20,60,0.05)\';">'
            # Logo circle
            f'<div style="margin-bottom:0.75rem;">{logo_html}</div>'
            f'<div style="font-family:Syne,sans-serif;font-size:15px;font-weight:700;'
            f'color:#0C0C1A;margin-bottom:0.4rem;line-height:1.2;">{dapp["name"]}</div>'
            f'<div style="font-size:12px;color:#5B5F6E;line-height:1.6;'
            f'margin-bottom:0.75rem;flex:1;">{dapp["desc"]}</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px;">{tags_html}</div>'
            f'</a>'
        )
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

    st.link_button(
        "View all dApps on Pharos Testnet ↗",
        "https://testnet.pharosnetwork.xyz",
        use_container_width=False,
    )



# ── Footer (rendered on every page) ───────────────────────
    # ── Footer ────────────────────────────────────────────────────

# ═════════════════════════════════════════════
# PAGE: OCTOBOT PAYMENT AGENT
# ═════════════════════════════════════════════
elif st.session_state.page == "pay":

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
        import hashlib as _hl
        _tid = _hl.md5(f"{recipient}{amount_hex}{chain_id}{mode}".encode()).hexdigest()[:8]

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

    # ── Intent type legend ────────────────────────
    st.markdown(
        '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:1rem;">'
        '<div style="display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;'
        'color:#166016;background:#F0FFF4;border:1px solid #86EFAC;border-radius:20px;padding:5px 12px;">'
        '➡️ Send — "Send 5 PROS to 0x1234…"</div>'
        '<div style="display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;'
        'color:#1414E8;background:#EEF0FF;border:1px solid #C7D2FE;border-radius:20px;padding:5px 12px;">'
        '📦 Batch — "Send 1 PROS to 0xAAA…, 0xBBB…, 0xCCC…"</div>'
        '<div style="display:inline-flex;align-items:center;gap:6px;font-size:11.5px;font-weight:600;'
        'color:#7A5800;background:#FFFBEB;border:1px solid #FDE68A;border-radius:20px;padding:5px 12px;">'
        '✅ Approve — "Approve 0xFaroswap to spend 100 PROS"</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Network selector ──────────────────────────
    st.markdown('<div style="font-size:12px;font-weight:700;color:#7A7F96;margin-bottom:6px;letter-spacing:0.05em;text-transform:uppercase;">Select Network</div>', unsafe_allow_html=True)
    net_col1, net_col2, net_spacer = st.columns([1, 1, 3])
    with net_col1:
        mainnet_active = st.session_state.pay_network == "mainnet"
        if st.button(("● " if mainnet_active else "") + "🌐 Mainnet", key="pay_net_mainnet",
                     use_container_width=True, type="primary" if mainnet_active else "secondary"):
            if st.session_state.pay_network != "mainnet":
                st.session_state.pay_network = "mainnet"
                st.session_state.pay_parsed  = None
                st.session_state.pay_result  = None
                st.rerun()
    with net_col2:
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
    st.markdown(
        f'<div style="display:inline-flex;align-items:center;gap:7px;background:{net_badge_bg};'
        f'border:1px solid {net_badge_color}33;border-radius:10px;padding:5px 12px;margin-bottom:1rem;'
        f'font-size:12px;font-weight:600;color:{net_badge_color};">'
        f'{"🌐" if st.session_state.pay_network == "mainnet" else "🧪"} '
        f'{_net["label"]} · Chain ID {_net["chain_id_dec"]} · {_net.get("symbol","PROS")} · {_net["rpc"][:32]}…</div>',
        unsafe_allow_html=True,
    )

    # ── Wallet connect ────────────────────────────
    wallet_addr = st.session_state.get("wallet_address", "")
    if not wallet_addr:
        st.markdown(
            '<div style="background:#FFFFFF;border:1.5px solid rgba(26,26,255,0.2);border-radius:18px;'
            'padding:1.4rem 1.7rem;margin-bottom:1.2rem;'
            'box-shadow:0 6px 20px rgba(20,20,60,0.07),0 0 0 4px rgba(26,26,255,0.04);">'
            '<div style="display:flex;align-items:center;gap:10px;margin-bottom:0.6rem;">'
            '<div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#1414E8,#0C0C1A);'
            'display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0;">🔑</div>'
            '<div><div style="font-family:Syne,sans-serif;font-size:14px;font-weight:700;color:#0C0C1A;">Connect Your Wallet</div>'
            '<div style="font-size:11.5px;color:#7A7F96;margin-top:1px;">Paste your wallet address — read-only, no signing</div>'
            '</div></div>'
            '<div style="font-size:12.5px;color:#5B5F6E;line-height:1.55;margin-bottom:0.9rem;">'
            'Enter your Pharos wallet address to enable the Payment Agent.</div>',
            unsafe_allow_html=True,
        )
        _pwi = st.text_input("Your wallet address", placeholder="0x1234...your Pharos wallet address",
                              key="pay_inline_wallet_input", label_visibility="collapsed")
        pw1, pw2 = st.columns([2, 1])
        with pw1:
            if st.button("🔗 Connect Wallet", key="pay_inline_wallet_btn", use_container_width=True, type="primary"):
                if _pwi.strip().startswith("0x") and len(_pwi.strip()) == 42:
                    st.session_state.wallet_address = _pwi.strip()
                    st.session_state.wallet_data    = None
                    st.session_state.wallet_profile = None
                    st.rerun()
                else:
                    st.error("Enter a valid 0x… wallet address (42 characters).")
        with pw2:
            if st.button("🧠 Memory Ledger", key="pay_go_memory", use_container_width=True):
                st.session_state.page = "memory"; st.rerun()
        st.markdown('</div><div style="margin-bottom:1rem;"></div>', unsafe_allow_html=True)
    else:
        _wa = wallet_addr; _ws = _wa[:6] + "…" + _wa[-4:]
        wcol1, wcol2 = st.columns([4, 1])
        with wcol1:
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px;background:linear-gradient(90deg,#0C0C1A,#1414E8);'
                f'border-radius:12px;padding:0.7rem 1.1rem;margin-bottom:0.7rem;">'
                f'<span style="font-size:16px;">🔗</span><div>'
                f'<div style="font-size:9.5px;color:rgba(255,255,255,0.5);font-weight:600;letter-spacing:0.07em;text-transform:uppercase;">Connected Wallet</div>'
                f'<div style="font-size:13px;color:#fff;font-weight:700;font-family:monospace;">{_ws}</div>'
                f'</div></div>', unsafe_allow_html=True)
        with wcol2:
            if st.button("✕ Disconnect", key="pay_disconnect_wallet", use_container_width=True):
                st.session_state.wallet_address = ""
                st.session_state.wallet_data    = None
                st.session_state.wallet_profile = None
                st.session_state.pay_parsed     = None
                st.session_state.pay_result     = None
                st.rerun()

    # ── Example prompts ───────────────────────────
    EXAMPLE_PROMPTS = [
        ("➡️ Send",    "Send 10 PROS to 0xAbCd1234567890AbCd1234567890AbCd12345678"),
        ("📦 Batch",   "Send 1 PROS each to 0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA, 0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB, 0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"),
        ("✅ Approve", "Approve 0xFaroswap1111111111111111111111111111111111 to spend 100 PROS"),
    ]
    st.markdown('<div style="font-size:12px;font-weight:600;color:#7A7F96;margin-bottom:6px;">Try an example:</div>', unsafe_allow_html=True)
    ep_cols = st.columns(3)
    for i, (ep_label, ep_text) in enumerate(EXAMPLE_PROMPTS):
        with ep_cols[i]:
            if st.button(ep_label, key=f"pay_ep_{i}", use_container_width=True):
                st.session_state.pay_intent_raw = ep_text
                st.session_state.pay_parsed     = None
                st.session_state.pay_confirmed  = False
                st.session_state.pay_result     = None
                st.rerun()

    # ── Input + Parse ─────────────────────────────
    st.markdown('<div style="margin-top:0.8rem;"></div>', unsafe_allow_html=True)
    pay_input = st.text_input(
        "Payment instruction in plain English",
        value=st.session_state.pay_intent_raw,
        placeholder='e.g. "Send 5 PROS to 0xAbCd…" or "Approve 0xContract to spend 100 PROS"',
        key="pay_text_input",
        label_visibility="collapsed",
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
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{wallet_addr or "⚠️ Not connected"}</div>'
                + (f'<div style="font-size:11px;color:{"#E5484D" if insufficient else "#7A7F96"};margin-top:3px;">Balance: {sender_balance:,.4f} {_sym}' + (' — <strong style="color:#E5484D;">Insufficient</strong>' if insufficient else '') + '</div>' if sender_balance is not None else '') +
                '</div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:6px;">To</div>'
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{recipient}</div>'
                '</div>'
                + (f'<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                   f'<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Reason</div>'
                   f'<div style="font-size:12px;color:#0C0C1A;">{reason}</div></div>' if reason else '') +
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
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{wallet_addr or "⚠️ Not connected"}</div>'
                + (f'<div style="font-size:11px;color:{"#E5484D" if insufficient else "#7A7F96"};margin-top:3px;">Balance: {sender_balance:,.4f} {_sym}' + (' — <strong style="color:#E5484D;">Insufficient</strong>' if insufficient else '') + '</div>' if sender_balance is not None else '') +
                '</div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:8px;">Recipients</div>' +
                "".join([f'<div style="font-size:11.5px;font-weight:600;color:#0C0C1A;word-break:break-all;padding:4px 0;border-bottom:1px solid #ECEEF4;">'
                         f'<span style="color:#1414E8;font-weight:700;">{i+1}.</span> {addr} '
                         f'<span style="color:#7A7F96;">({amount_each:,.4f} {_sym})</span></div>'
                         for i, addr in enumerate(recipients)]) +
                '</div>'
                + (f'<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                   f'<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Reason</div>'
                   f'<div style="font-size:12px;color:#0C0C1A;">{reason}</div></div>' if reason else '') +
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
                f'<div style="font-size:12px;font-weight:600;color:#0C0C1A;word-break:break-all;">{wallet_addr or "⚠️ Not connected"}</div>'
                + (f'<div style="font-size:11px;color:#7A7F96;margin-top:3px;">Balance: {sender_balance:,.4f} {_sym}</div>' if sender_balance is not None else '') +
                '</div>'
                '<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                '<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:6px;">Spender (Contract being approved)</div>'
                f'<div style="font-size:12px;font-weight:600;color:#1414E8;word-break:break-all;">{spender}</div>'
                '</div>'
                + (f'<div style="background:#F9F9FC;border-radius:10px;padding:0.75rem 0.9rem;margin-bottom:0.9rem;">'
                   f'<div style="font-size:10px;font-weight:600;letter-spacing:0.06em;text-transform:uppercase;color:#7A7F96;margin-bottom:3px;">Note</div>'
                   f'<div style="font-size:12px;color:#0C0C1A;">{reason}</div></div>' if reason else '') +
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
    _pay_tx   = st.query_params.get("pay_tx", "")
    _pay_to   = st.query_params.get("pay_to", "")
    _pay_amt  = st.query_params.get("pay_amt", "")
    _pay_net  = st.query_params.get("pay_net", "mainnet")
    _pay_mode = st.query_params.get("pay_mode", "send")
    if _pay_tx and _pay_to and _pay_amt:
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
            f'<div style="font-size:12.5px;color:#166534;margin-bottom:4px;"><strong>Address:</strong> {r["recipient"]}</div>'
            f'<div style="font-size:12.5px;color:#166534;margin-bottom:4px;"><strong>Network:</strong> {r.get("network","Pharos")}</div>'
            f'<div style="font-size:12px;color:#15803D;word-break:break-all;margin-bottom:4px;"><strong>Tx Hash:</strong> {r["tx_hash"]}</div>'
            f'<a href="{_exp}/tx/{r["tx_hash"]}" target="_blank" '
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
                f'{_mode_icon} {_h_mode} · {h["amount"]:,.4f} {_h_sym} → {h["recipient"][:16]}…</div>'
                f'<div style="font-size:11px;color:#7A7F96;margin-top:2px;">{h.get("timestamp","")} · {_h_net} · {tx_short}</div></div>'
                f'<a href="{_h_exp}/tx/{h["tx_hash"]}" target="_blank" '
                'style="font-size:11.5px;font-weight:600;color:#1A1AFF;white-space:nowrap;text-decoration:none;">View ↗</a>'
                '</div>',
                unsafe_allow_html=True,
            )


st.markdown('<div style="margin-top:2rem;"></div>', unsafe_allow_html=True)
st.markdown(
    
    '<div style="text-align:center;padding:1rem 0 0.5rem 0;'
    'border-top:1px solid #D0D3E0;margin-top:1rem;">'
    '<span style="font-size:12px;color:#7A7F96;">Built by&nbsp;</span>'
    '<strong style="font-size:12px;color:#0C0C1A;">Echo</strong>'
    '<span style="font-size:12px;color:#7A7F96;">&nbsp;·&nbsp;</span>'
    '<span style="font-size:12px;color:#7A7F96;">Discord:&nbsp;</span>'
    '<strong style="font-size:12px;color:#0C0C1A;">@echoplex99</strong>'
    '<span style="font-size:12px;color:#7A7F96;">&nbsp;·&nbsp;</span>'
    '<a href="https://x.com/isharik99" target="_blank" '
    'style="font-size:12px;font-weight:600;color:#1A1AFF;text-decoration:none;">@isharik99 on X ↗</a>'
    '<span style="font-size:12px;color:#7A7F96;">&nbsp;·&nbsp;</span>'
    '<a href="https://github.com/isharik/Pharos-Octobot" target="_blank" '
    'style="font-size:12px;font-weight:600;color:#1A1AFF;text-decoration:none;">'
    'GitHub ↗</a>'
    '</div>',
    unsafe_allow_html=True,
)