"""
octobot.py
----------
OctoBot core RAG engine.

Powered by:
- Gemini 2.5 Flash (LLM)
- HuggingFace sentence-transformers (embeddings — local, free)
- ChromaDB (vector store)

Multilingual: responds in the same language the user writes in.
General mode: falls back to Gemini when answer not in docs.

── Lifecycle note (fixes the "Chat page hangs on Loading Knowledge Base") ──
Loading the embedding model, opening Chroma, and constructing the Gemini
client are all expensive, process-wide, stateless resources. They are built
ONCE per server process via `st.cache_resource`-wrapped factory functions
below, and every OctoBot instance simply borrows the same cached objects —
constructing a second (or hundredth) OctoBot() no longer re-downloads the
embedding model or re-opens the vector store. app.py is responsible for
kicking this off in the background at app *startup* (not on Chat
navigation) — see `load_octobot()` in app.py.

Conversation memory (`chat_history`) is explicitly NOT part of this shared
state: it is passed into `ask()` by the caller (app.py keeps one list per
Streamlit session in `st.session_state`) so one user's conversation never
leaks into another's.
"""

import os
import requests
import streamlit as st
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CHROMA_DB_DIR   = "chroma_db"
COLLECTION_NAME = "pharos_docs"
TOP_K           = 5
GEMINI_MODEL    = "gemini-2.5-flash"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# ─────────────────────────────────────────────
# SYSTEM PROMPT — multilingual + anti-hallucination
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are OctoBot, a helpful and accurate documentation assistant \
for the Pharos blockchain network.

Your job is to answer questions ONLY using the documentation excerpts provided \
below in the <context> section.

RULES YOU MUST FOLLOW:
1. ONLY answer based on what is in the provided context.
2. If the answer is not in the context, respond EXACTLY with this sentence \
translated into the language the user wrote in:
   "I could not find that information in the Pharos documentation."
3. Do NOT guess, invent, or hallucinate any information.
4. Keep your answers clear, concise, and accurate.
5. When possible, structure your answer with bullet points for clarity.
6. Always be professional and helpful.
7. ALWAYS respond in the SAME language the user used in their question, \
regardless of what language the documentation context is written in. \
The documentation is in English, but translate your answer into the user's \
language while keeping technical terms (SPN, PROS, RWA, L1-Core, EVM) \
in their original form.
8. Hinglish, mixed-language questions (e.g. "PROS ka price kya hai?") \
should be answered in the same mixed style the user wrote in.

<context>
{context}
</context>

Remember: You are OctoBot. Only answer from the documentation above, \
and always respond in the same language as the user's question.
"""

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])


# ─────────────────────────────────────────────
# SHARED, PROCESS-WIDE RESOURCES
# Each factory is wrapped in @st.cache_resource, so no matter how many
# OctoBot() instances get constructed (or how many Streamlit sessions /
# reruns hit this module), the underlying embedding model / vector store /
# Gemini client are built exactly once per server process and reused.
# show_spinner=False: these are warmed up on a background thread by
# app.py's load_octobot(), never on the interactive request path, so
# there's no user-facing spinner to show anyway.
# ─────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def _get_embeddings(model_name: str) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name)


@st.cache_resource(show_spinner=False)
def _get_vectorstore(persist_dir: str, collection_name: str, model_name: str) -> Chroma:
    # model_name is part of the cache key (not used directly here) so a
    # change in embedding model correctly busts this cached vectorstore
    # instead of silently reusing one built with a different embedder.
    embeddings = _get_embeddings(model_name)
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )


@st.cache_resource(show_spinner=False)
def _get_gemini_client(model: str, temperature: float, api_key: str) -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)


def get_shared_resources():
    """Build (once) and return the shared embeddings/vectorstore/retriever/
    llm tuple. Safe to call from any thread — st.cache_resource itself is
    the single-flight guard, so concurrent callers never build duplicates.
    Raises if GEMINI_API_KEY is missing or the vector store doesn't exist,
    exactly like the old OctoBot.__init__ did."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. "
            "Add it to your .env file or Streamlit secrets."
        )
    if not os.path.exists(CHROMA_DB_DIR):
        raise FileNotFoundError(
            f"Vector store not found: '{CHROMA_DB_DIR}'. "
            "Run: python build_vectorstore.py"
        )

    embeddings = _get_embeddings(EMBEDDING_MODEL)
    vectorstore = _get_vectorstore(CHROMA_DB_DIR, COLLECTION_NAME, EMBEDDING_MODEL)
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": TOP_K},
    )
    llm = _get_gemini_client(GEMINI_MODEL, 0, api_key)
    return embeddings, vectorstore, retriever, llm


# ─────────────────────────────────────────────
# OCTOBOT CLASS
# ─────────────────────────────────────────────
class OctoBot:

    def __init__(self, price_fetcher=None):
        """
        price_fetcher: optional callable() -> dict with keys
            {price_usd, market_cap_usd, volume_24h, change_24h, ...}
            (the same shape app.py's cached get_pros_price() returns).
            When provided, ask() reuses that cached market-data lookup
            instead of hitting CoinGecko again for every price-related
            question. Falls back to an internal (uncached) CoinGecko
            call only if no fetcher is supplied — kept for standalone /
            terminal use (see `__main__` below).
        """
        print("Initializing OctoBot...")

        # All expensive, stateless resources are shared/cached at module
        # level — constructing OctoBot never rebuilds them.
        self.embeddings, self.vectorstore, self.retriever, self.llm = get_shared_resources()

        self._price_fetcher = price_fetcher

        count = self.vectorstore._collection.count()
        print(f"OctoBot ready! {count} chunks loaded.")

    # ─────────────────────────────────────────
    def _format_docs(self, docs):
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            title  = doc.metadata.get("title", "untitled")
            parts.append(
                f"[Excerpt {i}] {title}\n"
                f"Source: {source}\n\n"
                f"{doc.page_content}"
            )
        return "\n\n---\n\n".join(parts)

    # ─────────────────────────────────────────
    def _get_live_pros_data(self):
        """Fetch live PROS price. Prefers the caller-supplied cached
        fetcher (app.py's get_pros_price(), which is throttled/cached
        across the whole app) so this never issues its own uncached
        CoinGecko request per question. Falls back to a direct,
        short-timeout CoinGecko call only when no fetcher was supplied
        (e.g. running octobot.py standalone from the terminal)."""
        if self._price_fetcher is not None:
            try:
                data = self._price_fetcher() or {}
                if not data.get("available", True) and data.get("price_usd") is None:
                    return None
                price = data.get("price_usd")
                if price is None:
                    return None
                return {
                    "price":      price,
                    "market_cap": data.get("market_cap_usd"),
                    "change_24h": data.get("change_24h"),
                }
            except Exception as e:
                print(f"Price fetch error (shared fetcher): {e}")
                return None

        # Standalone fallback — no shared/cached fetcher available.
        try:
            r = requests.get(
                "https://api.coingecko.com/api/v3/simple/price"
                "?ids=pharos-network&vs_currencies=usd"
                "&include_market_cap=true&include_24hr_change=true",
                timeout=5
            )
            data = r.json().get("pharos-network", {})
            if not data:
                return None
            return {
                "price":      data.get("usd"),
                "market_cap": data.get("usd_market_cap"),
                "change_24h": data.get("usd_24h_change"),
            }
        except Exception as e:
            print(f"Price fetch error: {e}")
            return None

    # ─────────────────────────────────────────
    def _extract_sources(self, docs):
        sources = []
        seen    = set()
        for doc in docs:
            url   = doc.metadata.get("source", "")
            title = doc.metadata.get("title", "Untitled")
            if url and url not in seen:
                seen.add(url)
                sources.append({"url": url, "title": title})
        return sources

    # ─────────────────────────────────────────
    def ask(self, question: str, chat_history: list = None):
        """
        Main method — retrieves answer from docs.
        Injects live PROS price when question is price-related.

        chat_history: the CALLER's own conversation memory (a list of
        Human/AIMessage), e.g. st.session_state[...] in app.py — one per
        Streamlit session. This method reads it for prompt context and
        appends this turn to it in place; it is NEVER stored on `self`,
        so a single shared/cached OctoBot instance never mixes one
        user's conversation into another's. Pass None for a stateless,
        single-shot call (e.g. build-path / premium-answer generation).

        Returns (answer_str, sources_list).
        """
        if chat_history is None:
            chat_history = []

        relevant_docs = self.retriever.invoke(question)

        if not relevant_docs:
            return (
                "I could not find that information in the Pharos documentation.",
                []
            )

        context = self._format_docs(relevant_docs)

        # Inject live price data for token-related questions
        q_lower = question.lower()
        price_keywords = ["price", "market cap", "pros", "$pros", "token",
                          "worth", "value", "trading", "buy", "sell", "usd"]
        if any(kw in q_lower for kw in price_keywords):
            live = self._get_live_pros_data()
            if live and live.get("price"):
                chg_str = f"{live['change_24h']:+.2f}%" if live.get("change_24h") else "N/A"
                context += (
                    "\n\nLIVE PROS TOKEN DATA (from CoinGecko):\n"
                    f"Current Price: ${live['price']:.4f} USD\n"
                    f"Market Cap: ${live['market_cap']:,.0f}\n"
                    f"24h Change: {chg_str}"
                )

        chain = PROMPT_TEMPLATE | self.llm | StrOutputParser()

        answer = chain.invoke({
            "context":      context,
            "chat_history": chat_history,
            "question":     question,
        })

        chat_history.append(HumanMessage(content=question))
        chat_history.append(AIMessage(content=answer))

        sources = self._extract_sources(relevant_docs)
        return answer, sources

    # ─────────────────────────────────────────
    def reset_memory(self, chat_history: list) -> None:
        """Clears the CALLER's history list in place (per-session — see
        `ask()`). Kept as a method for API-compatibility / terminal use."""
        chat_history.clear()
        print("Memory cleared.")


# ─────────────────────────────────────────────
# TERMINAL TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    bot = OctoBot()
    history = []
    print("\nOctoBot Ready — type 'quit' to exit, 'reset' to clear memory\n")

    while True:
        q = input("You: ").strip()
        if q.lower() in ["quit", "exit"]:
            break
        if q.lower() == "reset":
            bot.reset_memory(history)
            continue
        answer, sources = bot.ask(q, chat_history=history)
        print(f"\nOctoBot: {answer}")
        if sources:
            print("\nSources:")
            for s in sources:
                print(f"  {s['title']} — {s['url']}")
        print()