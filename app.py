"""
app.py
------
Phase 6: OctoBot Streamlit UI
Run:
streamlit run app.py
"""

import streamlit as st

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="OctoBot — Pharos Docs Assistant",
    page_icon="🐙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# STYLE
# ─────────────────────────────────────────────
st.markdown("""
<style>

.main-header{
text-align:center;
padding:1rem;
border-bottom:2px solid #f0f2f6;
margin-bottom:1rem;
}

.source-card{
background:#f8f9fa;
padding:10px;
margin:8px 0;
border-left:4px solid #667eea;
border-radius:8px;
}

.source-card a{
text-decoration:none;
color:#667eea;
}

</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# LOAD BOT
# ─────────────────────────────────────────────
@st.cache_resource(show_spinner="🐙 Loading knowledge base...")
def load_octobot():

    try:

        from octobot import OctoBot

        bot = OctoBot()

        return bot, None

    except Exception as e:

        return None, str(e)


# ─────────────────────────────────────────────
# SESSION
# ─────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "sources" not in st.session_state:
    st.session_state.sources = []


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:

    st.title("🐙 OctoBot")

    st.caption(
        "Pharos Documentation Assistant"
    )

    st.divider()

    show_sources = st.toggle(
        "Show Sources",
        value=True
    )

    if st.button(
        "🔄 Reset Conversation",
        use_container_width=True
    ):

        st.session_state.messages=[]

        st.session_state.sources=[]

        bot,_=load_octobot()

        if bot:
            bot.reset_memory()

        st.rerun()

    st.divider()

    examples=[

        "What is Pharos Network?",

        "What are SPNs?",

        "How does consensus work?",

        "What is Native Restaking?"
    ]

    for q in examples:

        if st.button(
            q,
            use_container_width=True
        ):
            st.session_state["pending"]=q
            st.rerun()


# ─────────────────────────────────────────────
# TITLE
# ─────────────────────────────────────────────
st.markdown(
'<div class="main-header">',
unsafe_allow_html=True
)

st.title(
"🐙 OctoBot"
)

st.caption(
"Powered by RAG + Gemini"
)

st.markdown(
"</div>",
unsafe_allow_html=True
)


# ─────────────────────────────────────────────
# LOAD
# ─────────────────────────────────────────────
bot,error=load_octobot()

if error:

    st.error(error)

    st.stop()


# Stats
count=bot.vectorstore._collection.count()

c1,c2,c3=st.columns(3)

c1.metric(
"📚 Chunks",
count
)

c2.metric(
"🤖 Model",
"Gemini"
)

c3.metric(
"🗄️ DB",
"Chroma"
)

st.divider()


# ─────────────────────────────────────────────
# DISPLAY HISTORY
# ─────────────────────────────────────────────
for idx,msg in enumerate(
    st.session_state.messages
):

    with st.chat_message(
        msg["role"]
    ):

        st.markdown(
            msg["content"]
        )

        # FIXED SOURCE DISPLAY
        if (

            msg["role"]=="assistant"

            and show_sources

            and idx//2 < len(
                st.session_state.sources
            )

        ):

            srcs=st.session_state.sources[
                idx//2
            ]

            if srcs:

                with st.expander(
                    f"📚 Sources ({len(srcs)})"
                ):

                    for src in srcs:

                        st.markdown(
f"""
<div class="source-card">
<b>{src["title"]}</b><br>
<a href="{src["url"]}">
{src["url"]}
</a>
</div>
""",
unsafe_allow_html=True
                        )


# ─────────────────────────────────────────────
# INPUT
# ─────────────────────────────────────────────
pending=st.session_state.pop(
"pending",
None
)

typed=st.chat_input(
"Ask OctoBot..."
)

question=(
pending
or typed
)


# ─────────────────────────────────────────────
# ASK
# ─────────────────────────────────────────────
if question:

    st.session_state.messages.append(
        {
            "role":"user",
            "content":question
        }
    )

    with st.chat_message(
        "user"
    ):

        st.markdown(
            question
        )

    with st.chat_message(
        "assistant"
    ):

        with st.spinner(
            "Searching docs..."
        ):

            try:

                answer,sources=bot.ask(
                    question
                )

            except Exception as e:

                answer=str(e)

                sources=[]

        st.markdown(
            answer
        )

        if (

            show_sources

            and sources

        ):

            with st.expander(
                f"📚 Sources ({len(sources)})",
                expanded=True
            ):

                for src in sources:

                    st.markdown(
f"""
<div class="source-card">
<b>{src["title"]}</b><br>
<a href="{src["url"]}">
{src["url"]}
</a>
</div>
""",
unsafe_allow_html=True
                    )

    st.session_state.messages.append(
        {
            "role":"assistant",
            "content":answer
        }
    )

    st.session_state.sources.append(
        sources
    )