"""Local read-only MCP server for searching OctoBot's crawled Pharos docs."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "raw_docs"
MAX_CHARS = 6000


def search_docs(query: str, limit: int = 5) -> list[dict[str, str]]:
    terms = {term for term in re.findall(r"[a-z0-9_-]{2,}", query.lower()) if term not in {"what", "does", "the", "how", "with", "from", "about", "please"}}
    hits: list[tuple[int, dict[str, str]]] = []
    if not DOCS.exists() or not terms:
        return []
    for path in DOCS.glob("*.txt"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = text.lower()
        score = sum(low.count(term) for term in terms)
        if score:
            # Return a bounded excerpt around the densest matching region.
            lines = text.splitlines()
            best = max(range(len(lines)), key=lambda i: sum(sum(term in lines[j].lower() for term in terms) for j in range(max(0, i-2), min(len(lines), i+3))))
            excerpt = "\n".join(lines[max(0, best-2):min(len(lines), best+5)])[:MAX_CHARS]
            source = next((line.partition(": ")[2].strip() for line in lines[:8] if line.startswith("SOURCE_URL:")), "")
            title = next((line.partition(": ")[2].strip() for line in lines[:8] if line.startswith("TITLE:")), path.stem)
            hits.append((score, {"title": title, "url": source, "excerpt": excerpt}))
    hits.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in hits[:max(1, min(int(limit), 10))]]


def respond(message: dict) -> dict | None:
    method = message.get("method")
    req_id = message.get("id")
    if method == "notifications/initialized":
        return None
    if method == "initialize":
        result = {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "pharos-docs", "version": "1.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [{"name": "search_pharos_docs", "description": "Search the bundled, crawled Pharos documentation and return cited excerpts.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 10}}, "required": ["query"]}}]}
    elif method == "tools/call":
        params = message.get("params", {})
        if params.get("name") != "search_pharos_docs":
            return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32602, "message": "Unknown docs tool"}}
        args = params.get("arguments", {})
        hits = search_docs(str(args.get("query", "")), int(args.get("limit", 5)))
        result = {"content": [{"type": "text", "text": json.dumps(hits, ensure_ascii=False)}], "isError": not bool(hits)}
    else:
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


def main() -> None:
    # MCP stdio transport: stdout is reserved for newline-delimited JSON-RPC.
    for line in sys.stdin:
        try:
            response = respond(json.loads(line))
            if response is not None:
                sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}}) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
