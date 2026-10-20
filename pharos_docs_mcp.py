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
    normalized_query = re.sub(r"([a-z])([A-Z])", r"\1 \2", query).replace("_", " ").lower()
    terms = {term for term in re.findall(r"[a-z0-9-]{2,}", normalized_query) if term not in {
        "what", "does", "the", "how", "with", "from", "about", "please", "use",
        "on", "and", "for", "of", "to", "in", "a", "an", "my", "me", "do",
        "eth", "get", "id",
    }}
    hits: list[tuple[int, int, dict[str, str]]] = []
    best_by_source: dict[str, tuple[int, int, dict[str, str]]] = {}
    if not DOCS.exists() or not terms:
        return []
    for path in DOCS.glob("*.txt"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        source = next((line.partition(": ")[2].strip() for line in lines[:8] if line.startswith("SOURCE_URL:")), "")
        # This MCP is specifically the Developer Docs MCP. Ignore scraped
        # third-party pages (which often repeat words such as "testnet" and
        # previously outranked the actual Pharos documentation).
        if not source.startswith("https://docs.pharos.xyz/"):
            continue
        title = next((line.partition(": ")[2].strip() for line in lines[:8] if line.startswith("TITLE:")), path.stem)
        # Split camelCase JSON-RPC names (eth_getBalance) so method docs can
        # be found with normal user language (balance).
        searchable = re.sub(r"([a-z])([A-Z])", r"\1 \2", text).replace("_", " ")
        low = searchable.lower()
        matches = {term for term in terms if term in low}
        relevant_terms = terms - {"atlantic", "pacific", "testnet", "mainnet", "pharos", "network"}
        coverage = len(matches & relevant_terms)
        # A supported plan needs at least two topic terms in the source; broad
        # keyword overlap alone is not enough to claim the docs cover it.
        if coverage >= min(2, len(relevant_terms)):
            score = sum(min(low.count(term), 12) for term in matches) + coverage * 5
            # Return a bounded excerpt around the densest matching region.
            best = max(range(len(lines)), key=lambda i: sum(sum(term in lines[j].lower() for term in matches) for j in range(max(0, i-2), min(len(lines), i+3))))
            excerpt = "\n".join(lines[max(0, best-2):min(len(lines), best+5)])[:MAX_CHARS]
            item = {"title": title, "url": source, "excerpt": excerpt}
            candidate = (coverage, score, item)
            current = best_by_source.get(source)
            if current is None or candidate[:2] > current[:2]:
                best_by_source[source] = candidate
    hits = list(best_by_source.values())
    hits.sort(key=lambda pair: (pair[0], pair[1]), reverse=True)
    return [item for _, _, item in hits[:max(1, min(int(limit), 10))]]


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
