"""
octobot.py
----------
Phase 5: OctoBot — the core RAG chatbot engine.

This module defines:
  - The system prompt (OctoBot's personality and rules)
  - The retrieval pipeline (fetches relevant chunks)
  - The answer generation chain (GPT reads chunks and answers)

This file is imported by the Streamlit app (app.py).
You can also test it directly:

How to run:
    python octobot.py

Expected output:
    🐙 OctoBot is ready!
    You: What is Pharos?
    OctoBot: Pharos is a Modular & Full-stack Parallel L1 Blockchain...
    Sources used:
      - https://docs.pharos.xyz/ (About Pharos)
"""

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise ValueError(
        "GEMINI_API_KEY not found in .env file"
    )

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
CHROMA_DB_DIR = "chroma_db"
COLLECTION_NAME = "pharos_docs"
TOP_K = 5          # Number of chunks to retrieve per question
GEMINI_MODEL = "gemini-2.5-flash"  # Fast, cheap, and very capable


# ─────────────────────────────────────────────
# OCTOBOT'S SYSTEM PROMPT
#
# This is OctoBot's "personality" and rules.
# The {context} placeholder is filled with retrieved chunks.
# The {chat_history} placeholder holds the conversation so far.
# The {question} placeholder is the user's current question.
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """You are OctoBot, a helpful and accurate documentation assistant \
for the Pharos blockchain network.

Your job is to answer questions ONLY using the documentation excerpts provided \
below in the <context> section.

RULES YOU MUST FOLLOW:
1. ONLY answer based on what is in the provided context.
2. If the answer is not in the context, respond EXACTLY with:
   "I could not find that information in the Pharos documentation."
3. Do NOT guess, invent, or hallucinate any information.
4. Keep your answers clear, concise, and accurate.
5. When possible, structure your answer with bullet points for clarity.
6. Always be professional and helpful.

<context>
{context}
</context>

Remember: You are OctoBot. Only answer from the documentation above.
"""

PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])


# ─────────────────────────────────────────────
# OCTOBOT CLASS
# ─────────────────────────────────────────────
class OctoBot:
    """
    The main OctoBot RAG chatbot.

    Usage:
        bot = OctoBot()
        answer, sources = bot.ask("What is Pharos?")
        print(answer)
        for src in sources:
            print(src["url"], src["title"])
    """

    def __init__(self):
        """Initialize the vector store, embeddings, and LLM."""
        print("🐙 Initializing OctoBot...")

        # Check the vector store exists
        if not os.path.exists(CHROMA_DB_DIR):
            raise FileNotFoundError(
                f"Vector store not found at '{CHROMA_DB_DIR}'. "
                "Please run build_vectorstore.py first."
            )

        # Load embeddings (same model used when building the store)
        self.embeddings = HuggingFaceEmbeddings(
                 model_name="sentence-transformers/all-MiniLM-L6-v2"
             ) 

        # Load the ChromaDB vector store
        self.vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=self.embeddings,
            persist_directory=CHROMA_DB_DIR,
        )

        # Create a retriever — this is what searches ChromaDB
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={"k": TOP_K}
        )

        # Create the LLM
        self.llm = ChatGoogleGenerativeAI(
           model=GEMINI_MODEL,
           temperature=0,
           google_api_key=os.getenv("GEMINI_API_KEY")
        )
        # Conversation memory — stores the back-and-forth
        self.chat_history: list = []

        count = self.vectorstore._collection.count()
        print(f"✅ OctoBot ready! ({count} chunks in knowledge base)")

    def _format_docs(self, docs) -> str:
        """Format retrieved documents into a single string for the prompt."""
        parts = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            title = doc.metadata.get("title", "")
            parts.append(
                f"[Excerpt {i} from: {title} ({source})]\n{doc.page_content}"
            )
        return "\n\n---\n\n".join(parts)

    def _extract_sources(self, docs) -> list[dict]:
        """Extract source metadata from retrieved docs (for citation display)."""
        seen = set()
        sources = []
        for doc in docs:
            url = doc.metadata.get("source", "")
            title = doc.metadata.get("title", "")
            if url and url not in seen:
                seen.add(url)
                sources.append({"url": url, "title": title})
        return sources

    def ask(self, question: str) -> tuple[str, list[dict]]:
        """
        Ask OctoBot a question.

        Returns:
            (answer_text, sources_list)
            sources_list is a list of {"url": ..., "title": ...} dicts
        """
        # Step 1: Retrieve relevant chunks from ChromaDB
        relevant_docs = self.retriever.invoke(question)

        if not relevant_docs:
            return (
                "I could not find that information in the Pharos documentation.",
                []
            )

        # Step 2: Format the retrieved docs into context text
        context = self._format_docs(relevant_docs)

        # Step 3: Build the prompt and get GPT's answer
        chain = PROMPT_TEMPLATE | self.llm | StrOutputParser()

        answer = chain.invoke({
            "context": context,
            "chat_history": self.chat_history,
            "question": question,
        })

        # Step 4: Save this turn to memory
        self.chat_history.append(HumanMessage(content=question))
        self.chat_history.append(AIMessage(content=answer))

        # Step 5: Extract sources for citation
        sources = self._extract_sources(relevant_docs)

        return answer, sources

    def reset_memory(self):
        """Clear conversation history (start a new session)."""
        self.chat_history = []
        print("🔄 Conversation memory cleared.")


# ─────────────────────────────────────────────
# COMMAND-LINE TEST
# ─────────────────────────────────────────────
if __name__ == "__main__":
    bot = OctoBot()
    print("\n" + "=" * 60)
    print("🐙 OctoBot — Pharos Documentation Assistant")
    print("   Type 'quit' to exit | Type 'reset' to clear memory")
    print("=" * 60 + "\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye!")
            break
        if user_input.lower() == "reset":
            bot.reset_memory()
            continue

        answer, sources = bot.ask(user_input)

        print(f"\n🐙 OctoBot: {answer}\n")

        if sources:
            print("📚 Sources:")
            for src in sources:
                print(f"   • {src['title']}")
                print(f"     {src['url']}")
        print()