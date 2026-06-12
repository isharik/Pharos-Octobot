"""
app.py  (REDESIGNED — Pharos Brand Theme)
------------------------------------------
OctoBot Streamlit UI redesigned with:
- Pharos logo as the hero centerpiece
- Deep royal blue (#1A1AFF) Pharos brand palette
- Dark background matching Pharos Network aesthetic
- Geometric accents inspired by the Pharos logo mark
- Clean sharp typography (Syne + DM Sans via Google Fonts)
- Animated elements for a premium Web3 feel

HOW TO RUN:
    streamlit run app.py
"""

import streamlit as st

# ─────────────────────────────────────────────
# PAGE CONFIG — must be first Streamlit command
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="OctoBot — Pharos AI Assistant",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded" \
    
)

# ─────────────────────────────────────────────
# PHAROS BRAND THEME + CUSTOM CSS
# Colors extracted from Pharos logo + docs site:
#   Primary blue:   #1A1AFF  (deep electric blue)
#   Bright blue:    #3D3DFF  (hover/accent)
#   Light blue:     #6B8CFF  (secondary accent)
#   Dark bg:        #0A0A12  (near-black with blue tint)
#   Surface:        #10101E  (card backgrounds)
#   Border:         #1E1E3A  (subtle borders)
#   Text primary:   #FFFFFF
#   Text secondary: #A0A8CC
# ─────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet">

<style>
/* ── ROOT VARIABLES ─────────────────────────────────── */
:root {
    --blue-primary:   #1A1AFF;
    --blue-bright:    #3D3DFF;
    --blue-light:     #6B8CFF;
    --blue-glow:      rgba(26, 26, 255, 0.3);
    --blue-subtle:    rgba(26, 26, 255, 0.08);
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

/* ── GLOBAL RESET ───────────────────────────────────── */
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

/* ── HIDE STREAMLIT CHROME ──────────────────────────── */
#MainMenu, footer {
    visibility: hidden !important;
}
.stDeployButton { display: none !important; }

/* ── SIDEBAR ────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: var(--bg-surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--text-primary) !important;
}

/* ── LOGO HERO SECTION ──────────────────────────────── */
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

/* Glowing ring behind logo */
.logo-wrapper::before {
    content: '';
    position: absolute;
    inset: -16px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(26,26,255,0.25) 0%, transparent 70%);
    animation: pulse-glow 3s ease-in-out infinite;
}

/* Outer geometric ring */
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

/* Horizontal divider line with blue glow */
.pharos-divider {
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--blue-primary), transparent);
    margin: 0.5rem 0 1.5rem 0;
    opacity: 0.6;
}

/* ── METRICS ROW ────────────────────────────────────── */
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
    font-family: var(--font-body) !important;
}
[data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-family: var(--font-display) !important;
    font-weight: 700 !important;
    font-size: 1.3rem !important;
}

/* ── CHAT MESSAGES ──────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 0.4rem 0 !important;
}

/* User message bubble */
[data-testid="stChatMessage"][data-testid*="user"],
.stChatMessage:has([data-testid="chatAvatarIcon-user"]) {
    background: var(--blue-subtle) !important;
    border: 1px solid rgba(26,26,255,0.2) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
}

/* Assistant message */
.stChatMessage:has([data-testid="chatAvatarIcon-assistant"]) {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
}

/* ── CHAT INPUT ─────────────────────────────────────── */
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

/* ── EXPANDER (Sources) ─────────────────────────────── */
[data-testid="stExpander"] {
    background: var(--bg-raised) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    margin-top: 0.5rem !important;
}
[data-testid="stExpander"] summary {
    color: var(--text-secondary) !important;
    font-size: 0.82rem !important;
    font-family: var(--font-body) !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--blue-light) !important;
}

/* ── SOURCE CARDS ───────────────────────────────────── */
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
    font-family: var(--font-body) !important;
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

/* ── SIDEBAR BUTTONS ────────────────────────────────── */
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

/* Reset button stands out */
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

/* ── TOGGLE ─────────────────────────────────────────── */
[data-testid="stToggle"] label {
    color: var(--text-secondary) !important;
    font-size: 0.85rem !important;
    font-family: var(--font-body) !important;
}

/* ── SECTION LABELS ─────────────────────────────────── */
.sidebar-section {
    font-family: var(--font-display) !important;
    font-size: 0.7rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--text-muted) !important;
    margin: 1rem 0 0.5rem 0 !important;
}

/* ── SPINNER ─────────────────────────────────────────── */
[data-testid="stSpinner"] {
    color: var(--blue-light) !important;
}

/* ── SCROLLBAR ──────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg-dark); }
::-webkit-scrollbar-thumb {
    background: var(--border-bright);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--blue-primary);
}

/* ── HORIZONTAL RULE ────────────────────────────────── */
hr {
    border-color: var(--border) !important;
    margin: 0.8rem 0 !important;
}

/* ── ALERT / SUCCESS BOXES ──────────────────────────── */
[data-testid="stAlert"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
}

/* ── STATUS BAR ─────────────────────────────────────── */
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

/* ── WELCOME MESSAGE ────────────────────────────────── */
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
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ENCODE LOGO TO BASE64 SO IT WORKS RELIABLY
# IN STREAMLIT (avoids file path issues)
# ─────────────────────────────────────────────
import base64, os

def get_logo_base64() -> str:
    """
    Look for the Pharos logo in common locations.
    Returns base64 string or empty string if not found.
    """
    search_paths = [
        "pharos_logo.jpg",
        "pharos_logo.png",
        "assets/pharos_logo.jpg",
        "assets/pharos_logo.png",
    ]
    for path in search_paths:
        if os.path.exists(path):
            with open(path, "rb") as f:
                ext = path.rsplit(".", 1)[-1].lower()
                mime = "image/jpeg" if ext == "jpg" else "image/png"
                b64 = base64.b64encode(f.read()).decode()
                return f"data:{mime};base64,{b64}"
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
        return None, f"Unexpected error: {e}"


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

    # ── Logo + name in sidebar ───────────────
    logo_b64 = get_logo_base64()
    if logo_b64:
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:0.5rem 0 1rem 0;">
            <img src="{logo_b64}" style="width:38px;height:38px;border-radius:50%;
                filter:drop-shadow(0 0 8px rgba(26,26,255,0.7));" />
            <div>
                <div style="font-family:'Syne',sans-serif;font-weight:800;
                    font-size:1rem;color:#FFFFFF;line-height:1.1;">OctoBot</div>
                <div style="font-size:0.7rem;color:#5A5A8A;
                    letter-spacing:0.06em;text-transform:uppercase;">Pharos AI Assistant</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="padding:0.5rem 0 1rem 0;">
            <div style="font-family:'Syne',sans-serif;font-weight:800;
                font-size:1.1rem;color:#FFFFFF;">🐙 OctoBot</div>
            <div style="font-size:0.7rem;color:#5A5A8A;
                letter-spacing:0.06em;text-transform:uppercase;">Pharos AI Assistant</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    # ── Settings ─────────────────────────────
    st.markdown('<p class="sidebar-section">Settings</p>', unsafe_allow_html=True)
    show_sources = st.toggle("Show source citations", value=True)

    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    # ── Reset button ──────────────────────────
    st.markdown('<div class="reset-btn">', unsafe_allow_html=True)
    if st.button("↺  New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sources_history = []
        bot, err = load_octobot()
        if bot:
            bot.reset_memory()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    # ── Example questions ─────────────────────
    st.markdown('<p class="sidebar-section">Example Questions</p>', unsafe_allow_html=True)
    examples = [
        "What is Pharos Network?",
        "What is PROS?",
        "What are SPNs?",
        "How does Native Restaking work?",
        "How do I build on Pharos?",
        "What are RWA use cases?",
    ]
    for q in examples:
        if st.button(q, use_container_width=True, key=f"ex_{q}"):
            st.session_state["pending_q"] = q
            st.rerun()

    st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

    # ── Status indicator ──────────────────────
    st.markdown("""
    <div class="status-bar">
        <div class="status-dot"></div>
        <span>Connected to knowledge base</span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:1.5rem;font-size:0.72rem;color:#5A5A8A;
        font-family:'DM Sans',sans-serif;line-height:1.6;">
        OctoBot answers only from verified<br>
        Pharos documentation sources.<br>
        Zero hallucination guaranteed.
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN AREA
# ─────────────────────────────────────────────

# ── Hero Section ─────────────────────────────
logo_b64 = get_logo_base64()

if logo_b64:
    st.markdown(f"""
    <div class="pharos-hero">
        <div class="logo-wrapper">
            <img src="{logo_b64}" class="pharos-logo-img" alt="Pharos Logo" />
        </div>
        <h1 class="hero-title">OctoBot</h1>
        <p class="hero-subtitle">Pharos Network · AI Documentation & Agent Skill for Pharos</p>
    </div>
    """, unsafe_allow_html=True)
else:
    # Fallback if logo file not found
    st.markdown("""
    <div class="pharos-hero">
        <div style="font-size:3.5rem;margin-bottom:0.5rem;
            filter:drop-shadow(0 0 20px rgba(26,26,255,0.6));">🐙</div>
        <h1 class="hero-title">OctoBot</h1>
        <p class="hero-subtitle">Pharos Network · AI Documentation Assistant</p>
        <div style="margin-top:0.75rem;padding:0.4rem 0.9rem;
            background:rgba(26,26,255,0.1);border:1px solid rgba(26,26,255,0.3);
            border-radius:8px;font-size:0.78rem;color:#6B8CFF;font-family:'DM Sans',sans-serif;">
            💡 Add your Pharos logo: save it as <code>pharos_logo.jpg</code>
            in your octobot folder, then refresh.
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

# ── Load bot + error handling ─────────────────
bot, load_error = load_octobot()

if load_error:
    st.markdown(f"""
    <div style="background:rgba(255,50,50,0.08);border:1px solid rgba(255,50,50,0.3);
        border-radius:12px;padding:1.5rem;margin:1rem 0;">
        <div style="font-family:'Syne',sans-serif;font-weight:700;
            color:#FF6B6B;margin-bottom:0.5rem;">⚠ OctoBot could not start</div>
        <div style="color:#A0A8CC;font-size:0.9rem;margin-bottom:1rem;">{load_error}</div>
        <div style="color:#5A5A8A;font-size:0.85rem;">
            Run in your terminal:<br>
            <code style="color:#6B8CFF;">python build_vectorstore.py</code><br>
            then refresh this page.
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Metrics row ───────────────────────────────
chunk_count = bot.vectorstore._collection.count()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Knowledge Chunks", f"{chunk_count:,}")
c2.metric("API Source", "Studio/Gemini")
c3.metric("Vector DB", "ChromaDB")
c4.metric("Mode", "RAG · No Hallucination")

st.markdown('<div class="pharos-divider"></div>', unsafe_allow_html=True)

# ── Welcome card (shown only when no messages) ─
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

# ── Chat history ──────────────────────────────
for i, message in enumerate(st.session_state.messages):
    avatar = "👤" if message["role"] == "user" else "🐙"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

        # Show sources for assistant messages
        if (
            message["role"] == "assistant"
            and show_sources
        ):
            src_idx = i // 2
            if src_idx < len(st.session_state.sources_history):
                sources = st.session_state.sources_history[src_idx]
                if sources:
                    with st.expander(f"📎 {len(sources)} source(s) used", expanded=False):
                        for src in sources:
                            st.markdown(
                                f'<div class="source-card">'
                                f'<strong>{src["title"]}</strong>'
                                f'<a href="{src["url"]}" target="_blank">{src["url"]}</a>'
                                f'</div>',
                                unsafe_allow_html=True,
                            )

# ── Handle sidebar example button clicks ──────
pending = st.session_state.pop("pending_q", None)

# ── Chat input ────────────────────────────────
user_input = st.chat_input("Ask about Pharos Network...")
question = pending or user_input

if question:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    # Get answer
    with st.chat_message("assistant", avatar="🐙"):
        with st.spinner("Searching Pharos knowledge base..."):
            try:
                answer, sources = bot.ask(question)
            except Exception as e:
                answer = f"An error occurred: {e}"
                sources = []

        st.markdown(answer)

        if show_sources and sources:
            with st.expander(f"📎 {len(sources)} source(s) used", expanded=True):
                for src in sources:
                    st.markdown(
                        f'<div class="source-card">'
                        f'<strong>{src["title"]}</strong>'
                        f'<a href="{src["url"]}" target="_blank">{src["url"]}</a>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.sources_history.append(sources)