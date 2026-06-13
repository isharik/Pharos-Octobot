"""
octobot.py
----------
Phase 5: OctoBot — the core RAG chatbot engine.

Now powered by:
- Gemini (LLM)
- HuggingFace embeddings
- ChromaDB

Run:
    python octobot.py
"""

import os
import requests
from dotenv import load_dotenv

# Gemini
from langchain_google_genai import ChatGoogleGenerativeAI

# Local embeddings
from langchain_huggingface import HuggingFaceEmbeddings

# Vector DB
from langchain_chroma import Chroma

# LangChain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser

load_dotenv()

# ─────────────────────────────────────────────
# CHECK API KEY
# ─────────────────────────────────────────────
if not os.getenv("GEMINI_API_KEY"):
    raise ValueError(
        "❌ GEMINI_API_KEY not found in .env"
    )

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
CHROMA_DB_DIR = "chroma_db"
COLLECTION_NAME = "pharos_docs"

TOP_K = 5

GEMINI_MODEL = "gemini-2.5-flash"

# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """
You are OctoBot, a helpful and accurate documentation assistant
for the Pharos blockchain network.

Answer ONLY using the provided context.

RULES:
1. Use ONLY documentation context.
2. If answer missing:
   "I could not find that information in the Pharos documentation."
3. Never hallucinate.
4. Be concise.
5. Use bullet points when useful.

<context>
{context}
</context>
"""

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}")
])


# ─────────────────────────────────────────────
# OCTOBOT
# ─────────────────────────────────────────────
class OctoBot:

    def __init__(self):

        print("🐙 Initializing OctoBot...")

        if not os.path.exists(CHROMA_DB_DIR):
            raise FileNotFoundError(
                f"Vector store missing: {CHROMA_DB_DIR}\n"
                "Run build_vectorstore.py first"
            )

        # SAME embeddings used during vector creation
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
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

        # Gemini
        self.llm = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )

        self.chat_history = []

        count = self.vectorstore._collection.count()

        print(
            f"✅ OctoBot ready! "
            f"({count} chunks loaded)"
        )

    # ─────────────────────────────────────────

    def _format_docs(self, docs):

        parts = []

        for i, doc in enumerate(docs, 1):

            source = doc.metadata.get(
                "source",
                "unknown"
            )

            title = doc.metadata.get(
                "title",
                "untitled"
            )

            parts.append(
                f"[Excerpt {i}] "
                f"{title}\n"
                f"Source: {source}\n\n"
                f"{doc.page_content}"
            )

        return "\n\n---\n\n".join(parts)
    
    # ─────────────────────────────────────────
    def _get_live_pros_data(self):
        try:
            url = (
                "https://api.coingecko.com/api/v3/coins/pharos-network"
            )
            r = requests.get(
                url,
                timeout=5
            )
            data = r.json()

            return {
                "price": data["market_data"]["current_price"]["usd"],
                "market_cap": data["market_data"]["market_cap"]["usd"]
            }

        except Exception as e:
            print(f"Error fetching PROS data: {e}")
            return None
    
    


    # ─────────────────────────────────────────

    def _extract_sources(self, docs):

        sources = []
        seen = set()

        for doc in docs:

            url = doc.metadata.get(
                "source",
                ""
            )

            title = doc.metadata.get(
                "title",
                "Untitled"
            )

            if url and url not in seen:

                seen.add(url)

                sources.append({
                    "url": url,
                    "title": title
                })

        return sources

    # ─────────────────────────────────────────

    def ask(self, question):

        relevant_docs = self.retriever.invoke(
            question
        )

        if not relevant_docs:

            return (
                "I could not find that information in the Pharos documentation.",
                []
            )

        context = self._format_docs(
            relevant_docs
        )
        
        question_lower = question.lower()
        if ("price" in question_lower or
            "market cap" in question_lower or
            "pros" in question_lower):
            live = self._get_live_pros_data()
            if live:
                context += (
                    "\n\nLIVE TOKEN DATA:\n"
                    f"Current Price: ${live['price']}\n"
                    f"Market Cap: ${live['market_cap']}"
                )

        chain = (
            PROMPT_TEMPLATE
            | self.llm
            | StrOutputParser()
        )

        answer = chain.invoke({
            "context": context,
            "chat_history": self.chat_history,
            "question": question
        })

        self.chat_history.append(
            HumanMessage(
                content=question
            )
        )

        self.chat_history.append(
            AIMessage(
                content=answer
            )
        )

        sources = self._extract_sources(
            relevant_docs
        )

        return answer, sources

    # ─────────────────────────────────────────

    def reset_memory(self):

        self.chat_history = []

        print(
            "🔄 Memory cleared"
        )


# ─────────────────────────────────────────────
# TERMINAL TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":

    bot = OctoBot()

    print("\n🐙 OctoBot Ready\n")

    while True:

        q = input("You: ").strip()

        if q.lower() in [
            "quit",
            "exit"
        ]:
            break

        if q.lower() == "reset":
            bot.reset_memory()
            continue

        answer, sources = bot.ask(q)

        print("\n🐙", answer)

        if sources:

            print("\n📚 Sources:")

            for s in sources:

                print(
                    f"- {s['title']}"
                )

                print(
                    f"  {s['url']}"
                )

        print()