"""
skill_api.py
------------
Wraps OctoBot as a callable Skill API for the Pharos AI Agent Carnival.

Any Agent on Pharos can call POST /query with a question
and get a structured answer back with sources.

HOW TO INSTALL:
    pip install fastapi uvicorn

HOW TO RUN LOCALLY:
    uvicorn skill_api:app --host 0.0.0.0 --port 8000

HOW TO TEST IN BROWSER:
    http://localhost:8000          -> health check
    http://localhost:8000/docs     -> interactive Swagger UI (auto-generated)

HOW AN AGENT CALLS THIS SKILL:
    POST http://localhost:8000/query
    Body: { "question": "What are SPNs?" }

    Response:
    {
      "answer": "SPNs are Special Processing Networks...",
      "sources": [{"url": "...", "title": "..."}],
      "found_in_docs": true
    }

BEFORE RUNNING:
    Make sure you have run build_vectorstore.py first so
    the chroma_db folder exists.
"""

import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

# ─────────────────────────────────────────────
# VERIFY ENV BEFORE STARTING
# ─────────────────────────────────────────────
if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError(
        "GEMINI_API_KEY not found. "
        "Make sure your .env file exists and contains GEMINI_API_KEY=sk-..."
    )

if not os.path.exists("chroma_db"):
    raise RuntimeError(
        "chroma_db folder not found. "
        "Please run: python build_vectorstore.py"
    )

# ─────────────────────────────────────────────
# LOAD OCTOBOT
# ─────────────────────────────────────────────
from octobot import OctoBot

print("Loading OctoBot knowledge base...")
bot = OctoBot()
print("OctoBot ready — Skill API starting up.")

# ─────────────────────────────────────────────
# FASTAPI APP
# ─────────────────────────────────────────────
app = FastAPI(
    title="Pharos Knowledge Skill",
    description=(
        "A reusable AI Skill for the Pharos AI Agent Carnival. "
        "Answers any question about the Pharos Network using verified "
        "documentation. Zero hallucination — only answers from real sources."
    ),
    version="1.0.0",
)

# Allow any Agent or frontend to call this Skill
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# REQUEST / RESPONSE MODELS
# ─────────────────────────────────────────────
class SkillRequest(BaseModel):
    question: str

    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are Special Processing Networks (SPNs)?"
            }
        }


class SourceItem(BaseModel):
    url: str
    title: str


class SkillResponse(BaseModel):
    answer: str
    sources: list[SourceItem]
    found_in_docs: bool

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "SPNs (Special Processing Networks) are...",
                "sources": [
                    {
                        "url": "https://docs.pharos.xyz/spns",
                        "title": "Special Processing Networks"
                    }
                ],
                "found_in_docs": True
            }
        }


# ─────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
def health_check():
    """Health check — confirms the Skill is online."""
    chunk_count = bot.vectorstore._collection.count()
    return {
        "skill": "pharos-knowledge",
        "status": "online",
        "knowledge_chunks": chunk_count,
        "model": "gpt-4o-mini",
    }


@app.post("/query", response_model=SkillResponse, tags=["Skill"])
def query_pharos_docs(request: SkillRequest):
    """
    The main Skill endpoint.

    Any Agent calls this with a question about Pharos Network.
    Returns the answer, the source documents used, and whether
    the answer was found in the documentation.

    If the information is not in the docs, found_in_docs will
    be False and the answer will say so explicitly.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail="question field cannot be empty."
        )

    try:
        answer, raw_sources = bot.ask(request.question.strip())
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="OctoBot encountered an error: " + str(e)
        )

    not_found = "I could not find that information" in answer

    sources = [
        SourceItem(url=s.get("url", ""), title=s.get("title", ""))
        for s in raw_sources
    ]

    return SkillResponse(
        answer=answer,
        sources=sources,
        found_in_docs=not not_found,
    )


@app.get("/info", tags=["Skill"])
def skill_info():
    """Returns metadata about this Skill for Agent discovery."""
    return {
        "skill_name": "pharos-knowledge",
        "version": "1.0.0",
        "description": (
            "Answers any question about the Pharos Network using verified "
            "documentation. Returns structured answers with source citations."
        ),
        "category": "data-fetch",
        "input": {
            "question": "string — any question about Pharos Network"
        },
        "output": {
            "answer": "string — the answer from documentation",
            "sources": "array of {url, title} objects",
            "found_in_docs": "boolean — True if answer was found"
        },
        "tags": ["pharos", "documentation", "RAG", "knowledge-base", "AI"],
    }