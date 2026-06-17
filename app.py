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
    {"name": "OKX",      "url": "https://www.okx.com/trade-spot/pros-usdt?channelid=35427002",                 "desc": "PROS/USDT · Highest Volume"},
    {"name": "Bitget",   "url": "https://www.bitget.com/spot/PROSUSDT?channelCode=y53z&vipCode=s3t2",                     "desc": "PROS/USDT"},
    {"name": "KuCoin",   "url": "https://www.kucoin.com/trade/PROS-USDT?rcode=rPH7VCS",                   "desc": "PROS/USDT"},
    {"name": "Upbit",    "url": "https://www.upbit.com/exchange?code=CRIX.UPBIT.KRW-PROS",     "desc": "PROS/USDT · KRW · BTC"},
    {"name": "Coinbase", "url": "https://exchange.coinbase.com/trade/PROS-USD",   "desc": "PROS/USDT"},
]

CAMPAIGNS = [
    {
        "title": "AI Agent Carnival — Phase 1",
        "tag":   "LIVE · Skill Hackathon",
        "desc":  "Build reusable Skill modules on Pharos and win from a 150,000 PROS prize pool. Phase 1 closes Jun 15.",
        "link":  "https://dorahacks.io/hackathon/pharos-phase1",
        "cta":   "Submit your Skill",
        "color": "#1A1AFF",
    },
    {
        "title": "Pharos Expedition Season 2",
        "tag":   "LIVE · Post Mainnet Voyage",
        "desc":  "Showcase your skills and support on X and Discord to participate.",
        "link":  "https://www.notion.so/Pharos-Expedition-Season-2-3578ec314f7580488f69ca722cc31cf9",
        "cta":   "Join here",
        "color": "#1A1AFF",
    },
    {
        "title": "Storyteller Program 2.0",
        "tag":   "LIVE · Content Creators",
        "desc":  "Create impactful educational content about Pharos and earn perks. Open to writers, educators, meme creators.",
        "link":  "https://silken-muskox-24e.notion.site/pharos-storyteller-program-2-0",
        "cta":   "Apply now",
        "color": "#1A1AFF",
    },
    {
        "title": "Pharos Inner Circle ",
        "tag":   "# Make a Million, Become a PRO",
        "desc":  "Merit-based initiative designed to recognize and reward the most committed Pharos supporters",
        "link":  "https://app.notion.com/p/Pharos-Inner-Circle-Make-a-Million-Become-a-PRO-3808ec314f75806e960bcb15e147c10d",
        "cta":   "Grow with Us",
        "color": "#1A1AFF",
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
        "logo":  "https://www.google.com/s2/favicons?domain=bitverse.zone&sz=64",
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
        "logo":  "https://www.google.com/s2/favicons?domain=zenithfinance.xyz&sz=64",
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
        "logo":  "https://www.google.com/s2/favicons?domain=spout.finance&sz=64",
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


def render_octo_fab() -> None:
    """Fixed bottom-right animated octopus scroll-to-bottom FAB."""
    components.html(
        "<style>"
        "#ocfab{position:fixed;bottom:80px;right:20px;width:54px;height:54px;"
        "cursor:pointer;z-index:99999;animation:ocbo 3s ease-in-out infinite;"
        "filter:drop-shadow(0 4px 14px rgba(26,26,255,0.4));}"
        "#ocfab:hover{animation-play-state:paused;}"
        "@keyframes ocbo{0%,100%{transform:translateY(0);}50%{transform:translateY(-8px);}}"
        "</style>"
        '<svg id="ocfab" viewBox="0 0 100 112" xmlns="http://www.w3.org/2000/svg"'
        ' title="Scroll to bottom"'
        " onclick=\"window.parent.scrollTo({top:window.parent.document.body.scrollHeight,behavior:'smooth'})\">"
        '<ellipse cx="50" cy="42" rx="32" ry="30" fill="#1A1AFF"/>'
        '<ellipse cx="42" cy="32" rx="10" ry="7" fill="rgba(255,255,255,0.2)" transform="rotate(-15,42,32)"/>'
        '<circle cx="38" cy="36" r="8" fill="white"/>'
        '<circle cx="62" cy="36" r="8" fill="white"/>'
        '<circle cx="40" cy="37" r="4.5" fill="#0A0A2E"/>'
        '<circle cx="63" cy="37" r="4.5" fill="#0A0A2E"/>'
        '<circle cx="42" cy="35" r="1.5" fill="white"/>'
        '<circle cx="65" cy="35" r="1.5" fill="white"/>'
        '<path d="M40 48 Q50 56 60 48" stroke="white" stroke-width="2.5" fill="none" stroke-linecap="round"/>'
        '<path d="M22 66 Q14 82 20 96 Q24 102 28 96 Q30 84 24 68" fill="#1A1AFF"/>'
        '<path d="M34 70 Q28 88 34 102 Q38 106 42 102 Q42 88 36 72" fill="#1A1AFF"/>'
        '<path d="M50 72 Q48 90 50 106 Q53 110 56 106 Q58 90 52 72" fill="#1A1AFF"/>'
        '<path d="M65 70 Q68 88 64 102 Q60 106 57 102 Q58 88 63 72" fill="#1A1AFF"/>'
        '<path d="M78 66 Q86 82 80 96 Q76 102 72 96 Q70 84 76 68" fill="#1A1AFF"/>'
        '<circle cx="24" cy="96" r="3.5" fill="#6B8CFF"/>'
        '<circle cx="38" cy="102" r="3.5" fill="#6B8CFF"/>'
        '<circle cx="53" cy="106" r="3.5" fill="#6B8CFF"/>'
        '<circle cx="60" cy="102" r="3.5" fill="#6B8CFF"/>'
        '<circle cx="76" cy="96" r="3.5" fill="#6B8CFF"/>'
        '<path d="M44 50 L50 59 L56 50" stroke="white" stroke-width="2.8" fill="none"'
        ' stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>",
        height=1,
    )

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
    --bg:   #D7DCE6;
    --bg1:  #F1F4F9;
    --bg2:  #E7ECF5;
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
    background:var(--bg)!important;
    background-image:
        radial-gradient(ellipse 70% 45% at 50% -5%,rgba(26,26,255,0.07) 0%,transparent 50%),
        radial-gradient(ellipse 35% 25% at 85% 70%,rgba(26,26,255,0.03) 0%,transparent 50%),
        radial-gradient(ellipse 25% 20% at 10% 80%,rgba(107,140,255,0.04) 0%,transparent 50%),
        radial-gradient(circle 2px at 0 0,rgba(26,26,255,0.12) 0%,transparent 100%),
        repeating-linear-gradient(0deg,  rgba(26,26,255,0.03) 0px,rgba(26,26,255,0.03) 1px,transparent 1px,transparent 64px),
        repeating-linear-gradient(90deg, rgba(26,26,255,0.03) 0px,rgba(26,26,255,0.03) 1px,transparent 1px,transparent 64px)
        !important;
    background-size:auto,auto,auto,64px 64px,100% 100%,100% 100%!important;
    background-attachment:fixed!important;
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
}
/* Center markdown blocks that contain hero */
[data-testid="stMarkdownContainer"] {
    width: 100%;
}

/* ── TOP NAV ─── */
.octo-nav{
    display:flex;align-items:center;gap:0;
    background:rgba(255,255,255,0.92);
    backdrop-filter:blur(12px);
    border-bottom:1px solid var(--border);
    padding:0 1.5rem;
    height:52px;
    position:sticky;top:0;z-index:100;
    box-shadow:0 1px 4px rgba(20,20,31,0.05);
}
.octo-nav-logo{
    display:flex;align-items:center;gap:8px;
    font-family:var(--fd);font-size:15px;font-weight:700;color:var(--t1);
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

/* nav buttons handled via Streamlit — override to look inline */
.nav-wrap .stButton>button{
    background:transparent!important;
    border:none!important;
    border-radius:6px!important;
    font-family:var(--fb)!important;
    font-size:18px!important;
    font-weight:800!important;
    color:#000000!important;
    opacity:1!important;
    letter-spacing:-0.01em!important;
    padding:0.3rem 0.8rem!important;
    height:auto!important;
    text-align:center!important;
    transition:all 0.12s ease!important;
}
.nav-wrap .stButton>button:hover{
    background:var(--subtle)!important;
    color:var(--blue)!important;
}
.nav-wrap.active .stButton>button{
    color:var(--blue)!important;
    font-weight:700!important;
    background:var(--subtle)!important;
}
.nav-cta .stButton>button{
    background:var(--blue)!important;
    color:#fff!important;
    border-radius:20px!important;
    font-size:13px!important;
    font-weight:600!important;
    padding:0.3rem 1rem!important;
    letter-spacing:0.02em!important;
}
.nav-cta .stButton>button:hover{background:var(--blue2)!important;}

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
    width:90px;height:90px;
    display:inline-flex;align-items:center;justify-content:center;
    margin-bottom:1.2rem;
}
.hero-logo-wrap img,.hero-logo-wrap .fi{
    width:52px;height:52px;border-radius:50%;
    position:relative;z-index:3;
    filter:drop-shadow(0 2px 12px rgba(26,26,255,0.3));
}
.hero-logo-wrap .fi{font-size:36px;line-height:52px;}
.hero-ring{
    position:absolute;border-radius:50%;border:1.5px solid var(--blue);
    opacity:0;animation:hr-pulse 2.8s ease-out infinite;
}
.hero-ring.r1{width:90px;height:90px;animation-delay:0s;}
.hero-ring.r2{width:90px;height:90px;animation-delay:0.9s;}
.hero-ring.r3{width:90px;height:90px;animation-delay:1.8s;}
@keyframes hr-pulse{
    0%{transform:scale(0.5);opacity:0.5;}
    100%{transform:scale(1.6);opacity:0;}
}
.hero-orbit{
    position:absolute;inset:-18px;border-radius:50%;
    border:1px dashed rgba(26,26,255,0.18);
    animation:orbit-spin 12s linear infinite;
}
.hero-orbit::before{
    content:'';position:absolute;width:7px;height:7px;border-radius:50%;
    background:var(--blue);top:-3px;left:50%;transform:translateX(-50%);
    box-shadow:0 0 8px var(--blue);
}
.hero-eyebrow{
    display:inline-flex;align-items:center;gap:6px;
    font-size:10px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;
    color:var(--blue);background:var(--subtle);border:1px solid rgba(26,26,255,0.18);
    border-radius:20px;padding:3px 12px;margin-bottom:1rem;margin-top:0.8rem;
    align-self:center;
}
.hero-eyebrow .live-dot{
    width:6px;height:6px;border-radius:50%;background:var(--green);
    box-shadow:0 0 5px var(--green);animation:blink 2s ease-in-out infinite;
}
@keyframes blink{0%,100%{opacity:1}50%{opacity:0.2}}
.hero-title{
    font-family:var(--fd);font-size:2.4rem;font-weight:800;
    color:var(--t1);letter-spacing:-0.03em;line-height:1.08;
    margin:0 auto 0.6rem auto;
    text-align:center;
    width:100%;
}
.hero-title span{background:linear-gradient(90deg,#1A1AFF,#6B6BFF);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}
.hero-sub{
    font-size:1rem;color:var(--t2);line-height:1.6;
    max-width:520px;margin:0 auto 1.8rem auto;
    text-align:center;
}
.hero-actions{display:flex;align-items:center;justify-content:center;gap:10px;flex-wrap:wrap;}
.hbtn{
    display:inline-flex;align-items:center;gap:6px;
    font-family:var(--fb);font-size:13px;font-weight:600;
    padding:0.6rem 1.3rem;border-radius:8px;
    text-decoration:none;cursor:pointer;transition:all 0.15s ease;border:none;
}
.hbtn-primary{background:var(--blue);color:#fff;}
.hbtn-primary:hover{background:var(--blue2);color:#fff;text-decoration:none;}
.hbtn-ghost{background:var(--bg1);color:var(--t1);border:1px solid var(--border);}
.hbtn-ghost:hover{border-color:var(--blue);color:var(--blue);background:var(--subtle);}

/* ── DOCS BADGE BANNER ── */
.docs-banner{
    display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;
    background:var(--t1);border-radius:10px;padding:0.65rem 1.1rem;margin-bottom:1rem;
}
.docs-banner-left{display:flex;align-items:center;gap:8px;}
.docs-banner-icon{font-size:14px;color:#fff;}
.docs-banner-text{font-size:12px;color:rgba(255,255,255,0.7);}
.docs-banner-text strong{color:#fff;font-weight:600;}
.docs-banner-link{
    display:inline-flex;align-items:center;gap:4px;
    font-size:11px;font-weight:600;letter-spacing:0.05em;
    background:var(--blue);color:#fff;border-radius:20px;
    padding:3px 12px;text-decoration:none;white-space:nowrap;
}
.docs-banner-link:hover{background:var(--blue2);color:#fff;}

/* ── NAV QUICK PILLS ── */
.quick-nav{
    display:flex;gap:6px;flex-wrap:wrap;margin-bottom:1rem;
}
.qpill{
    display:inline-flex;align-items:center;gap:5px;
    font-size:12px;font-weight:500;
    background:var(--bg1);border:1px solid var(--border);
    border-radius:20px;padding:4px 12px;
    text-decoration:none;color:var(--t2);
    transition:all 0.12s ease;cursor:pointer;
}
.qpill:hover{border-color:var(--blue);color:var(--blue);background:var(--subtle);}
.qpill .dot{width:5px;height:5px;border-radius:50%;background:var(--green);flex-shrink:0;}

/* ── SECTION HEADER (Campaigns / Updates) ── */
.section-dark{
    background:linear-gradient(135deg,#0D0D1A 0%,#0A0A2E 60%,#0D1540 100%);
    border-radius:14px;padding:2.5rem 2rem 2rem 2rem;
    margin-bottom:1.2rem;text-align:center;position:relative;overflow:hidden;
}
.section-dark::before{
    content:'';position:absolute;inset:0;
    background:radial-gradient(ellipse 80% 60% at 50% -10%,rgba(26,26,255,0.3) 0%,transparent 60%);
    pointer-events:none;
}
.section-eyebrow{
    display:inline-flex;align-items:center;gap:6px;
    font-size:9px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;
    color:#64BFFF;margin-bottom:0.6rem;
}
.section-eyebrow .drop{font-size:12px;}
.section-h{
    font-family:var(--fd);font-size:2rem;font-weight:800;
    color:#FFFFFF;letter-spacing:-0.02em;margin:0 0 0.5rem 0;
}
.section-sub{font-size:0.9rem;color:rgba(255,255,255,0.55);line-height:1.5;}
.section-sub a{color:#64BFFF;text-decoration:none;}

/* ── CAMPAIGN CARDS ── */
.camp-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;margin-bottom:1.2rem;}
.camp-card{
    background:var(--bg1);border:1px solid var(--border);
    border-radius:12px;padding:1.1rem 1.2rem;
    transition:box-shadow 0.15s ease,border-color 0.15s ease;
    box-shadow:0 1px 3px rgba(20,20,31,0.04);
    display:flex;flex-direction:column;gap:8px;
}
.camp-card:hover{border-color:var(--blue);box-shadow:0 4px 16px rgba(26,26,255,0.08);}
.camp-tag{
    display:inline-flex;align-items:center;gap:4px;
    font-size:9px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;
    background:rgba(26,26,255,0.07);border:1px solid rgba(26,26,255,0.18);
    color:var(--blue);border-radius:20px;padding:2px 8px;align-self:flex-start;
}
.camp-title{font-family:var(--fd);font-size:14px;font-weight:700;color:var(--t1);line-height:1.3;}
.camp-desc{font-size:12px;color:var(--t2);line-height:1.6;flex:1;}
.camp-link{
    display:inline-flex;align-items:center;gap:4px;
    font-size:11px;font-weight:600;color:var(--blue);
    text-decoration:none;align-self:flex-start;margin-top:2px;
}
.camp-link:hover{text-decoration:underline;}

/* ── NEWS CARDS ── */
.news-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-bottom:1.2rem;}
.news-card{
    background:var(--bg1);border:1px solid var(--border);
    border-radius:12px;padding:1rem 1.1rem;
    box-shadow:0 1px 3px rgba(20,20,31,0.04);
    transition:box-shadow 0.15s ease;
    display:flex;flex-direction:column;gap:6px;
}
.news-card:hover{box-shadow:0 4px 16px rgba(26,26,255,0.07);}
.news-source{font-size:9px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;color:var(--t3);}
.news-title{font-size:13px;font-weight:600;color:var(--t1);line-height:1.4;}
.news-title a{color:var(--t1);text-decoration:none;}
.news-title a:hover{color:var(--blue);}
.news-desc{font-size:11px;color:var(--t2);line-height:1.55;}
.news-date{font-size:10px;color:var(--t3);}

/* ── TRADE CEX ── */
.cex-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:10px;margin-bottom:1rem;}
.cex-card{
    background:var(--bg1);border:1px solid var(--border);border-radius:10px;
    padding:0.9rem 1rem;text-align:center;
    box-shadow:0 1px 2px rgba(20,20,31,0.04);
    transition:all 0.12s ease;
}
.cex-card:hover{border-color:var(--blue);box-shadow:0 4px 12px rgba(26,26,255,0.08);}
.cex-name{font-family:var(--fd);font-size:15px;font-weight:700;color:var(--t1);margin-bottom:3px;}
.cex-pair{font-size:10px;color:var(--t3);letter-spacing:0.05em;margin-bottom:8px;}
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
    text-align:left!important;transition:all 0.12s ease!important;line-height:1.4!important;
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
    background:linear-gradient(135deg,#080812 0%,#0A0A2E 60%,#0C1235 100%);
    border-radius:14px;padding:1.8rem 2rem 1.4rem 2rem;
    margin-bottom:1rem;text-align:center;position:relative;overflow:hidden;
}
.dapp-section-hdr::before{
    content:'';position:absolute;inset:0;
    background:radial-gradient(ellipse 80% 60% at 50% -10%,rgba(26,26,255,0.28) 0%,transparent 60%);
    pointer-events:none;
}
.dapp-grid{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(280px,1fr));
    gap:16px;margin-bottom:1.4rem;
}
.dapp-card{
    background:#FFFFFF;
    border:1px solid #ECEEF4;
    border-radius:16px;
    padding:1.3rem 1.4rem;
    box-shadow:0 1px 4px rgba(20,20,60,0.05);
    transition:all 0.18s cubic-bezier(0.4,0,0.2,1);
    cursor:pointer;
    display:flex;flex-direction:column;gap:0;
    text-decoration:none;
}
.dapp-card:hover{
    border-color:#C8D0FF;
    box-shadow:0 8px 28px rgba(26,26,255,0.1);
    transform:translateY(-3px);
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
    padding:1.8rem 0 1.5rem 0!important;
}
.hero-logo-wrap{margin-bottom:0.8rem!important;}
.hero-title{font-size:2.6rem!important;letter-spacing:-0.04em!important;}
.hero-sub{font-size:0.95rem!important;margin-bottom:1.3rem!important;}

/* ── MICRO INTERACTIONS ── */
.camp-card,.cex-card,.dapp-card,.news-card{
    transition:all 0.18s cubic-bezier(0.4,0,0.2,1)!important;
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

/* ── OCTOPUS FAB ── */
#ocfab{
    position:fixed;bottom:80px;right:20px;
    width:54px;height:54px;
    cursor:pointer;z-index:99999;
    animation:ocbo 3s ease-in-out infinite;
    filter:drop-shadow(0 4px 14px rgba(26,26,255,0.4));
}
#ocfab:hover{animation-play-state:paused;filter:drop-shadow(0 6px 20px rgba(26,26,255,0.6));}
@keyframes ocbo{0%,100%{transform:translateY(0);}50%{transform:translateY(-8px);}}

/* ── DOWNLOAD BTN ── */
.dl-btn{
    display:inline-flex;align-items:center;gap:5px;
    font-size:11px;font-weight:600;
    padding:5px 12px;border-radius:8px;
    border:1px solid #D0D3E0;background:#FFFFFF;color:#0C0C1A;
    cursor:pointer;font-family:'DM Sans',sans-serif;text-decoration:none;
}
</style>
""", unsafe_allow_html=True)


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
]

nav_cols = st.columns([1.2, 0.9, 0.9, 0.9, 0.9, 0.9, 0.9, 0.1, 1.1])

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

with nav_cols[8]:
    st.markdown('<div class="nav-cta">', unsafe_allow_html=True)
    st.link_button("↗ Pharos Network", PHAROS_MAIN_URL, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<hr style="border:none;border-top:1px solid #E3E5EA;margin:0 0 1rem 0;">', unsafe_allow_html=True)

# ═════════════════════════════════════════════
# PAGE: HOME
# ═════════════════════════════════════════════
if st.session_state.page == "home":

    # ── Hero ──────────────────────────────────
    if logo_b64:
        hero_logo = (
            '<div class="hero-logo-wrap">'
            '<div class="hero-ring r1"></div>'
            '<div class="hero-ring r2"></div>'
            '<div class="hero-ring r3"></div>'
            '<div class="hero-orbit"></div>'
            '<img src="' + logo_b64 + '" />'
            '</div>'
        )
    else:
        hero_logo = (
            '<div class="hero-logo-wrap">'
            '<div class="hero-ring r1"></div><div class="hero-ring r2"></div><div class="hero-ring r3"></div>'
            '<div class="hero-orbit"></div>'
            '<span class="fi">🐙</span>'
            '</div>'
        )

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
        + hero_logo +
        '<div class="hero-eyebrow"><div class="live-dot"></div>Live · Pharos Network AI Hub</div>'
        '<h1 class="hero-title">Your <span>Pharos</span> Command Center</h1>'
        '<p class="hero-sub">Ask OctoBot anything about Pharos, track live $PROS price, explore active campaigns, read the latest updates, and trade — all in one place.</p>'
        '<div style="margin-bottom:1.2rem;">' + price_pill + '</div>'
        '<div class="hero-actions">'
        '<a class="hbtn hbtn-primary" href="?nav=chat" onclick="void(0)">💬 Chat with OctoBot</a>'
        '<a class="hbtn hbtn-ghost" href="' + PHAROS_DOCS_URL + '" target="_blank">📄 Pharos Docs ↗</a>'
        '<a class="hbtn hbtn-ghost" href="' + PHAROS_DISCORD_URL + '" target="_blank">Discord ↗</a>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # hero button handlers (JS links don't trigger Streamlit reruns — use pills below)
    hcol1, hcol2, hcol3 = st.columns(3)
    with hcol1:
        if st.button("💬 Multilingual", key="home_chat", use_container_width=True):
            st.session_state.page = "None"; st.rerun()
    with hcol2:
        if st.button("🚀 50+ Languages", key="home_camp", use_container_width=True):
            st.session_state.page = "None"; st.rerun()
    with hcol3:
        if st.button("📊 Real time Markets", key="home_trade", use_container_width=True):
            st.session_state.page = "https://github.com/isharik/Pharos-Octobot"; st.rerun()

    st.markdown('<div style="margin-bottom:1rem;"></div>', unsafe_allow_html=True)

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
    camp_cols = st.columns(2)
    for i, c in enumerate(CAMPAIGNS[:2]):
        with camp_cols[i % 2]:
            st.markdown(
                '<div class="camp-card">'
                '<div class="camp-tag">' + c["tag"] + '</div>'
                '<div class="camp-title">' + c["title"] + '</div>'
                '<div class="camp-desc">' + c["desc"] + '</div>'
                '<a class="camp-link" href="' + c["link"] + '" target="_blank">' + c["cta"] + ' ↗</a>'
                '</div>',
                unsafe_allow_html=True,
            )
    if st.button("View all campaigns →", key="home_all_camp"):
        st.session_state.page = "campaigns"; st.rerun()


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

        # Live price card
        p = price_data
        if p.get("price_usd"):
            chg     = p.get("change_24h") or 0
            chg_col = "#1FA855" if chg >= 0 else "#E5484D"
            chg_sym = "▲" if chg >= 0 else "▼"
            st.markdown(
                '<div style="background:#0C0C1A;border-radius:10px;padding:0.8rem 1rem;margin-bottom:0.9rem;">'
                '<div style="font-size:9px;font-weight:700;letter-spacing:0.12em;'
                'text-transform:uppercase;color:rgba(255,255,255,0.4);margin-bottom:5px;">$PROS Live Price</div>'
                '<div style="font-size:22px;font-weight:800;font-family:Syne,sans-serif;'
                'color:#FFFFFF;line-height:1.1;letter-spacing:-0.02em;">$' + f'{p["price_usd"]:.4f}' + '</div>'
                '<div style="font-size:12px;font-weight:600;color:' + chg_col + ';margin-top:3px;">'
                + chg_sym + f' {abs(chg):.2f}% 24h</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="background:#0C0C1A;border-radius:10px;padding:0.7rem 0.9rem;'
                'margin-bottom:0.9rem;font-size:11px;color:rgba(255,255,255,0.4);">$PROS loading…</div>',
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
        st.session_state.show_sources = st.toggle("📎 Show sources", value=st.session_state.show_sources)
        st.session_state.voice_reply  = st.toggle("🔊 Read aloud",   value=st.session_state.voice_reply)

        st.markdown('<hr style="border:none;border-top:1px solid #D0D3E0;margin:0.7rem 0;">', unsafe_allow_html=True)

        # Knowledge base stats
        st.markdown(
            '<div style="font-size:10px;font-weight:700;color:#0C0C1A;'
            'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:5px;">Knowledge Base</div>'
            '<div style="font-size:13px;color:#42475A;margin-bottom:0.6rem;">'
            '<strong style="color:#0C0C1A;">' + str(chunk_count) + '</strong> document chunks</div>',
            unsafe_allow_html=True,
        )

        st.markdown('<hr style="border:none;border-top:1px solid #D0D3E0;margin:0.7rem 0;">', unsafe_allow_html=True)

        # Example prompts
        st.markdown(
            '<div style="font-size:10px;font-weight:700;color:#0C0C1A;'
            'letter-spacing:0.08em;text-transform:uppercase;margin-bottom:6px;">Ask OctoBot</div>',
            unsafe_allow_html=True,
        )
        for q in ["What is Pharos?", "What are SPNs?", "How does Native Restaking work?",
                  "What is the PROS token?", "How do I build on Pharos?", "What is RWA?"]:
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

    # ── Welcome card ───────────────────────────
    if not st.session_state.messages:
        mode_note = ("Docs + General mode: OctoBot answers from docs first, then uses Gemini for anything not in documentation."
                     if st.session_state.chat_mode == "general"
                     else "Docs only mode: OctoBot answers strictly from verified Pharos documentation.")
        st.markdown(
            '<div class="welcome-card">'
            '<h3>Welcome to OctoBot</h3>'
            '<p>Ask me anything about Pharos Network — SPNs, Native Restaking, RWA, consensus, '
            'building on Pharos, or the $PROS token. <em>' + mode_note + '</em></p>'
            '<div class="tag-row">'
            '<span class="tag">SPNs</span><span class="tag">L1 Architecture</span>'
            '<span class="tag">Native Restaking</span><span class="tag">RWA</span>'
            '<span class="tag">DeFi</span><span class="tag">Build on Pharos</span>'
            '<span class="tag">$PROS Token</span><span class="tag">🌐 Multilingual</span>'
            '</div></div>'

            '<p class="notice" style="color:#000000; font-weight:700;">⚠️ If chat is not responding or not loading, API usage may be exhausted. '
             'Run OctoBot locally with your own API key to continue.</p>'

            '</div>',
            unsafe_allow_html=True,
        )

    # ── Chat history ───────────────────────────
    for i, msg in enumerate(st.session_state.messages):
        av = "👤" if msg["role"] == "user" else "🐙"
        with st.chat_message(msg["role"], avatar=av):
            st.markdown(msg["content"])
            if msg["role"] == "assistant":
                if st.button("🔊", key="rh_" + str(i), help="Read aloud"):
                    speak_text(msg["content"])
                if st.session_state.show_sources:
                    src_idx = i // 2
                    if src_idx < len(st.session_state.sources_history):
                        srcs = st.session_state.sources_history[src_idx]
                        if srcs:
                            with st.expander("Sources · " + str(len(srcs)), expanded=False):
                                for s in srcs:
                                    st.markdown(
                                        '<div class="source-card"><strong>' + s["title"] + '</strong>'
                                        '<a href="' + s["url"] + '" target="_blank">' + s["url"] + '</a></div>',
                                        unsafe_allow_html=True,
                                    )

    # ── Voice input widget ─────────────────────
    if False:  # disabled until mic works reliably — remove "if False:" to re-enable
        components.html("""
        <div style="font-family:'DM Sans',sans-serif;margin-bottom:6px;">
          <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
            <button id="m" style="width:28px;height:28px;border-radius:50%;border:1px solid #D6D9E0;background:#fff;color:#1A1AFF;cursor:pointer;font-size:13px;flex-shrink:0;">🎙</button>
            <span id="ms" style="font-size:11px;color:#5B5F6E;">Tap to speak</span>
            <button id="ms2" style="display:none;padding:3px 10px;border-radius:6px;border:1px solid #1A1AFF;background:#1A1AFF;color:#fff;cursor:pointer;font-size:11px;font-weight:600;">Send →</button>
          </div>
        </div>
        <script>(function(){
        const btn=document.getElementById('m'),st=document.getElementById('ms'),sb=document.getElementById('ms2');
        const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
        if(!SR){st.innerText='Voice needs Chrome/Edge';btn.style.opacity='0.4';return;}
        const r=new SR();r.continuous=true;r.interimResults=true;r.maxAlternatives=1;r.lang=navigator.language||'en-US';
        let on=false,ft='',timer=null;
        function rst(){if(timer)clearTimeout(timer);timer=setTimeout(()=>{if(on)r.stop();},3500);}
        btn.onclick=()=>{if(on){r.stop();}else{ft='';sb.style.display='none';r.start();}};
        sb.onclick=()=>{if(!ft.trim())return;
          try{const u=new URL(window.top.location.href);u.searchParams.set('voice_q',ft.trim());window.top.location.assign(u.toString());}
          catch(e){try{const u2=new URL(window.parent.location.href);u2.searchParams.set('voice_q',ft.trim());window.parent.location.assign(u2.toString());}catch(e2){st.innerText='Copy: '+ft;}}
        };
        r.onstart=()=>{on=true;btn.style.background='#1A1AFF';btn.style.color='#fff';st.innerText='Listening…';rst();};
        r.onresult=(e)=>{let it='';for(let i=e.resultIndex;i<e.results.length;i++){const t=e.results[i][0].transcript;if(e.results[i].isFinal){ft+=t+' ';}else{it+=t;}}if((ft+it).trim())st.innerText='"'+(ft+it).trim()+'"';rst();};
        r.onerror=(e)=>{on=false;btn.style.background='#fff';btn.style.color='#1A1AFF';st.innerText=e.error==='not-allowed'?'Mic blocked':e.error;};
        r.onend=()=>{on=false;btn.style.background='#fff';btn.style.color='#1A1AFF';if(ft.trim()){st.innerText='"'+ft.trim()+'" — click Send';sb.style.display='inline-flex';}else if(st.innerText.indexOf('Listening')>-1){st.innerText='Tap to speak';}};
        })();</script>""", height=44)

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
            with st.spinner("Searching…"):
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

            st.markdown(answer)

            # ── Voice ─────────────────────────────────
            if st.session_state.voice_reply:
                speak_text(answer)

            # ── Action buttons row ────────────────────
            msg_idx = str(len(st.session_state.messages))
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
            if "fups_" + msg_idx not in st.session_state:
                fups = get_followup_questions(question, answer)
                st.session_state["fups_" + msg_idx] = fups
            fups = st.session_state.get("fups_" + msg_idx, [])
            if fups:
                st.markdown(
                    '<div style="margin-top:0.7rem;padding-top:0.5rem;border-top:1px solid #D0D3E0;">'
                    '<div style="font-size:10px;font-weight:600;color:#7A7F96;letter-spacing:0.08em;'
                    'text-transform:uppercase;margin-bottom:0.5rem;">Follow-up questions</div>'
                    '<div style="display:flex;flex-wrap:wrap;gap:6px;">'
                    + "".join([
                        '<span style="display:inline-flex;align-items:center;gap:4px;font-size:12px;'
                        'font-weight:500;color:#1A1AFF;background:rgba(26,26,255,0.06);'
                        'border:1px solid rgba(26,26,255,0.2);border-radius:20px;'
                        'padding:4px 12px;cursor:pointer;" '
                        'onclick="void(0)">↪ ' + q + '</span>'
                        for q in fups
                    ])
                    + '</div></div>',
                    unsafe_allow_html=True,
                )
                # Render as actual clickable Streamlit buttons below
                for fq in fups:
                    if st.button("↪ " + fq, key="fup_" + msg_idx + "_" + fq[:15]):
                        st.session_state["pending_q"] = fq
                        st.rerun()

        st.session_state.messages.append({"role":"assistant","content":answer})
        st.session_state.sources_history.append(sources)

    # ── Octopus scroll-to-bottom FAB ─────────────
    render_octo_fab()


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

    st.markdown('<div class="camp-grid">', unsafe_allow_html=True)
    for c in CAMPAIGNS:
        st.markdown(
            '<div class="camp-card">'
            '<div class="camp-tag">' + c["tag"] + '</div>'
            '<div class="camp-title">' + c["title"] + '</div>'
            '<div class="camp-desc">' + c["desc"] + '</div>'
            '<a class="camp-link" href="' + c["link"] + '" target="_blank">' + c["cta"] + ' ↗</a>'
            '</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

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
        st.markdown('<div class="news-grid">', unsafe_allow_html=True)
        for item in news_items:
            date_str = ""
            if item.get("date"):
                try:
                    dt = datetime.fromisoformat(str(item["date"]).replace("Z",""))
                    date_str = dt.strftime("%b %d, %Y")
                except Exception:
                    date_str = str(item["date"])[:10]

            st.markdown(
                '<div class="news-card">'
                '<div class="news-source">' + (item.get("source","") or "") + '</div>'
                '<div class="news-title"><a href="' + item.get("url","#") + '" target="_blank">' + item.get("title","") + '</a></div>'
                + ('<div class="news-desc">' + item["description"][:160] + '…</div>' if item.get("description") else '')
                + ('<div class="news-date">' + date_str + '</div>' if date_str else '')
                + '</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Fallback curated updates if CoinGecko news returns nothing
        st.markdown(
            '<div style="background:#FFFFFF;border:1px solid #E3E5EA;border-radius:10px;padding:1rem 1.2rem;margin-bottom:0.8rem;">'
            '<div style="font-size:11px;color:#9499A8;margin-bottom:0.4rem;">News could not be loaded from CoinGecko. Latest known updates:</div>',
            unsafe_allow_html=True,
        )
        fallback_updates = [
            {"title": "AI Agent Carnival Phase 1 is LIVE", "desc": "150,000 PROS prize pool · Submit Skills by June 15 on DoraHacks", "link": "https://dorahacks.io/hackathon/pharos-phase1"},
            {"title": "The Builders Harbor on Pharos has been upgraded ", "desc": "new tools, templates, and technical resources .", "link": "https://www.pharos.xyz/devhub"},
            {"title": "USDC + CCTP integration live", "desc": "Pharos integrates Circle's USDC and CCTP for real-time RealFi settlement.", "link": PHAROS_MAIN_URL},
            {"title": "Expedition Season 2 ongoing", "desc": "Particpate in the Ecosystem.", "link": "https://discord.gg/pharos"},
            {"title": "$PROS now powers AI payments","desc": "Use $PROS and USDC to access premier AI models.", "link": "https://x.com/pharos_network/status/2066517384928834003"},
            {"title": "Pharos x XLayer & OKX ","desc": "Fellow partners in bringing World Cup outcomes onchain.", "link": "https://x.com/pharos_network/status/2065362220851335650"},
        ]
        for u in fallback_updates:
            st.markdown(
                '<div class="news-card" style="margin-bottom:8px;">'
                '<div class="news-title"><a href="' + u["link"] + '" target="_blank">' + u["title"] + '</a></div>'
                '<div class="news-desc">' + u["desc"] + '</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div style="height:0.5rem;"></div>', unsafe_allow_html=True)
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
        chg     = p["change_24h"] or 0
        chg_cls = "green" if chg >= 0 else "red"
        st.markdown(
            '<div class="price-ticker" style="margin-bottom:1.2rem;">'
            '<div class="ticker-cell"><div class="ticker-label">$PROS Price</div>'
            '<div class="ticker-value">$' + f'{p["price_usd"]:.4f}' + '</div></div>'
            '<div class="ticker-cell"><div class="ticker-label">24h Change</div>'
            '<div class="ticker-value ' + chg_cls + '">' + ("▲" if chg>=0 else "▼") + f'{abs(chg):.2f}%</div></div>'
            '<div class="ticker-cell"><div class="ticker-label">Market Cap</div>'
            '<div class="ticker-value">' + ("$" + f'{p["market_cap_usd"]:,.0f}' if p.get("market_cap_usd") else "—") + '</div></div>'
            '<div class="ticker-cell"><div class="ticker-label">24h Volume</div>'
            '<div class="ticker-value">' + ("$" + f'{p["volume_24h"]:,.0f}' if p.get("volume_24h") else "—") + '</div></div>'
            '</div>'
            '<div class="ticker-source">CoinGecko · Updated ' + (p.get("last_updated","—")) + '</div>',
            unsafe_allow_html=True,
        )

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
            st.markdown(
                '<div class="cex-card">'
                '<div class="cex-name">' + cex["name"] + '</div>'
                '<div class="cex-pair">' + cex["desc"] + '</div>'
                '<a class="cex-btn" href="' + cex["url"] + '" target="_blank">Trade ↗</a>'
                '</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<div style="font-size:11px;color:#9499A8;margin-top:0.8rem;padding:0.6rem 0.8rem;'
        'background:#FFFFFF;border-radius:8px;border:1px solid #E3E5EA;">'
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
            f'background:#E9EEFF;border:1px solid #E9EEFF;border-radius:6px;'
            f'padding:3px 9px;margin-right:4px;">{t}</span>'
            for t in dapp["cat"]
        )
        cards_html += (
            f'<a href="{dapp["url"]}" target="_blank" '
            f'style="background:#FFFFFF;border:1px solid #ECEEF4;border-radius:16px;'
            f'padding:1.2rem 1.3rem;display:flex;flex-direction:column;gap:0;'
            f'text-decoration:none;box-shadow:0 1px 4px rgba(20,20,60,0.05);'
            f'transition:all 0.18s ease;cursor:pointer;">'
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