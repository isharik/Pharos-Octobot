"""
app.py
------
Phase 6: OctoBot's Streamlit web interface.

Run this command from your 'octobot' folder:
    streamlit run app.py

This will automatically open http://localhost:8501 in your browser.

Features:
  - Chat interface (like ChatGPT)
  - Shows source documents used for each answer
  - Session memory (remembers your conversation)
  - Reset button to start a new conversation
"""

import streamlit as st
from build_vectorstore import build_vectorstore
from build_vectorstore import load_documents, split_documents, build_vectorstore

# ─────────────────────────────────────────────
# PAGE CONFIGURATION
# Must be the FIRST Streamlit command called
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="OctoBot — Pharos Docs Assistant",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS — gives the app a polished look
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Main header */
    .main-header {
        text-align: center;
        padding: 1rem 0;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 1rem;
    }
    /* Source card styling */
    .source-card {
        background: #f8f9fa;
        border-left: 3px solid #667eea;
        padding: 0.5rem 0.75rem;
        margin: 0.25rem 0;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
    }
    .source-card a {
        color: #667eea;
        text-decoration: none;
    }
    /* Status badges */
    .status-ok { color: #28a745; font-weight: bold; }
    .status-err { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD OCTOBOT (cached so it only loads once)
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="🐙 Loading OctoBot knowledge base...")
def load_octobot():
    """
    Load OctoBot once and cache it for the session.
    @st.cache_resource means this function runs only once
    and reuses the result for all users/reruns.
    """
    try:
        from octobot import OctoBot
        bot = OctoBot()
        return bot, None  # (bot, error)
    except FileNotFoundError as e:
        return None, str(e)
    except Exception as e:
        return None, f"Unexpected error: {e}"


# ─────────────────────────────────────────────
# INITIALIZE SESSION STATE
#
# st.session_state persists data across reruns
# (Streamlit reruns your script on every interaction)
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # Chat history for display
if "sources_history" not in st.session_state:
    st.session_state.sources_history = []  # Sources per message


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://img.icons8.com/fluency/96/octopus.png",
        width=80
    )
    st.title("OctoBot")
    st.caption("Pharos Documentation Assistant")
    st.divider()

    st.markdown("### 📋 About")
    st.markdown(
        "OctoBot answers questions **only** from the "
        "[Pharos documentation](https://docs.pharos.xyz). "
        "It will not guess or make things up."
    )
    st.divider()

    st.markdown("### ⚙️ Settings")
    show_sources = st.toggle("Show source citations", value=True)
    st.divider()

    if st.button("🔄 Reset Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.sources_history = []
        # Also reset the bot's internal memory
        bot, err = load_octobot()
        if bot:
            bot.reset_memory()
        st.success("Conversation cleared!")
        st.rerun()

    st.divider()
    st.markdown("### 💡 Example Questions")
    example_questions = [
        "What is Pharos Network?",
        "What are SPNs?",
        "How does consensus work?",
        "What is Native Restaking?",
        "What is L1-Core?",
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True, key=f"ex_{q}"):
            st.session_state["pending_question"] = q
            st.rerun()


# ─────────────────────────────────────────────
# MAIN CONTENT AREA
# ─────────────────────────────────────────────
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.title("🐙 OctoBot")
st.caption("Your Pharos Documentation Assistant — Powered by RAG + Gemini")
st.markdown('</div>', unsafe_allow_html=True)

import os

vectorstore_path = "path/to/your/vectorstore/files"

documents = load_documents()
chunks = split_documents(documents)

print(f"Number of chunks: {len(chunks)}")
for i, chunk in enumerate(chunks):
    if not chunk.metadata:
        print(f"Chunk {i} is missing metadata!")
    else:
        print(f"Chunk {i} has metadata: {chunk.metadata}")

        
if not os.path.exists(vectorstore_path):
    documents = load_documents()
    chunks = split_documents(documents)
    build_vectorstore(chunks)  # Now you call it with chunks inside the block

# Load the bot
bot, load_error = load_octobot()

if load_error:
    st.error(f"""
    ❌ **OctoBot could not start.**

    **Error:** {load_error}

    **To fix this, run in your terminal:**
    ```
    python build_vectorstore.py
    ```
    Then refresh this page.
    """)
    st.stop()

# Show knowledge base stats
chunk_count = bot.vectorstore._collection.count()
col1, col2, col3 = st.columns(3)
col1.metric("📚 Knowledge Chunks", chunk_count)
col2.metric("🤖 Model", "Gemini")
col3.metric("🗄️ Vector DB", "ChromaDB")

st.divider()

# ─────────────────────────────────────────────
# CHAT HISTORY DISPLAY
# ─────────────────────────────────────────────
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar="👤" if message["role"] == "user" else "🐙"):
        st.markdown(message["content"])

        # Show sources for assistant messages
        if (
            message["role"] == "assistant"
            and show_sources
            and i < len(st.session_state.sources_history)
        ):
            sources = st.session_state.sources_history[i // 2]  # i//2 maps to source index
            if sources:
                with st.expander(f"📚 Sources ({len(sources)} page(s) used)", expanded=False):
                    for src in sources:
                        st.markdown(
                            f'<div class="source-card">'
                            f'<strong>{src["title"]}</strong><br>'
                            f'<a href="{src["url"]}" target="_blank">{src["url"]}</a>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )


# ─────────────────────────────────────────────
# HANDLE EXAMPLE QUESTION BUTTONS
# ─────────────────────────────────────────────
pending = st.session_state.pop("pending_question", None)


# ─────────────────────────────────────────────
# CHAT INPUT BOX
# ─────────────────────────────────────────────
user_input = st.chat_input(
    "Ask OctoBot about Pharos documentation...",
    key="chat_input"
)

# Use pending question from sidebar button, or typed input
question = pending or user_input

if question:
    # Display user message
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    # Get OctoBot's answer
    with st.chat_message("assistant", avatar="🐙"):
        with st.spinner("🔍 Searching Pharos docs..."):
            try:
                answer, sources = bot.ask(question)
            except Exception as e:
                answer = f"❌ An error occurred: {e}"
                sources = []

        st.markdown(answer)

        # Show sources inline
        if show_sources and sources:
            with st.expander(f"📚 Sources ({len(sources)} page(s) used)", expanded=True):
                for src in sources:
                    st.markdown(
                        f'<div class="source-card">'
                        f'<strong>{src["title"]}</strong><br>'
                        f'<a href="{src["url"]}" target="_blank">{src["url"]}</a>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

    # Save to session state
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.sources_history.append(sources)