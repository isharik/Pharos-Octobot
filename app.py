"""
app.py
------
OctoBot Streamlit Web UI

Run:
streamlit run app.py
"""

import streamlit as st


# PAGE CONFIG
st.set_page_config(
    page_title="OctoBot",
    page_icon="🐙",
    layout="wide"
)


# STYLE
st.markdown("""
<style>

.main-title{
text-align:center;
padding-bottom:15px;
}

.source{
background:#f6f6f6;
padding:10px;
border-radius:10px;
margin-top:6px;
}

</style>
""", unsafe_allow_html=True)


# LOAD BOT
@st.cache_resource
def load_bot():

    try:
        from octobot import OctoBot

        bot = OctoBot()

        return bot, None

    except Exception as e:

        return None, str(e)


bot, error = load_bot()


# SIDEBAR
with st.sidebar:

    st.title("🐙 OctoBot")

    st.caption(
        "Pharos Documentation Assistant"
    )

    st.divider()

    st.markdown(
        """
Ask questions about:

• Pharos Network  
• SPNs  
• Consensus  
• Native Restaking  
• L1 Core  
"""
    )

    st.divider()

    show_sources = st.toggle(
        "Show Sources",
        value=True
    )

    if st.button(
        "Reset Chat"
    ):

        st.session_state.messages = []

        if bot:
            bot.reset_memory()

        st.rerun()


# HEADER
st.markdown(
    """
<div class='main-title'>
<h1>🐙 OctoBot</h1>
<p>Powered by RAG + Gemini</p>
</div>
""",
unsafe_allow_html=True
)


# CHECK LOAD
if error:

    st.error(error)

    st.stop()


# STATS
count = bot.vectorstore._collection.count()

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Knowledge Chunks",
        count
    )

with c2:
    st.metric(
        "Model",
        "Gemini"
    )

with c3:
    st.metric(
        "Database",
        "Chroma"
    )


st.divider()


# SESSION MEMORY
if "messages" not in st.session_state:

    st.session_state.messages = []

if "sources" not in st.session_state:

    st.session_state.sources = []


# SHOW CHAT
for i, msg in enumerate(
    st.session_state.messages
):

    avatar = (
        "👤"
        if msg["role"] == "user"
        else "🐙"
    )

    with st.chat_message(
        msg["role"],
        avatar=avatar
    ):

        st.markdown(
            msg["content"]
        )

        if (
            msg["role"]
            == "assistant"
            and show_sources
            and i // 2 < len(
                st.session_state.sources
            )
        ):

            sources = (
                st.session_state
                .sources[
                    i // 2
                ]
            )

            if sources:

                with st.expander(
                    "Sources"
                ):

                    for src in sources:

                        st.markdown(
f"""
<div class='source'>
<b>{src["title"]}</b>
<br>
{src["url"]}
</div>
""",
unsafe_allow_html=True
                        )


# INPUT
question = st.chat_input(
    "Ask OctoBot..."
)


if question:

    st.session_state.messages.append(
        {
            "role":"user",
            "content":question
        }
    )

    with st.chat_message(
        "user",
        avatar="👤"
    ):

        st.markdown(
            question
        )

    with st.chat_message(
        "assistant",
        avatar="🐙"
    ):

        with st.spinner(
            "Searching docs..."
        ):

            try:

                answer, sources = (
                    bot.ask(
                        question
                    )
                )

            except Exception as e:

                answer = (
                    f"Error: {e}"
                )

                sources = []

        st.markdown(
            answer
        )

        if (
            show_sources
            and sources
        ):

            with st.expander(
                "Sources"
            ):

                for src in sources:

                    st.markdown(
f"""
<div class='source'>
<b>{src["title"]}</b>
<br>
{src["url"]}
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