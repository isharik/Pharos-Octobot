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
"""

import os
import requests
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
# OCTOBOT CLASS
# ─────────────────────────────────────────────
class OctoBot:

    def __init__(self):
        print("Initializing OctoBot...")

        # API key check inside __init__ — NOT at module level
        # This prevents circular import when app.py imports octobot
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

        # Embeddings — MUST match build_vectorstore.py exactly
        self.embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL
        )

        self.vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=CHROMA_DB_DIR,
        )

        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOP_K},
        )

        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0,
            google_api_key=api_key,
        )

        self.chat_history = []

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
        """Fetch live PROS price from CoinGecko for context injection."""
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
    def ask(self, question: str):
        """
        Main method — retrieves answer from docs.
        Injects live PROS price when question is price-related.
        Returns (answer_str, sources_list).
        """
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
            "chat_history": self.chat_history,
            "question":     question,
        })

        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))

        sources = self._extract_sources(relevant_docs)
        return answer, sources

    # ─────────────────────────────────────────
    def reset_memory(self):
        self.chat_history = []
        print("Memory cleared.")


# ─────────────────────────────────────────────
# TERMINAL TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    bot = OctoBot()
    print("\nOctoBot Ready — type 'quit' to exit, 'reset' to clear memory\n")

    while True:
        q = input("You: ").strip()
        if q.lower() in ["quit", "exit"]:
            break
        if q.lower() == "reset":
            bot.reset_memory()
            continue
        answer, sources = bot.ask(q)
        print(f"\nOctoBot: {answer}")
        if sources:
            print("\nSources:")
            for s in sources:
                print(f"  {s['title']} — {s['url']}")
        print()