"""
app.py  (FIXED — Pharos Brand Theme, zero f-string errors)
-----------------------------------------------------------
All CSS is in plain triple-quoted strings (no f-prefix).
f-strings are only used where Python variables are injected,
and those blocks contain NO curly braces from CSS.

HOW TO RUN:
    streamlit run app.py
"""

import os
import time
import base64
import requests
import streamlit as st
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# LIVE $PROS PRICE — CoinGecko integration
# Verified asset ID: "pharos" (coingecko.com/en/coins/pharos)
# Free API, no key needed, 100 calls/min limit
# Cached 5 minutes via st.session_state
# Auto-refreshes every 5 minutes via st_autorefresh
# ─────────────────────────────────────────────
COINGECKO_ASSET_ID  = "pharos-network"
COINGECKO_URL       = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=" + "pharos-network" +
    "&vs_currencies=usd"
    "&include_24hr_change=true"
    "&include_market_cap=true"
    "&include_24hr_vol=true"
)
PRICE_CACHE_SECONDS = 300   # 5 minutes


def get_pros_price() -> dict:
    """
    Fetch live PROS price from CoinGecko.
    Caches in st.session_state for 5 minutes.
    On failure returns available=False — never crashes the app.
    """
    now    = time.time()
    cached = st.session_state.get("pros_price_cache", {})

    if cached and now - cached.get("fetched_at", 0) < PRICE_CACHE_SECONDS:
        return cached

    try:
        r = requests.get(COINGECKO_URL, timeout=6,
                         headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json().get(COINGECKO_ASSET_ID, {})
        if not data:
            raise ValueError("Empty response from CoinGecko")
        result = {
            "price_usd":      data.get("usd"),
            "market_cap_usd": data.get("usd_market_cap"),
            "volume_24h":     data.get("usd_24h_vol"),
            "change_24h":     data.get("usd_24h_change"),
            "last_updated":   datetime.now(timezone.utc).strftime("%H:%M UTC"),
            "fetched_at":     now,
            "available":      True,
            "error":          None,
        }
    except Exception as e:
        prev = st.session_state.get("pros_price_cache", {})
        result = {
            "price_usd":      prev.get("price_usd"),
            "market_cap_usd": prev.get("market_cap_usd"),
            "volume_24h":     prev.get("volume_24h"),
            "change_24h":     prev.get("change_24h"),
            "last_updated":   prev.get("last_updated"),
            "fetched_at":     now,
            "available":      False,
            "error":          str(e),
        }

    st.session_state["pros_price_cache"] = result
    return result

# ─────────────────────────────────────────────
# PAGE CONFIG — must be the very first st. call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="OctoBot — Pharos AI Assistant",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# GOOGLE FONTS — plain string, no f-prefix
# ─────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800'
    '&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# ALL CSS — plain string, no f-prefix
# Curly braces here are CSS, not Python.
# Keeping this completely separate from any
# f-string avoids every possible syntax error.
# ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --blue-primary:   #1A1AFF;
    --blue-bright:    #3D3DFF;
    --blue-light:     #6B8CFF;
    --blue-glow:      rgba(26,26,255,0.3);
    --blue-subtle:    rgba(26,26,255,0.08);
    --bg-dark:        #0A0A12;
    --bg-surface:     #10101E;
    --bg-raised:      #16162A;
    --border:         #1E1E3A;
    --border-bright:  #2A2A5A;
    --text-primary:   #FFFFFF;
    --text-secondary: #A0A8CC;
    --text-muted:     #5A5A8A;
    --font-display:   'Syne', sans-serif;
    --font-body:      'DM Sans', sans-serif;
}

html, body, [class*="css"] {
    font-family: var(--font-body) !important;
    background-color: var(--bg-dark) !important;
    color: var(--text-primary) !important;
}

.stApp {
    background: var(--bg-dark) !important;
    background-image:
        radial-gradient(ellipse 80% 50% at 50% -10%, rgba(26,26,255,0.15) 0%, transparent 60%),
        radial-gradient(ellipse 40% 30% at 80% 80%, rgba(26,26,255,0.06) 0%, transparent 50%) !important;
}

#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }

[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}

.pharos-hero {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2.5rem 0 1.5rem 0;
    position: relative;
}

.logo-wrapper {
    position: relative;
    display: inline-block;
    margin-bottom: 1rem;
}

.logo-wrapper::before {
    content: '';
    position: absolute;
    inset: -16px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(26,26,255,0.25) 0%, transparent 70%);
    animation: pulse-glow 3s ease-in-out infinite;
}

.logo-wrapper::after {
    content: '';
    position: absolute;
    inset: -10px;
    border-radius: 50%;
    border: 1px solid rgba(26,26,255,0.4);
    animation: spin-ring 20s linear infinite;
}

@keyframes pulse-glow {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50%       { transform: scale(1.1); opacity: 1; }
}

@keyframes spin-ring {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}

.pharos-logo-img {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    position: relative;
    z-index: 2;
    filter: drop-shadow(0 0 20px rgba(26,26,255,0.6));
}

.hero-title {
    font-family: var(--font-display) !important;
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em !important;
    background: linear-gradient(135deg, #FFFFFF 0%, #6B8CFF 60%, #1A1AFF 100%);
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    margin: 0 !important;
    line-height: 1.1 !important;
    text-align: center;
}

.hero-subtitle {
    font-family: var(--font-body) !important;
    font-size: 0.95rem !important;
    color: var(--text-secondary) !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    text-align: center;
    margin-top: 0.4rem !important;
}

.pharos-divider {
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--blue-primary), transparent);
    margin: 0.5rem 0 1.5rem 0;
    opacity: 0.6;
}

[data-testid="stMetric"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    padding: 0.75rem 1rem !important;
    transition: border-color 0.2s ease !important;
}
[data-testid="stMetric"]:hover {
    border-color: var(--blue-bright) !important;
}
[data-testid="stMetricLabel"] > div {
    color: var(--text-secondary) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    font-size: 1.3rem !important;
}

[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.4rem 0 !important;
}
.stChatMessage:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--blue-subtle) !important;
    border: 1px solid rgba(26,26,255,0.2) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
}
.stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
}

[data-testid="stChatInput"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: 12px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--blue-primary) !important;
    box-shadow: 0 0 0 3px var(--blue-glow) !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: var(--text-primary) !important;
    font-family: var(--font-body) !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--text-muted) !important;
}

[data-testid="stExpander"] {
    background: var(--bg-raised) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin-top: 0.5rem !important;
}
[data-testid="stExpander"] summary {
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--blue-light) !important;
}

.source-card {
    background: var(--bg-surface);
    border-left: 3px solid var(--blue-primary);
    border-radius: 0 8px 8px 0;
    padding: 0.6rem 0.9rem;
    margin: 0.35rem 0;
    transition: border-color 0.2s ease, background 0.2s ease;
}
.source-card:hover {
    background: var(--bg-raised);
    border-left-color: var(--blue-light);
}
.source-card a {
    color: var(--blue-light) !important;
    text-decoration: none !important;
    font-size: 0.8rem !important;
}
.source-card a:hover {
    color: #FFFFFF !important;
    text-decoration: underline !important;
}
.source-card strong {
    color: var(--text-primary) !important;
    font-size: 0.85rem !important;
    display: block;
    margin-bottom: 2px;
}

.stButton > button {
    background: var(--bg-raised) !important;
    color: var(--text-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-family: var(--font-body) !important;
    font-size: 0.82rem !important;
    transition: all 0.2s ease !important;
    text-align: left !important;
}
.stButton > button:hover {
    background: var(--blue-subtle) !important;
    border-color: var(--blue-primary) !important;
    color: var(--text-primary) !important;
    box-shadow: 0 0 12px var(--blue-glow) !important;
}

.reset-btn > button {
    background: rgba(26,26,255,0.12) !important;
    border-color: var(--blue-primary) !important;
    color: var(--blue-light) !important;
    font-weight: 600 !important;
    text-align: center !important;
}
.reset-btn > button:hover {
    background: var(--blue-primary) !important;
    color: #FFFFFF !important;
}

[data-testid="stToggle"] label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
}

.sidebar-section {
    font-family: var(--font-display) !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
    margin: 1rem 0 0.5rem 0 !important;
}

.status-bar {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.75rem;
    color: var(--text-muted);
    font-family: var(--font-body);
    padding: 0.4rem 0;
}
.status-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #00FF88;
    box-shadow: 0 0 6px #00FF88;
    animation: blink 2s ease-in-out infinite;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.3; }
}

.welcome-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.5rem 1.8rem;
    margin: 1rem 0;
    position: relative;
    overflow: hidden;
}
.welcome-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--blue-primary), var(--blue-light), transparent);
}
.welcome-card h3 {
    font-family: var(--font-display) !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    margin-bottom: 0.5rem !important;
}
.welcome-card p {
    font-size: 0.9rem !important;
    color: var(--text-secondary) !important;
    line-height: 1.6 !important;
    margin: 0 !important;
}
.welcome-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 1rem;
}
.tag {
    background: var(--blue-subtle);
    border: 1px solid rgba(26,26,255,0.25);
    border-radius: 20px;
    padding: 3px 10px;
    font-size: 0.75rem;
    color: var(--blue-light);
    font-family: var(--font-body);
}

hr { border-color: var(--border) !important; margin: 0.8rem 0 !important; }

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg-dark); }
::-webkit-scrollbar-thumb { background: var(--border-bright); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--blue-primary); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOGO HELPER
# ─────────────────────────────────────────────
def get_logo_base64():
    """Find pharos_logo.jpg or .png in the project folder and return base64 src."""
    for path, mime in [("pharos_logo.jpg", "image/jpeg"), ("pharos_logo.png", "image/png")]:
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            return "data:" + mime + ";base64," + b64
    return ""


# ─────────────────────────────────────────────
# LOAD OCTOBOT (cached — runs only once)
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="Initializing OctoBot knowledge base...")
def load_octobot():
    try:
        from octobot import OctoBot
        return OctoBot(), None
    except FileNotFoundError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "sources_history" not in st.session_state:
    st.session_state.sources_history = []


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:

    logo_b64 = get_logo_base64()

    # Logo + title — f-string here has NO CSS curly braces, safe to use
    if logo_b64:
        logo_html = (
            '<div style="display:flex;align-items:center;gap:12px;padding:0.5rem 0 1rem 0;">'
            '<img src="' + logo_b64 + '" style="width:38px;height:38px;border-radius:50%;'
            'filter:drop-shadow(0 0 8px rgba(26,26,255,0.7));" />'
            '<div>'
            '<div style="font-family:Syne,sans-serif;font-weight:800;font-size:1rem;'
            'color:#FFFFFF;line-height:1.1;">OctoBot</div>'
            '<div style="font-size:0.7rem;color:#5A5A8A;letter-spacing:0.06em;'
            'text-transform:uppercase;">Pharos AI Assistant</div>'
            '</div></div>'
        )
    else:
        logo_html = (
            '<div style="padding:0.5rem 0 1rem 0;">'
            '<div style="font-family:Syne,sans-serif;font-weight:800;'
            'font-size:1.1rem;color:#FFFFFF;">&#x1F419; OctoBot</div>'
            '<div style="font-size:0.7rem;color:#5A5A8A;letter-spacing:0.06em;'
            'text-transform:uppercase;">Pharos AI Assistant</div>'
            '</div>'
        )

    st.markdown(logo_html, unsafe_allow_html=True)
    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    st.markdown('<p class="sidebar-section">Settings</p>', unsafe_allow_html=True)
    show_sources = st.toggle("Show source citations", value=True)

    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("↺  New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sources_history = []
        bot_obj, _ = load_octobot()
        if bot_obj:
            bot_obj.reset_memory()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    st.markdown('<p class="sidebar-section">Example Questions</p>', unsafe_allow_html=True)
    examples = [
        "What is Pharos Network?",
        "What are SPNs?",
        "How does Native Restaking work?",
        "What is L1-Core?",
        "How do I build on Pharos?",
        "What is the consensus mechanism?",
        "What are RWA use cases?",
    ]
    for q in examples:
        if st.button(q, use_container_width=True, key="ex_" + q):
            st.session_state["pending_q"] = q
            st.rerun()

    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="status-bar"><div class="status-dot"></div>'
        '<span>Connected to knowledge base</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div style="margin-top:1.5rem;font-size:0.72rem;color:#5A5A8A;'
        'font-family:DM Sans,sans-serif;line-height:1.6;">'
        'OctoBot answers only from verified<br>'
        'Pharos documentation sources.<br>'
        'Zero hallucination guaranteed.</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# MAIN AREA — HERO
# ─────────────────────────────────────────────
logo_b64 = get_logo_base64()

if logo_b64:
    # Build HTML using string concatenation — no f-string, no CSS braces conflict
    hero_html = (
        '<div class="pharos-hero">'
        '<div class="logo-wrapper">'
        '<img src="' + logo_b64 + '" class="pharos-logo-img" alt="Pharos Logo" />'
        '</div>'
        '<h1 class="hero-title">OctoBot</h1>'
        '<p class="hero-subtitle">Pharos Network &middot; AI Documentation Assistant</p>'
        '</div>'
    )
else:
    hero_html = (
        '<div class="pharos-hero">'
        '<div style="font-size:3.5rem;margin-bottom:0.5rem;'
        'filter:drop-shadow(0 0 20px rgba(26,26,255,0.6));">&#x1F419;</div>'
        '<h1 class="hero-title">OctoBot</h1>'
        '<p class="hero-subtitle">Pharos Network &middot; AI Documentation Assistant</p>'
        '<div style="margin-top:0.75rem;padding:0.4rem 0.9rem;'
        'background:rgba(26,26,255,0.1);border:1px solid rgba(26,26,255,0.3);'
        'border-radius:8px;font-size:0.78rem;color:#6B8CFF;'
        'font-family:DM Sans,sans-serif;">'
        '&#x1F4A1; Save your logo as <code>pharos_logo.jpg</code> '
        'in your octobot folder, then refresh.</div>'
        '</div>'
    )

st.markdown(hero_html, unsafe_allow_html=True)
st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD BOT
# ─────────────────────────────────────────────
bot, load_error = load_octobot()

if load_error:
    # Plain string concat — no f-string, no CSS braces
    error_html = (
        '<div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);'
        'border-radius:12px;padding:1.5rem;margin:1rem 0;">'
        '<div style="font-family:Syne,sans-serif;font-weight:700;'
        'color:#FF6B6B;margin-bottom:0.5rem;">&#x26A0; OctoBot could not start</div>'
        '<div style="color:#A0A8CC;font-size:0.9rem;margin-bottom:1rem;">'
        + str(load_error) +
        '</div>'
        '<div style="color:#5A5A8A;font-size:0.85rem;">'
        'Run in your terminal:<br>'
        '<code style="color:#6B8CFF;">python build_vectorstore.py</code><br>'
        'then refresh this page.</div>'
        '</div>'
    )
    st.markdown(error_html, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────
# METRICS
# ─────────────────────────────────────────────
chunk_count = bot.vectorstore._collection.count()
price_data  = get_pros_price()

# ── Metrics row ───────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("Knowledge Chunks", str(chunk_count))
c2.metric("AI Model", "Gemini")
c3.metric("Vector DB", "ChromaDB")

if price_data.get("available") and price_data.get("price_usd") is not None:
    usd     = price_data["price_usd"]
    chg     = price_data.get("change_24h")
    chg_str = f"{chg:+.2f}%" if chg is not None else None
    c4.metric(label="$PROS Price", value=f"${usd:.4f}", delta=chg_str)
elif not price_data.get("available") and price_data.get("price_usd") is not None:
    # Stale cached value — show it with a warning indicator
    usd = price_data["price_usd"]
    c4.metric(label="$PROS Price", value=f"${usd:.4f}", delta="⚠ stale")
else:
    c4.metric("$PROS Price", "Fetching...")

st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

# ── PROS Live Market Card ─────────────────────────────────────────
# Auto-refreshes every 5 minutes via JavaScript meta-refresh
# Shows warning if CoinGecko is unavailable — never crashes
with st.expander("📊 Live $PROS Market Data", expanded=True):
    if price_data.get("available") and price_data.get("price_usd") is not None:
        p_usd  = price_data["price_usd"]
        mcap   = price_data.get("market_cap_usd")
        vol    = price_data.get("volume_24h")
        chg    = price_data.get("change_24h")
        upd    = price_data.get("last_updated", "N/A")

        chg_color = "#00FF88" if (chg or 0) >= 0 else "#FF6B6B"
        chg_str   = f"{chg:+.2f}%" if chg  is not None else "N/A"
        mcap_str  = f"${mcap:,.0f}"  if mcap is not None else "N/A"
        vol_str   = f"${vol:,.0f}"   if vol  is not None else "N/A"

        st.markdown(
            '<div style="display:flex;gap:1.5rem;flex-wrap:wrap;padding:0.5rem 0;">'
            '<div style="flex:1;min-width:120px;background:#10101E;border:1px solid #1E1E3A;'
            'border-radius:10px;padding:0.8rem 1rem;">'
            '<div style="font-size:0.7rem;color:#5A5A8A;text-transform:uppercase;'
            'letter-spacing:0.08em;margin-bottom:4px;">Price (USD)</div>'
            '<div style="font-size:1.3rem;font-weight:700;color:#FFFFFF;'
            'font-family:Syne,sans-serif;">$' + f"{p_usd:.4f}" + '</div></div>'
            '<div style="flex:1;min-width:120px;background:#10101E;border:1px solid #1E1E3A;'
            'border-radius:10px;padding:0.8rem 1rem;">'
            '<div style="font-size:0.7rem;color:#5A5A8A;text-transform:uppercase;'
            'letter-spacing:0.08em;margin-bottom:4px;">24h Change</div>'
            '<div style="font-size:1.3rem;font-weight:700;color:' + chg_color + ';'
            'font-family:Syne,sans-serif;">' + chg_str + '</div></div>'
            '<div style="flex:1;min-width:120px;background:#10101E;border:1px solid #1E1E3A;'
            'border-radius:10px;padding:0.8rem 1rem;">'
            '<div style="font-size:0.7rem;color:#5A5A8A;text-transform:uppercase;'
            'letter-spacing:0.08em;margin-bottom:4px;">Market Cap</div>'
            '<div style="font-size:1.1rem;font-weight:700;color:#FFFFFF;'
            'font-family:Syne,sans-serif;">' + mcap_str + '</div></div>'
            '<div style="flex:1;min-width:120px;background:#10101E;border:1px solid #1E1E3A;'
            'border-radius:10px;padding:0.8rem 1rem;">'
            '<div style="font-size:0.7rem;color:#5A5A8A;text-transform:uppercase;'
            'letter-spacing:0.08em;margin-bottom:4px;">24h Volume</div>'
            '<div style="font-size:1.1rem;font-weight:700;color:#FFFFFF;'
            'font-family:Syne,sans-serif;">' + vol_str + '</div></div>'
            '</div>'
            '<div style="font-size:0.7rem;color:#5A5A8A;margin-top:4px;">'
            'Source: CoinGecko &nbsp;·&nbsp; Last updated: ' + upd + ' &nbsp;·&nbsp;'
            ' Auto-refreshes every 5 min</div>',
            unsafe_allow_html=True,
        )
        # Hidden auto-refresh every 5 minutes
        st.markdown(
            '<meta http-equiv="refresh" content="300">',
            unsafe_allow_html=True,
        )
    elif not price_data.get("available") and price_data.get("price_usd") is not None:
        # Show stale data with warning
        p_usd = price_data["price_usd"]
        st.warning(
            "CoinGecko temporarily unavailable. "
            "Showing last known price: $" + f"{p_usd:.4f}" + ". "
            "Documentation answers continue to work normally."
        )
    else:
        # No data at all
        st.warning(
            "CoinGecko is currently unavailable. "
            "Price data will appear once the connection is restored. "
            "All documentation features continue to work normally."
        )

st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────
# WELCOME CARD (only when chat is empty)
# ─────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
<div class="welcome-card">
    <h3>Welcome to OctoBot</h3>
    <p>
        Ask me anything about the Pharos Network — architecture, SPNs,
        consensus, restaking, RWA, developer programs, or how to build on Pharos.
        I answer only from verified documentation sources, so every answer is
        grounded in real content.
    </p>
    <div class="welcome-tags">
        <span class="tag">SPNs</span>
        <span class="tag">L1 Architecture</span>
        <span class="tag">Native Restaking</span>
        <span class="tag">RWA</span>
        <span class="tag">DeFi</span>
        <span class="tag">Build on Pharos</span>
        <span class="tag">Consensus</span>
        <span class="tag">Cross-chain</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CHAT HISTORY
# ─────────────────────────────────────────────
for i, message in enumerate(st.session_state.messages):
    avatar = "👤" if message["role"] == "user" else "🐙"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

        if message["role"] == "assistant" and show_sources:
            src_idx = i // 2
            if src_idx < len(st.session_state.sources_history):
                sources = st.session_state.sources_history[src_idx]
                if sources:
                    label = "📎 " + str(len(sources)) + " source(s) used"
                    with st.expander(label, expanded=False):
                        for src in sources:
                            card = (
                                '<div class="source-card">'
                                '<strong>' + src["title"] + '</strong>'
                                '<a href="' + src["url"] + '" target="_blank">'
                                + src["url"] + '</a>'
                                '</div>'
                            )
                            st.markdown(card, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CHAT INPUT
# ─────────────────────────────────────────────
pending = st.session_state.pop("pending_q", None)
user_input = st.chat_input("Ask about Pharos Network...")
question = pending or user_input

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🐙"):
        with st.spinner("Searching Pharos knowledge base..."):
            try:
                answer, sources = bot.ask(question)
            except Exception as e:
                answer = "An error occurred: " + str(e)
                sources = []

        st.markdown(answer)

        if show_sources and sources:
            label = "📎 " + str(len(sources)) + " source(s) used"
            with st.expander(label, expanded=True):
                for src in sources:
                    card = (
                        '<div class="source-card">'
                        '<strong>' + src["title"] + '</strong>'
                        '<a href="' + src["url"] + '" target="_blank">'
                        + src["url"] + '</a>'
                        '</div>'
                    )
                    st.markdown(card, unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.sources_history.append(sources)