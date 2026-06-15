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
import streamlit.components.v1 as components
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
CHART_CACHE_SECONDS = 900   # 15 minutes — charts don't need 5-min freshness


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
# VOICE OUTPUT HELPER (Web Speech API speechSynthesis)
# ─────────────────────────────────────────────
def speak_text(text: str) -> None:
    """
    Render a tiny invisible component that speaks the given text
    aloud using the browser's built-in speechSynthesis API.

    Improvements for naturalness:
    - Strips ALL markdown (tables, headers, lists, bold/italic, links)
    - Picks the best-quality available voice for the language
      (prefers "Natural"/"Neural"/"Premium"/"Google" voices over
      robotic default ones)
    - Slightly slower rate + natural pitch for clearer speech

    Free, no extra packages, Chrome/Edge/Safari support.
    """
    import json
    import re as _re

    # ── Strip markdown so TTS doesn't read out symbols ──────────
    clean = text

    # Remove markdown table rows entirely (e.g. "| Price | $0.59 |")
    clean = _re.sub(r"^\|.*\|\s*$", "", clean, flags=_re.MULTILINE)
    # Remove table separator rows (e.g. "|---|---|")
    clean = _re.sub(r"^[\s|:-]+$", "", clean, flags=_re.MULTILINE)
    # Remove markdown headers (###, ##, #)
    clean = _re.sub(r"^#{1,6}\s*", "", clean, flags=_re.MULTILINE)
    # Remove bullet/list markers
    clean = _re.sub(r"^\s*[-*•]\s+", "", clean, flags=_re.MULTILINE)
    # Remove bold/italic/code markers
    clean = _re.sub(r"[*_`]", "", clean)
    # Remove markdown links but keep the link text: [text](url) -> text
    clean = _re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
    # Remove any remaining raw URLs
    clean = _re.sub(r"https?://\S+", "", clean)
    # Remove horizontal rule lines (---)
    clean = _re.sub(r"^-{2,}\s*$", "", clean, flags=_re.MULTILINE)
    # Collapse whitespace
    clean = _re.sub(r"\s+", " ", clean).strip()

    safe_text = json.dumps(clean)

    components.html(
        "<script>"
        "(function() {"
        "  try {"
        "    const synth = window.parent.speechSynthesis;"
        "    const text  = " + safe_text + ";"
        "    const lang  = (navigator.language || 'en-US');"
        ""
        "    function pickVoice(voices) {"
        "      const langPrefix = lang.split('-')[0].toLowerCase();"
        "      const candidates = voices.filter(v =>"
        "        v.lang.toLowerCase().startsWith(langPrefix)"
        "      );"
        "      const pool = candidates.length ? candidates : voices;"
        ""
        "      const qualityKeywords = ["
        "        'natural', 'neural', 'premium', 'enhanced',"
        "        'google', 'wavenet', 'studio'"
        "      ];"
        ""
        "      for (const kw of qualityKeywords) {"
        "        const match = pool.find(v =>"
        "          v.name.toLowerCase().includes(kw)"
        "        );"
        "        if (match) return match;"
        "      }"
        "      return pool[0] || null;"
        "    }"
        ""
        "    function speak() {"
        "      const voices = synth.getVoices();"
        "      const utter  = new SpeechSynthesisUtterance(text);"
        "      const voice  = pickVoice(voices);"
        "      if (voice) {"
        "        utter.voice = voice;"
        "        utter.lang  = voice.lang;"
        "      } else {"
        "        utter.lang  = lang;"
        "      }"
        "      utter.rate  = 0.95;"
        "      utter.pitch = 1.0;"
        "      utter.volume = 1.0;"
        "      synth.cancel();"
        "      synth.speak(utter);"
        "    }"
        ""
        "    if (synth.getVoices().length === 0) {"
        "      synth.onvoiceschanged = speak;"
        "    } else {"
        "      speak();"
        "    }"
        "  } catch (e) { console.log('TTS error', e); }"
        "})();"
        "</script>",
        height=0,
    )


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
        radial-gradient(ellipse 60% 40% at 50% 0%, rgba(26,26,255,0.05) 0%, transparent 55%),
        repeating-linear-gradient(0deg,  rgba(20,20,31,0.045) 0px, rgba(20,20,31,0.045) 1px, transparent 1px, transparent 56px),
        repeating-linear-gradient(90deg, rgba(20,20,31,0.045) 0px, rgba(20,20,31,0.045) 1px, transparent 1px, transparent 56px)
        !important;
    background-attachment: fixed !important;
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

/* ── CHART RANGE SELECTOR BUTTONS ───── */
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button {
    background: var(--bg-2) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: 14px !important;
    font-size: 11px !important;
    padding: 2px 6px !important;
    text-align: center !important;
    color: var(--txt-2) !important;
    min-height: 0 !important;
    line-height: 1.6 !important;
}
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button:hover {
    background: var(--p-subtle) !important;
    border-color: var(--p-blue) !important;
    color: var(--p-blue) !important;
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
.stChatInput,
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

/* ── CUSTOM LOADING SCREEN ──────────── */
.octobot-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 4.5rem 1rem 3.5rem 1rem;
    min-height: 50vh;
}
.octobot-loading-logo-wrap {
    position: relative;
    width: 96px;
    height: 96px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 1.5rem;
}
.octobot-loading-logo-wrap img,
.octobot-loading-logo-wrap .fallback-icon {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    position: relative;
    z-index: 3;
    filter: drop-shadow(0 2px 10px rgba(26,26,255,0.25));
}
.octobot-loading-logo-wrap .fallback-icon {
    font-size: 40px;
    line-height: 56px;
}
.octobot-ring {
    position: absolute;
    border-radius: 50%;
    border: 1.5px solid var(--p-blue);
    opacity: 0;
    animation: octobot-pulse 2.4s ease-out infinite;
}
.octobot-ring.r1 { width: 96px;  height: 96px;  animation-delay: 0s;   }
.octobot-ring.r2 { width: 96px;  height: 96px;  animation-delay: 0.8s; }
.octobot-ring.r3 { width: 96px;  height: 96px;  animation-delay: 1.6s; }
@keyframes octobot-pulse {
    0%   { transform: scale(0.55); opacity: 0.55; }
    70%  { transform: scale(1.35); opacity: 0; }
    100% { transform: scale(1.35); opacity: 0; }
}
.octobot-loading-title {
    font-family: var(--fn-d);
    font-size: 18px;
    font-weight: 700;
    color: var(--txt-1);
    letter-spacing: -0.01em;
    margin-bottom: 0.35rem;
}
.octobot-loading-sub {
    font-size: 12px;
    color: var(--txt-2);
    margin-bottom: 1.1rem;
}
.octobot-loading-dots {
    display: flex;
    gap: 6px;
}
.octobot-loading-dots span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--p-blue);
    animation: octobot-dot 1.2s ease-in-out infinite;
}
.octobot-loading-dots span:nth-child(2) { animation-delay: 0.15s; }
.octobot-loading-dots span:nth-child(3) { animation-delay: 0.30s; }
@keyframes octobot-dot {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.35; }
    40%           { transform: scale(1);   opacity: 1;    }
}
.octobot-loading-steps {
    margin-top: 1.6rem;
    display: flex;
    flex-direction: column;
    gap: 6px;
    font-size: 11px;
    color: var(--txt-3);
}
.octobot-loading-steps .step-done::before {
    content: "✓ ";
    color: var(--green);
    font-weight: 700;
}
.octobot-loading-steps .step-active::before {
    content: "○ ";
    color: var(--p-blue);
    font-weight: 700;
}


/* ── MIC / VOICE WIDGET ─────────────── */
.mic-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 0.4rem;
}
.mic-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 1px solid var(--border-2);
    background: var(--bg-1);
    color: var(--p-blue);
    cursor: pointer;
    transition: all 0.15s ease;
    flex-shrink: 0;
}
.mic-btn:hover {
    border-color: var(--p-blue);
    background: var(--p-subtle);
}
.mic-btn.recording {
    background: var(--p-blue);
    border-color: var(--p-blue);
    color: #fff;
    animation: mic-pulse 1.2s ease-in-out infinite;
}
@keyframes mic-pulse {
    0%, 100% { box-shadow: 0 0 0 0 var(--p-glow); }
    50%      { box-shadow: 0 0 0 6px var(--p-glow); }
}
.mic-status {
    font-size: 11px;
    color: var(--txt-2);
}
.mic-unsupported {
    font-size: 10px;
    color: var(--txt-3);
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
# show_spinner=False because we render our own
# branded full-page loading screen below instead
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def load_octobot():
    try:
        from octobot import OctoBot
        return OctoBot(), None
    except FileNotFoundError as e:
        return None, str(e)
    except Exception as e:
        return None, str(e)

def get_price_chart_df(days: str = "1"):
    """
    Fetch $PROS price history from CoinGecko for the area chart.

    days: CoinGecko range parameter -
          "1"   -> last 24 hours (high-resolution, ~5 min intervals)
          "7"   -> last 7 days
          "30"  -> last 30 days
          "90"  -> last 90 days
          "365" -> last 1 year
          "max" -> entire available history since listing

    Each range is cached separately in session_state for 5 minutes
    so switching between ranges doesn't always hit the API, but each
    range still refreshes independently.

    Returns a DataFrame with columns [time, price] or None on failure.
    """
    now        = time.time()
    cache_all  = st.session_state.get("pros_chart_cache", {})
    cached     = cache_all.get(days, {})

    if cached.get("df") is not None and now - cached.get("fetched_at", 0) < CHART_CACHE_SECONDS:
        return cached["df"]

    try:
        url = (
            "https://api.coingecko.com/api/v3/coins/" + COINGECKO_ASSET_ID +
            "/market_chart?vs_currency=usd&days=" + days
        )
        r = requests.get(url, timeout=5, headers={"Accept": "application/json"})
        r.raise_for_status()
        prices = r.json().get("prices", [])
        if not prices:
            raise ValueError("Empty chart data")

        df = pd.DataFrame(prices, columns=["time", "price"])
        df["time"] = pd.to_datetime(df["time"], unit="ms")

        cache_all[days] = {"df": df, "fetched_at": now}
        st.session_state["pros_chart_cache"] = cache_all
        return df

    except Exception:
        # Keep showing the last good chart for this range if available
        return cached.get("df")


def render_price_chart(df: pd.DataFrame, chart_key: str = "pros_chart", days: str = "1") -> None:
    """
    Render a professional Pharos-themed area chart for $PROS price history.
    White/blue color scheme, gradient fill, clean axes, no legend clutter.

    Axis formatting adapts to the selected range:
    - "1"  (24h)  -> hour:minute ticks, hover shows time
    - "7"/"30"    -> day + month ticks, hover shows date + time
    - "90"+/"max" -> month + year ticks, hover shows date
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

    # Pick axis tick format and hover format based on range
    if days == "1":
        tick_format  = "%H:%M"
        hover_format = "$%{y:.4f}<br>%{x|%H:%M}<extra></extra>"
    elif days in ("7", "30"):
        tick_format  = "%b %d"
        hover_format = "$%{y:.4f}<br>%{x|%b %d, %H:%M}<extra></extra>"
    else:
        tick_format  = "%b %Y"
        hover_format = "$%{y:.4f}<br>%{x|%b %d, %Y}<extra></extra>"

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"],
        y=df["price"],
        mode="lines",
        line=dict(color=line_color, width=2, shape="spline", smoothing=0.4),
        fill="tozeroy",
        fillcolor=fill_color,
        hovertemplate=hover_format,
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
            tickformat=tick_format,
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

# ── Voice input: pick up transcript from URL query param ──────
# The mic widget below sets ?voice_q=... via JS, then reloads.
# We read it here once, then clear the param so it doesn't re-fire.
_voice_q = st.query_params.get("voice_q", "")
if _voice_q:
    st.session_state["pending_q"] = _voice_q
    st.query_params.clear()


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
    voice_reply  = st.toggle("Read answers aloud", value=False)

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

# ── Custom branded loading screen ─────────────
# load_octobot() is cached, so this only shows real
# loading time on the very first run (cold start).
# On reruns the cached result returns instantly and
# this placeholder is cleared right away.
_loading_placeholder = st.empty()

if logo_b64:
    _loading_logo_html = '<img src="' + logo_b64 + '" alt="Pharos" />'
else:
    _loading_logo_html = '<span class="fallback-icon">&#x1F419;</span>'

with _loading_placeholder.container():
    st.markdown(
        '<div class="octobot-loading">'
        '  <div class="octobot-loading-logo-wrap">'
        '    <div class="octobot-ring r1"></div>'
        '    <div class="octobot-ring r2"></div>'
        '    <div class="octobot-ring r3"></div>'
        + _loading_logo_html +
        '  </div>'
        '  <div class="octobot-loading-title">Waking up OctoBot</div>'
        '  <div class="octobot-loading-sub">Connecting to the Pharos knowledge base</div>'
        '  <div class="octobot-loading-dots"><span></span><span></span><span></span></div>'
        '  <div class="octobot-loading-steps">'
        '    <div class="step-done">Loading embeddings model</div>'
        '    <div class="step-done">Connecting to ChromaDB</div>'
        '    <div class="step-active">Preparing chat session</div>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Compact header row ────────────────────────
price_data  = get_pros_price()
bot, load_error = load_octobot()

# Loading complete — remove the loading screen
_loading_placeholder.empty()

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

    # ── PROS price chart with selectable time range ──────────────
    RANGE_OPTIONS = {
        "1D":  "1",
        "7D":  "7",
        "30D": "30",
        "90D": "90",
        "1Y":  "365",
        "All": "max",
    }
    RANGE_LABELS = {
        "1": "24H", "7": "7D", "30": "30D",
        "90": "90D", "365": "1Y", "max": "ALL-TIME",
    }

    if "pros_chart_range" not in st.session_state:
        st.session_state["pros_chart_range"] = "1"

    with st.container(border=True):
        label_col, btns_col = st.columns([2, 4])
        with label_col:
            current_label = RANGE_LABELS.get(st.session_state["pros_chart_range"], "24H")
            st.markdown(
                '<div class="chart-card-label">$PROS · ' + current_label + ' PRICE</div>',
                unsafe_allow_html=True,
            )
        with btns_col:
            range_cols = st.columns(len(RANGE_OPTIONS))
            for (label, days_val), col in zip(RANGE_OPTIONS.items(), range_cols):
                is_active = st.session_state["pros_chart_range"] == days_val
                btn_label = ("● " if is_active else "") + label
                if col.button(btn_label, key="range_" + days_val, use_container_width=True):
                    st.session_state["pros_chart_range"] = days_val
                    st.rerun()

        selected_days = st.session_state["pros_chart_range"]
        if "pros_chart_loaded" not in st.session_state:
            st.session_state["pros_chart_loaded"] = False

        if not st.session_state["pros_chart_loaded"]:
            if st.button("📈 Load price chart", key="load_chart_btn"):
                st.session_state["pros_chart_loaded"] = True
                st.rerun()
        else:
            chart_df = get_price_chart_df(days=selected_days)
            render_price_chart(chart_df, chart_key="pros_chart_main_" + selected_days, days=selected_days)
            
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
'<span style="font-size:11px;color:#9499A8;">Voice Improvements (Expected Soon)</span>'
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

        if message["role"] == "assistant":
            if st.button("🔊 Read aloud", key="replay_hist_" + str(i)):
                speak_text(message["content"])

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

# ── Voice input widget ─────────────────────────
components.html(
    """
    <div style="font-family: 'DM Sans', sans-serif;">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
        <button id="octobot-mic-btn" title="Ask by voice"
          style="display:flex;align-items:center;justify-content:center;
                 width:32px;height:32px;border-radius:50%;
                 border:1px solid #D6D9E0;background:#FFFFFF;color:#1A1AFF;
                 cursor:pointer;font-size:15px;transition:all .15s ease;flex-shrink:0;">
          &#127908;
        </button>
        <span id="octobot-mic-status" style="font-size:11px;color:#5B5F6E;">
          Tap the mic and ask your question out loud
        </span>
        <button id="octobot-mic-send" title="Send transcribed question"
          style="display:none;align-items:center;justify-content:center;
                 padding:4px 12px;border-radius:6px;border:1px solid #1A1AFF;
                 background:#1A1AFF;color:#FFFFFF;cursor:pointer;
                 font-size:11px;font-weight:600;flex-shrink:0;">
          Send &#8594;
        </button>
      </div>
      <div id="octobot-mic-fallback" style="display:none;margin-top:6px;">
        <textarea id="octobot-mic-fallback-text" readonly
          style="width:100%;min-height:40px;font-size:12px;padding:6px 8px;
                 border:1px solid #D6D9E0;border-radius:6px;
                 font-family:'DM Sans',sans-serif;color:#14141F;
                 background:#F7F8FA;resize:vertical;"></textarea>
        <div style="font-size:10px;color:#9499A8;margin-top:3px;">
          Auto-send blocked by browser — copy this text and paste it in the chat box below.
        </div>
      </div>
    </div>
    <script>
    (function() {
        const btn       = document.getElementById('octobot-mic-btn');
        const status    = document.getElementById('octobot-mic-status');
        const sendBtn   = document.getElementById('octobot-mic-send');
        const fallback  = document.getElementById('octobot-mic-fallback');
        const fallbackTxt = document.getElementById('octobot-mic-fallback-text');

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (!SpeechRecognition) {
            status.innerText = 'Voice input needs Chrome or Edge browser';
            btn.style.opacity = '0.4';
            btn.style.cursor = 'not-allowed';
            return;
        }

        const recognition = new SpeechRecognition();
        // continuous=true + interimResults=true makes recognition keep
        // listening across natural pauses instead of cutting off after
        // the first short phrase, and pick up quieter speech better.
        recognition.continuous      = true;
        recognition.interimResults  = true;
        recognition.maxAlternatives = 1;
        recognition.lang = navigator.language || 'en-US';

        let listening       = false;
        let finalTranscript = '';
        let silenceTimer    = null;

        function resetSilenceTimer() {
            if (silenceTimer) clearTimeout(silenceTimer);
            // Auto-stop after 3.5s of no new speech, so it doesn't
            // listen forever but gives plenty of time for pauses.
            silenceTimer = setTimeout(function() {
                if (listening) recognition.stop();
            }, 3500);
        }

        function sendToOctoBot(transcript) {
            // 1) Try direct same-origin navigation on the top window.
            //    Streamlit components are same-origin by default, so
            //    this usually works without being blocked.
            try {
                const url = new URL(window.top.location.href);
                url.searchParams.set('voice_q', transcript);
                window.top.location.assign(url.toString());
                return true;
            } catch (e1) {
                // 2) Fall back to parent frame.
                try {
                    const url2 = new URL(window.parent.location.href);
                    url2.searchParams.set('voice_q', transcript);
                    window.parent.location.assign(url2.toString());
                    return true;
                } catch (e2) {
                    return false;
                }
            }
        }

        btn.addEventListener('click', function() {
            if (listening) {
                recognition.stop();
                return;
            }
            finalTranscript = '';
            sendBtn.style.display = 'none';
            fallback.style.display = 'none';
            try {
                recognition.start();
            } catch (e) {
                status.innerText = 'Could not start microphone: ' + e.message;
            }
        });

        sendBtn.addEventListener('click', function() {
            if (!finalTranscript.trim()) return;
            status.innerText = 'Sending "' + finalTranscript.trim() + '"...';
            const ok = sendToOctoBot(finalTranscript.trim());
            if (!ok) {
                fallbackTxt.value = finalTranscript.trim();
                fallback.style.display = 'block';
                status.innerText = 'Heard: "' + finalTranscript.trim() + '"';
                fallbackTxt.select();
            }
        });

        recognition.onstart = function() {
            listening = true;
            btn.style.background = '#1A1AFF';
            btn.style.color = '#FFFFFF';
            btn.style.borderColor = '#1A1AFF';
            status.innerText = 'Listening... speak now (tap mic again to stop)';
            resetSilenceTimer();
        };

        recognition.onresult = function(event) {
            let interim = '';
            for (let i = event.resultIndex; i < event.results.length; i++) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript + ' ';
                } else {
                    interim += transcript;
                }
            }
            const shown = (finalTranscript + interim).trim();
            if (shown) {
                status.innerText = 'Heard: "' + shown + '"';
            }
            // Got new speech -> reset the auto-stop timer
            resetSilenceTimer();
        };

        recognition.onerror = function(event) {
            if (event.error === 'no-speech') {
                status.innerText = 'No speech detected — tap mic and try again, speak normally';
            } else if (event.error === 'not-allowed') {
                status.innerText = 'Microphone permission denied — allow mic access in browser settings';
            } else if (event.error === 'aborted') {
                // happens on manual stop - ignore, onend handles it
            } else {
                status.innerText = 'Mic error: ' + event.error + ' — try again';
            }
            listening = false;
            if (silenceTimer) clearTimeout(silenceTimer);
            resetBtn();
        };

        recognition.onend = function() {
            listening = false;
            if (silenceTimer) clearTimeout(silenceTimer);
            resetBtn();
            const text = finalTranscript.trim();
            if (text) {
                status.innerText = 'Heard: "' + text + '" — click Send to ask';
                sendBtn.style.display = 'inline-flex';
            } else if (status.innerText.indexOf('No speech') === -1
                       && status.innerText.indexOf('denied') === -1) {
                status.innerText = 'Tap the mic and ask your question out loud';
            }
        };

        function resetBtn() {
            btn.style.background = '#FFFFFF';
            btn.style.color = '#1A1AFF';
            btn.style.borderColor = '#D6D9E0';
        }
    })();
    </script>
    """,
    height=90,
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

        # ── Voice output: read the answer aloud if enabled ──────
        if voice_reply:
            speak_text(answer)

        # Manual replay button (works even if auto-read is off)
        if st.button("🔊 Read aloud", key="replay_" + str(len(st.session_state.messages))):
            speak_text(answer)

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