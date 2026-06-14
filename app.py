"""
app.py — OctoBot Pharos AI Assistant
--------------------------------------
Redesigned UI: compact, professional, structured.
- Smaller tighter hero section
- Compact inline price ticker instead of large expander
- Reduced sidebar element sizes
- Cleaner chat bubbles
- Better spacing and typography hierarchy
- All CSS in plain strings (no f-prefix) to avoid syntax errors
"""

import os
import time
import base64
import requests
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# PAGE CONFIG — must be first st. call
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="OctoBot · Pharos AI",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# COINGECKO — live $PROS price
# ─────────────────────────────────────────────
COINGECKO_ASSET_ID  = "pharos-network"
COINGECKO_URL       = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=pharos-network"
    "&vs_currencies=usd"
    "&include_24hr_change=true"
    "&include_market_cap=true"
    "&include_24hr_vol=true"
)
PRICE_CACHE_SECONDS = 300


def get_pros_price() -> dict:
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
            raise ValueError("Empty CoinGecko response")
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
        prev   = st.session_state.get("pros_price_cache", {})
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
# LOGO HELPER
# ─────────────────────────────────────────────
def get_logo_b64() -> str:
    for path, mime in [("pharos_logo.jpg","image/jpeg"),("pharos_logo.png","image/png")]:
        if os.path.exists(path):
            with open(path,"rb") as f:
                return "data:"+mime+";base64,"+base64.b64encode(f.read()).decode()
    return ""


# ─────────────────────────────────────────────
# FONTS
# ─────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=Syne:wght@500;600;700;800'
    '&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,400&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
# CSS — complete redesign
# All curly braces here are CSS, not Python.
# ─────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --p-blue:     #1A1AFF;
    --p-blue2:    #2D2DE0;
    --p-accent:   #1A1AFF;
    --p-light:    #4F4FFF;
    --p-glow:     rgba(26,26,255,0.18);
    --p-subtle:   rgba(26,26,255,0.06);
    --bg:         #F4F5F7;
    --bg-1:       #FFFFFF;
    --bg-2:       #F7F8FA;
    --bg-3:       #ECEDF1;
    --border-1:   #E3E5EA;
    --border-2:   #D6D9E0;
    --txt-1:      #14141F;
    --txt-2:      #5B5F6E;
    --txt-3:      #9499A8;
    --green:      #1FA855;
    --red:        #E5484D;
    --fn-d:       'Syne', sans-serif;
    --fn-b:       'DM Sans', sans-serif;
    --r-sm:       6px;
    --r-md:       10px;
    --r-lg:       14px;
}

/* ── GLOBAL ─────────────────────────── */
html, body, [class*="css"] {
    font-family: var(--fn-b) !important;
    background-color: var(--bg) !important;
    color: var(--txt-1) !important;
    font-size: 14px !important;
}

.stApp {
    background: var(--bg) !important;
    background-image:
        radial-gradient(ellipse 60% 40% at 50% 0%, rgba(26,26,255,0.05) 0%, transparent 55%) !important;
}

#MainMenu, footer, header, .stDeployButton { display: none !important; }

/* ── SIDEBAR ────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-1) !important;
    border-right: 1px solid var(--border-1) !important;
    width: 248px !important;
}
[data-testid="stSidebar"] > div:first-child {
    padding: 1rem 0.9rem !important;
}
[data-testid="stSidebar"] * { color: var(--txt-1) !important; }

/* ── SIDEBAR LOGO ROW ───────────────── */
.sb-logo {
    display: flex;
    align-items: center;
    gap: 9px;
    padding: 0 0 0.9rem 0;
    border-bottom: 1px solid var(--border-1);
    margin-bottom: 0.9rem;
}
.sb-logo img {
    width: 28px; height: 28px;
    border-radius: 50%;
    filter: drop-shadow(0 0 4px rgba(26,26,255,0.25));
    flex-shrink: 0;
}
.sb-logo-name {
    font-family: var(--fn-d);
    font-size: 14.5px;
    font-weight: 700;
    color: var(--txt-1);
    line-height: 1.1;
}
.sb-logo-sub {
    font-size: 11px;
    color: var(--txt-3);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

/* ── SIDEBAR SECTION LABEL ──────────── */
.sb-label {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--txt-3);
    margin: 0.8rem 0 0.4rem 0;
}

/* ── SIDEBAR DIVIDER ────────────────── */
.sb-div {
    height: 1px;
    background: var(--border-1);
    margin: 0.7rem 0;
}

/* ── SIDEBAR STATUS DOT ─────────────── */
.sb-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    color: var(--txt-3);
    padding: 0.3rem 0;
}
.dot-live {
    width: 8px; height: 8px;
    border-radius: 60%;
    background: var(--green);
    box-shadow: 0 0 5px var(--green);
    animation: blink 2.5s ease-in-out infinite;
    flex-shrink: 0;
}
@keyframes blink {
    0%,100%{opacity:1} 50%{opacity:0.25}
}

/* ── SIDEBAR FOOTER NOTE ────────────── */
.sb-note {
    font-size: 12px;
    color: var(--txt-3);
    line-height: 1.6;
    margin-top: 0.8rem;
}

/* ── SIDEBAR BUTTONS ────────────────── */
.stButton > button {
    background: transparent !important;
    color: var(--txt-2) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: var(--r-sm) !important;
    font-family: var(--fn-b) !important;
    font-size: 12px !important;
    padding: 0.35rem 0.65rem !important;
    height: auto !important;
    text-align: left !important;
    transition: all 0.15s ease !important;
    line-height: 1.4 !important;
}
.stButton > button:hover {
    background: var(--p-subtle) !important;
    border-color: var(--p-blue) !important;
    color: var(--txt-1) !important;
}

.reset-btn > button {
    background: rgba(26,26,255,0.09) !important;
    border-color: var(--p-blue2) !important;
    color: var(--p-light) !important;
    font-size: 11px !important;
    text-align: center !important;
}
.reset-btn > button:hover {
    background: var(--p-blue) !important;
    color: #fff !important;
}

/* ── TOGGLE ─────────────────────────── */
[data-testid="stToggle"] label {
    font-size: 13.5px !important;
    color: var(--txt-2) !important;
}

/* ── MAIN HEADER ────────────────────── */
.main-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 1.2rem 0 1rem 0;
    border-bottom: 1px solid var(--border-1);
    margin-bottom: 0.9rem;
}
.main-header img {
    width: 50px; height: 46px;
    border-radius: 60%;
    filter: drop-shadow(0 0 5px rgba(26,26,255,0.2));
    flex-shrink: 0;
}
.main-header-fallback {
    font-size: 23px;
    line-height: 1;
    flex-shrink: 0;
}
.main-title {
    font-family: var(--fn-d);
    font-size: 23px;
    font-weight: 700;
    color: var(--txt-1);
    line-height: 1.1;
    letter-spacing: -0.01em;
}
.main-subtitle {
    font-size: 13px;
    color: var(--txt-3);
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-top: 1px;
}
.main-header-right {
    margin-left: auto;
    text-align: right;
}
.powered-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 10px;
    font-weight: 600;
    color: #FFFFFF;
    background: #14141F;
    border: none;
    border-radius: 20px;
    padding: 4px 12px;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.powered-badge .dot-amber {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: #FFB020;
    flex-shrink: 0;
}

/* ── PRICE TICKER ───────────────────── */
.price-ticker {
    display: flex;
    align-items: center;
    gap: 0;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--r-md);
    overflow: hidden;
    margin-bottom: 0.75rem;
    box-shadow: 0 1px 3px rgba(20,20,31,0.04);
}
.ticker-cell {
    flex: 1;
    padding: 0.85rem 1.1rem;
    border-right: 1px solid var(--border-1);
}
.ticker-cell:last-child { border-right: none; }
.ticker-label {
    font-size: 12px;
    color: var(--txt-3);
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 2px;
}
.ticker-value {
    font-family: var(--fn-d);
    font-size: 17px;
    font-weight: 600;
    color: var(--txt-1);
}
.ticker-value.green { color: var(--green); }
.ticker-value.red   { color: var(--red); }
.ticker-source {
    font-size: 12px;
    color: var(--txt-3);
    padding: 0.3rem 0.9rem;
    background: var(--bg);
    border-top: 1px solid var(--border-1);
    letter-spacing: 0.04em;
}

/* ── STATS ROW ──────────────────────── */
.stats-row {
    display: flex;
    gap: 8px;
    margin-bottom: 0.75rem;
}
.stat-pill {
    display: flex;
    align-items: center;
    gap: 5px;
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: 20px;
    padding: 4px 11px;
    font-size: 12.5px;
    color: var(--txt-2);
    box-shadow: 0 1px 2px rgba(20,20,31,0.03);
}
.stat-pill-dot {
    width: 5px; height: 5px;
    border-radius: 50%;
    background: var(--p-accent);
    flex-shrink: 0;
}
.stat-pill strong {
    color: var(--txt-1);
    font-weight: 600;
}

/* ── BORDERED CONTAINER (chart card) ── */
[data-testid="stVerticalBlockBorderWrapper"] > div > div[data-testid="stVerticalBlock"] {
    background: var(--bg-1) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: var(--r-md) !important;
    padding: 0.7rem 0.9rem 0.3rem 0.9rem !important;
    margin-bottom: 0.75rem !important;
    box-shadow: 0 1px 3px rgba(20,20,31,0.04) !important;
}

/* ── CHART CARD ─────────────────────── */
.chart-card {
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-radius: var(--r-md);
    padding: 0.7rem 0.9rem 0.2rem 0.9rem;
    margin-bottom: 0.75rem;
}
.chart-card-label {
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--p-light);
    margin-bottom: 0.3rem;
}

/* ── THIN DIVIDER ───────────────────── */
.thin-div {
    height: 1px;
    background: var(--border-1);
    margin: 0.65rem 0;
}

/* ── WELCOME CARD ───────────────────── */
.welcome-card {
    background: var(--bg-1);
    border: 1px solid var(--border-1);
    border-left: 3px solid var(--p-blue);
    border-radius: var(--r-lg);
    padding: 1rem 1.2rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(20,20,31,0.04);
}
.welcome-card h3 {
    font-family: var(--fn-d) !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: var(--txt-1) !important;
    margin: 0 0 0.5rem 0 !important;
}
.welcome-card p {
    font-size: 13px !important;
    color: var(--txt-2) !important;
    line-height: 1.65 !important;
    margin: 0 !important;
}
.tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    margin-top: 0.7rem;
}
.tag {
    background: var(--p-subtle);
    border: 1px solid rgba(26,26,255,0.2);
    border-radius: 20px;
    padding: 2px 9px;
    font-size: 10px;
    color: var(--p-light);
}

/* ── CHAT MESSAGES ──────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.3rem 0 !important;
    color: var(--txt-1) !important;
}
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] span {
    color: var(--txt-1) !important;
}
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    background: var(--bg-2) !important;
    border: 1px solid var(--border-1) !important;
}

/* ── CHAT INPUT ─────────────────────── */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stBottomBlockContainer"],
[data-testid="stBottom"],
[data-testid="stBottom"] > div {
    background: var(--bg) !important;
}

[data-testid="stChatInput"] {
    background: var(--bg-1) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: var(--r-md) !important;
}

[data-testid="stChatInput"]:focus-within {
    border-color: var(--p-blue) !important;
    box-shadow: 0 0 0 2px var(--p-glow) !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInputTextArea"],
textarea[data-testid="stChatInputTextArea"] {
    background: var(--bg-1) !important;
    background-color: var(--bg-1) !important;
    color: var(--txt-1) !important;
    -webkit-text-fill-color: var(--txt-1) !important;
    font-family: var(--fn-b) !important;
    font-size: 13px !important;
    caret-color: var(--p-blue) !important;
}

[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInputTextArea"]::placeholder {
    color: var(--txt-2) !important;
    -webkit-text-fill-color: var(--txt-2) !important;
    font-size: 13px !important;
    opacity: 1 !important;
}

[data-testid="stChatInput"] button {
    background: var(--bg-2) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: var(--r-sm) !important;
}
[data-testid="stChatInput"] button svg {
    fill: var(--txt-1) !important;
}

/* ── EXPANDER (sources) ─────────────── */
[data-testid="stExpander"] {
    background: var(--bg-1) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: var(--r-md) !important;
    margin-top: 0.4rem !important;
}
[data-testid="stExpander"] summary {
    font-size: 11px !important;
    color: var(--txt-3) !important;
    padding: 0.4rem 0.7rem !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--p-light) !important;
}
[data-testid="stExpander"] summary svg {
    width: 14px !important;
    height: 14px !important;
}

/* ── SOURCE CARD ────────────────────── */
.source-card {
    background: var(--bg-2);
    border-left: 2px solid var(--p-blue);
    border-radius: 0 var(--r-sm) var(--r-sm) 0;
    padding: 0.4rem 0.7rem;
    margin: 0.25rem 0;
}
.source-card strong {
    display: block;
    font-size: 11px;
    font-weight: 500;
    color: var(--txt-1);
    margin-bottom: 1px;
}
.source-card a {
    font-size: 10px !important;
    color: var(--p-light) !important;
    text-decoration: none !important;
    word-break: break-all;
}
.source-card a:hover { text-decoration: underline !important; }

/* ── SPINNER ────────────────────────── */
[data-testid="stSpinner"] { color: var(--p-light) !important; }

/* ── SCROLLBAR ──────────────────────── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-2); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--p-blue); }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD OCTOBOT (cached — runs once)
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading OctoBot...")
def load_octobot():
    try:
        from octobot import OctoBot
        return OctoBot(), None
    except FileNotFoundError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)

def get_price_chart_df():
    """
    Fetch 24h PROS price history from CoinGecko for the area chart.
    Cached in session_state for 5 minutes alongside the price ticker.
    Returns a DataFrame with columns [time, price] or None on failure.
    """
    now    = time.time()
    cached = st.session_state.get("pros_chart_cache", {})

    if cached.get("df") is not None and now - cached.get("fetched_at", 0) < PRICE_CACHE_SECONDS:
        return cached["df"]

    try:
        url = (
            "https://api.coingecko.com/api/v3/coins/" + COINGECKO_ASSET_ID +
            "/market_chart?vs_currency=usd&days=1"
        )
        r = requests.get(url, timeout=8, headers={"Accept": "application/json"})
        r.raise_for_status()
        prices = r.json().get("prices", [])
        if not prices:
            raise ValueError("Empty chart data")

        df = pd.DataFrame(prices, columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")

        st.session_state["pros_chart_cache"] = {"df": df, "fetched_at": now}
        return df

    except Exception:
        # Keep showing the last good chart if available
        return cached.get("df")


def render_price_chart(df: pd.DataFrame, chart_key: str = "pros_chart") -> None:
    """
    Render a professional Pharos-themed area chart for $PROS 24h price.
    White/blue color scheme, gradient fill, clean axes, no legend clutter.
    """
    if df is None or df.empty:
        st.markdown(
            '<div style="font-size:11px;color:#9499A8;padding:0.4rem 0;">'
            'Chart unavailable — price history could not be loaded.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    line_color = "#1A1AFF"   # Pharos primary blue
    fill_color = "rgba(26,26,255,0.10)"
    grid_color = "rgba(20,20,31,0.06)"
    text_color = "#5B5F6E"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["price"],
        mode="lines",
        line=dict(color=line_color, width=2, shape="spline", smoothing=0.4),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate="$%{y:.4f}<br>%{x|%H:%M}<extra></extra>",
        name="PROS",
    ))

    fig.update_layout(
        height=190,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hovermode="x unified",
        font=dict(family="DM Sans, sans-serif", color=text_color, size=11),
        xaxis=dict(
            showgrid=False,
            showline=False,
            tickfont=dict(color=text_color, size=10),
            tickformat="%H:%M",
            nticks=6,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=grid_color,
            griddash="dot",
            showline=False,
            tickfont=dict(color=text_color, size=10),
            tickprefix="$",
            tickformat=".4f",
            side="right",
        ),
        hoverlabel=dict(
            bgcolor="#F7F8FA",
            font_color="#14141F",
            font_family="DM Sans, sans-serif",
            bordercolor="#D6D9E0",
        ),
    )

    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False}, key=chart_key)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
if "messages"        not in st.session_state: st.session_state.messages        = []
if "sources_history" not in st.session_state: st.session_state.sources_history = []


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
logo_b64 = get_logo_b64()

with st.sidebar:

    # Logo row
    if logo_b64:
        sb_logo = (
            '<div class="sb-logo">'
            '<img src="' + logo_b64 + '" />'
            '<div>'
            '<div class="sb-logo-name">OctoBot</div>'
            '<div class="sb-logo-sub">Pharos AI Assistant</div>'
            '</div></div>'
        )
    else:
        sb_logo = (
            '<div class="sb-logo">'
            '<span style="font-size:18px;">&#x1F419;</span>'
            '<div>'
            '<div class="sb-logo-name">OctoBot</div>'
            '<div class="sb-logo-sub">Pharos AI Assistant</div>'
            '</div></div>'
        )
    st.markdown(sb_logo, unsafe_allow_html=True)

    # Settings
    st.markdown('<div class="sb-label">Settings</div>', unsafe_allow_html=True)
    show_sources = st.toggle("Show source citations", value=True)

    st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

    # Reset
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("↺  New Conversation", use_container_width=True):
        st.session_state.messages        = []
        st.session_state.sources_history = []
        b, _ = load_octobot()
        if b: b.reset_memory()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

    # Example questions
    st.markdown('<div class="sb-label">Ask OctoBot</div>', unsafe_allow_html=True)
    examples = [
        "What is Pharos Network?",
        "What are SPNs?",
        "How does Native Restaking work?",
        "What is L1-Core?",
        "How do I build on Pharos?",
        "What is the consensus mechanism?",
        "What are RWA use cases?",
        "What is the PROS token?",
    ]
    for q in examples:
        if st.button(q, use_container_width=True, key="ex_" + q):
            st.session_state["pending_q"] = q
            st.rerun()

    st.markdown('<div class="sb-div"></div>', unsafe_allow_html=True)

    # Status + note
    st.markdown(
        '<div class="sb-status">'
        '<div class="dot-live"></div>'
        'Knowledge base online'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sb-note">'
        'Answers only from verified<br>Pharos sources. No hallucination.'
        '</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────

# ── Compact header row ────────────────────────
price_data  = get_pros_price()
bot, load_error = load_octobot()

if logo_b64:
    header_icon = '<img src="' + logo_b64 + '" />'
else:
    header_icon = '<span class="main-header-fallback">&#x1F419;</span>'

# Build price badge for header right side
if price_data.get("available") and price_data.get("price_usd") is not None:
    usd     = price_data["price_usd"]
    chg     = price_data.get("change_24h") or 0
    c_cls   = "green" if chg >= 0 else "red"
    chg_sym = "▲" if chg >= 0 else "▼"
    badge   = (
        '<span style="font-size:10px;color:#5B5F6E;">$PROS&nbsp;</span>'
        '<span style="font-family:Syne,sans-serif;font-size:12px;font-weight:600;'
        'color:#14141F;">' + f"${usd:.4f}" + '</span>'
        '<span style="font-size:10px;color:' + ("var(--green)" if chg>=0 else "var(--red)") + ';margin-left:4px;">'
        + chg_sym + f"{abs(chg):.2f}%" + '</span>'
    )
else:
    badge = '<span style="font-size:10px;color:#9499A8;">$PROS loading...</span>'

header_html = (
    '<div class="main-header">'
    + header_icon +
    '<div>'
    '<div class="main-title">OctoBot</div>'
    '<div class="main-subtitle">Pharos Network · AI Documentation Assistant</div>'
    '</div>'
    '<div class="main-header-right">'
    '<div class="powered-badge"><span class="dot-amber"></span>RAG · Gemini · ChromaDB</div>'
    '<div style="margin-top:4px;text-align:right;">' + badge + '</div>'
    '</div>'
    '</div>'
)
st.markdown(header_html, unsafe_allow_html=True)

# ── Error state ───────────────────────────────
if load_error:
    st.markdown(
        '<div style="background:rgba(255,50,50,0.07);border:1px solid rgba(255,80,80,0.25);'
        'border-radius:10px;padding:1rem 1.2rem;margin:0.5rem 0;">'
        '<div style="font-size:13px;font-weight:600;color:#FF6B6B;margin-bottom:4px;">'
        '&#x26A0; OctoBot could not start</div>'
        '<div style="font-size:12px;color:#5B5F6E;margin-bottom:8px;">' + str(load_error) + '</div>'
        '<div style="font-size:11px;color:#9499A8;">Run: '
        '<code style="color:#4F4FFF;background:#F7F8FA;padding:1px 5px;border-radius:4px;">'
        'python build_vectorstore.py</code> then refresh.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.stop()

# ── Stats pill row ────────────────────────────
chunk_count = bot.vectorstore._collection.count()

mcap = price_data.get("market_cap_usd")
vol  = price_data.get("volume_24h")
mcap_str = ("$" + f"{mcap/1e6:.1f}M") if mcap else "—"
vol_str  = ("$" + f"{vol/1e6:.1f}M")  if vol  else "—"

st.markdown(
    '<div class="stats-row">'
    '<div class="stat-pill"><div class="stat-pill-dot"></div>'
    '<strong>' + str(chunk_count) + '</strong>&nbsp;knowledge chunks</div>'
    '<div class="stat-pill"><div class="stat-pill-dot"></div>'
    'Market Cap&nbsp;<strong>' + mcap_str + '</strong></div>'
    '<div class="stat-pill"><div class="stat-pill-dot"></div>'
    '24h Vol&nbsp;<strong>' + vol_str + '</strong></div>'
    '<div class="stat-pill"><div class="stat-pill-dot"></div>'
    'Model&nbsp;<strong>Gemini</strong></div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Compact price ticker ──────────────────────
if price_data.get("available") and price_data.get("price_usd") is not None:
    p_usd = price_data["price_usd"]
    chg   = price_data.get("change_24h") or 0
    mcap  = price_data.get("market_cap_usd")
    vol   = price_data.get("volume_24h")
    upd   = price_data.get("last_updated","—")

    chg_cls  = "green" if chg >= 0 else "red"
    chg_sym  = "▲" if chg >= 0 else "▼"
    chg_str  = chg_sym + f"{abs(chg):.2f}%"
    mcap_str = ("$" + f"{mcap:,.0f}") if mcap else "—"
    vol_str  = ("$" + f"{vol:,.0f}")  if vol  else "—"

    st.markdown(
        '<div class="price-ticker">'
        '<div class="ticker-cell">'
        '<div class="ticker-label">$PROS Price</div>'
        '<div class="ticker-value">$' + f"{p_usd:.4f}" + '</div>'
        '</div>'
        '<div class="ticker-cell">'
        '<div class="ticker-label">24h Change</div>'
        '<div class="ticker-value ' + chg_cls + '">' + chg_str + '</div>'
        '</div>'
        '<div class="ticker-cell">'
        '<div class="ticker-label">Market Cap</div>'
        '<div class="ticker-value">' + mcap_str + '</div>'
        '</div>'
        '<div class="ticker-cell">'
        '<div class="ticker-label">24h Volume</div>'
        '<div class="ticker-value">' + vol_str + '</div>'
        '</div>'
        '</div>'
        '<div class="ticker-source">'
        'Source: CoinGecko &nbsp;·&nbsp; Updated ' + upd + ' &nbsp;·&nbsp; Auto-refreshes in 5 min'
        '</div>'
        '<meta http-equiv="refresh" content="300">',
        unsafe_allow_html=True,
    )

    # ── 24h price chart ────────────────────────────
    chart_df = get_price_chart_df()
    with st.container(border=True):
        st.markdown(
            '<div class="chart-card-label">$PROS · 24H PRICE (24H)</div>',
            unsafe_allow_html=True,
        )
        render_price_chart(chart_df, chart_key="pros_chart_main")
elif not price_data.get("available") and price_data.get("price_usd") is not None:
    p_usd = price_data["price_usd"]
    st.markdown(
        '<div style="font-size:10px;color:#9499A8;padding:0.3rem 0;">'
        '&#x26A0; CoinGecko unavailable — last known $PROS: $' + f"{p_usd:.4f}" +
        '</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="thin-div"></div>', unsafe_allow_html=True)

# ── Welcome card (only when no messages) ──────
if not st.session_state.messages:
    st.markdown(
        '<div class="welcome-card">'
        '<h3>Welcome to OctoBot</h3>'
        '<p>Ask me anything about Pharos Network. Answers come only from verified '
'documentation sources.</p>'
'<div class="tag-row">'
'<span class="tag">SPNs</span>'
'<span class="tag">L1 Architecture</span>'
'<span class="tag">Native Restaking</span>'
'<span class="tag">RWA</span>'
'<span class="tag">DeFi</span>'
'<span class="tag">Build on Pharos</span>'
'<span class="tag">Consensus</span>'
'<span class="tag">$PROS Token</span>'
'</div>'
'<div style="margin-top:0.9rem;padding-top:0.8rem;border-top:1px solid #E3E5EA;">'
'<div style="font-size:12px;font-weight:600;letter-spacing:0.1em;text-transform:uppercase;'
'color:#9499A8;margin-bottom:0.6rem;">Coming Soon</div>'
'<div style="display:flex;flex-wrap:wrap;gap:6px;">'
'<div style="display:flex;align-items:center;gap:5px;background:#F7F8FA;'
'border:1px dashed #D6D9E0;border-radius:6px;padding:3px 10px;">'
'<span style="font-size:8px;color:#1A1AFF;">●</span>'
'<span style="font-size:11px;color:#9499A8;">Multi-Language Support (Expected around 18th June)</span>'
'</div>'
'<div style="display:flex;align-items:center;gap:5px;background:#F7F8FA;'
'border:1px dashed #D6D9E0;border-radius:6px;padding:3px 10px;">'
'<span style="font-size:8px;color:#1A1AFF;">●</span>'
'<span style="font-size:11px;color:#9499A8;">CoinGecko News Feed on PROS (After 18th)</span>'
'</div>'
'<div style="display:flex;align-items:center;gap:5px;background:#F7F8FA;'
'border:1px dashed #D6D9E0;border-radius:6px;padding:3px 10px;">'
'<span style="font-size:8px;color:#1A1AFF;">●</span>'
'<span style="font-size:11px;color:#9499A8;">Wallet Checker</span>'
'</div>'
'<div style="display:flex;align-items:center;gap:5px;background:#F7F8FA;'
'border:1px dashed #D6D9E0;border-radius:6px;padding:3px 10px;">'
'<span style="font-size:8px;color:#1A1AFF;">●</span>'
'<span style="font-size:11px;color:#9499A8;">Pharos Ecosystem Map (Will take time)</span>'
'</div>'
'</div>'
'</div>'
'</div>',
        unsafe_allow_html=True,
    )

# ── Chat history ──────────────────────────────
for i, message in enumerate(st.session_state.messages):
    avatar = "👤" if message["role"] == "user" else "🐙"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

        if message["role"] == "assistant" and show_sources:
            src_idx = i // 2
            if src_idx < len(st.session_state.sources_history):
                srcs = st.session_state.sources_history[src_idx]
                if srcs:
                    label = "Sources · " + str(len(srcs))
                    with st.expander(label, expanded=False):
                        for s in srcs:
                            st.markdown(
                                '<div class="source-card">'
                                '<strong>' + s["title"] + '</strong>'
                                '<a href="' + s["url"] + '" target="_blank">'
                                + s["url"] + '</a></div>',
                                unsafe_allow_html=True,
                            )

# ── Chat input ────────────────────────────────
pending    = st.session_state.pop("pending_q", None)
user_input = st.chat_input("Ask about Pharos Network...")
question   = pending or user_input

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🐙"):
        with st.spinner("Searching..."):
            try:
                answer, sources = bot.ask(question)
            except Exception as e:
                answer  = "An error occurred: " + str(e)
                sources = []

        st.markdown(answer)

        # Show a mini price chart inline if the question was about
        # price / market cap / the PROS token
        q = question.lower()
        if "price" in q or "market cap" in q or "pros" in q or "$pros" in q:
            with st.container(border=True):
                st.markdown(
                    '<div class="chart-card-label">$PROS · 24H PRICE</div>',
                    unsafe_allow_html=True,
                )
                chart_key = "pros_chart_msg_" + str(len(st.session_state.messages))
                render_price_chart(get_price_chart_df(), chart_key=chart_key)

        if show_sources and sources:
            label = "Sources · " + str(len(sources))
            with st.expander(label, expanded=True):
                for s in sources:
                    st.markdown(
                        '<div class="source-card">'
                        '<strong>' + s["title"] + '</strong>'
                        '<a href="' + s["url"] + '" target="_blank">'
                        + s["url"] + '</a></div>',
                        unsafe_allow_html=True,
                    )

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.sources_history.append(sources)