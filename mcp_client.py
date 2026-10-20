"""Small MCP clients for OctoBot's remote Pharos and local docs tools.

The remote client implements the Streamable HTTP JSON-RPC subset used by MCP.
The docs adapter is a stdio MCP server in this repository, so it works without
an additional hosted docs service or credentials.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any

import requests

PHAROS_NETWORK_MCP_URL = os.getenv("PHAROS_NETWORK_MCP_URL", "https://mcp.pharos.xyz/mcp")
MCP_TIMEOUT = float(os.getenv("MCP_TIMEOUT_SECONDS", "12"))


def _decode_mcp_response(response: requests.Response) -> dict[str, Any]:
    content_type = response.headers.get("content-type", "")
    if "json" in content_type:
        data = response.json()
        if isinstance(data, dict):
            return data
    # Streamable HTTP servers may answer with a single-event SSE stream.
    for line in response.text.splitlines():
        if line.startswith("data:"):
            try:
                data = json.loads(line[5:].strip())
                if isinstance(data, dict):
                    return data
            except (ValueError, TypeError):
                continue
    raise RuntimeError("MCP server returned an unreadable response")


class RemoteMCPClient:
    def __init__(self, url: str, headers: dict[str, str] | None = None):
        self.url = url
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": "2025-03-26",
        }
        if headers:
            self.headers.update(headers)
        self.session = requests.Session()
        self.session_id: str | None = None
        self.next_id = 1

    def _post(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        req_id = self.next_id
        self.next_id += 1
        body = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            body["params"] = params
        headers = dict(self.headers)
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        response = self.session.post(self.url, json=body, headers=headers, timeout=MCP_TIMEOUT)
        response.raise_for_status()
        self.session_id = response.headers.get("MCP-Session-Id", self.session_id)
        payload = _decode_mcp_response(response)
        if payload.get("error"):
            raise RuntimeError(str(payload["error"].get("message", "MCP request failed")))
        return payload.get("result", {})

    def initialize(self) -> None:
        self._post("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "OctoBot", "version": "1.0"},
        })
        req_id = self.next_id
        self.next_id += 1
        body = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        headers = dict(self.headers)
        if self.session_id:
            headers["MCP-Session-Id"] = self.session_id
        response = self.session.post(self.url, json=body, headers=headers, timeout=MCP_TIMEOUT)
        if response.status_code not in (200, 202, 204):
            response.raise_for_status()

    def list_tools(self) -> list[dict[str, Any]]:
        return self._post("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._post("tools/call", {"name": name, "arguments": arguments})


def call_remote_pharos_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call a read-only tool on the official Pharos network MCP endpoint."""
    client = RemoteMCPClient(PHAROS_NETWORK_MCP_URL)
    client.initialize()
    available = client.list_tools()
    if name not in {tool.get("name") for tool in available}:
        raise RuntimeError(f"Pharos MCP tool is unavailable: {name}")
    return client.call_tool(name, arguments)


def call_local_docs_tool(name: str, arguments: dict[str, Any], project_dir: str | None = None) -> dict[str, Any]:
    """Run the bundled Pharos docs MCP server over its standard stdio transport."""
    root = project_dir or os.path.dirname(os.path.abspath(__file__))
    child_env = os.environ.copy()
    # Keep the stdio JSON-RPC stream UTF-8 on Windows as well as Linux; the
    # docs excerpts can contain typographic punctuation outside the console
    # code page used by a local Windows Python process.
    child_env["PYTHONIOENCODING"] = "utf-8"
    proc = subprocess.Popen(
        [sys.executable, os.path.join(root, "pharos_docs_mcp.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", cwd=root, env=child_env,
    )
    try:
        def send(msg: dict[str, Any], expect: bool = True) -> dict[str, Any] | None:
            proc.stdin.write(json.dumps(msg, separators=(",", ":")) + "\n")
            proc.stdin.flush()
            if not expect:
                return None
            while True:
                line = proc.stdout.readline()
                if not line:
                    raise RuntimeError("Pharos docs MCP stopped unexpectedly")
                obj = json.loads(line)
                if obj.get("id") == msg.get("id"):
                    if obj.get("error"):
                        raise RuntimeError(obj["error"].get("message", "Docs MCP request failed"))
                    return obj.get("result", {})

        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "OctoBot", "version": "1.0"},
        }})
        send({"jsonrpc": "2.0", "method": "notifications/initialized"}, expect=False)
        tools = send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).get("tools", [])
        if name not in {tool.get("name") for tool in tools}:
            raise RuntimeError(f"Pharos docs MCP tool is unavailable: {name}")
        return send({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": name, "arguments": arguments,
        }})
    finally:
        if proc.stdin:
            proc.stdin.close()
        proc.terminate()
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()


def mcp_text(result: dict[str, Any]) -> str:
    """Flatten text blocks returned by MCP tools for the chat context."""
    content = result.get("content", []) if isinstance(result, dict) else []
    return "\n".join(str(item.get("text", "")) for item in content if item.get("type") == "text").strip()


def network_tool_for_question(question: str) -> tuple[str, dict[str, Any]] | None:
    """Conservatively route explicit read-only chain-data questions to Pharos MCP."""
    text = question.lower()
    # The hosted Pharos MCP documents and serves Pacific mainnet (chain 1672).
    # Never silently present its values as Atlantic testnet data.
    if "testnet" in text or "atlantic" in text:
        return None
    address = re.search(r"0x[a-fA-F0-9]{40}", question)
    tx_hash = re.search(r"0x[a-fA-F0-9]{64}", question)
    if tx_hash and any(word in text for word in ("transaction", "tx ", "receipt", "status", "hash")):
        return "get_transaction_receipt", {"hash": tx_hash.group(0)}
    if tx_hash:
        return "get_transaction", {"hash": tx_hash.group(0)}
    if address and any(word in text for word in ("balance", "holdings", "funds")):
        return "get_balance", {"address": address.group(0)}
    if address and "nonce" in text:
        return "get_transaction_count", {"address": address.group(0)}
    if any(word in text for word in ("gas price", "gas fee", "current gas")):
        return "get_gas_price", {}
    if any(word in text for word in ("latest block", "block number", "block height")):
        return "get_block_number", {}
    if any(word in text for word in ("chain info", "network info", "chain id", "client version")):
        return "get_chain_info", {}
    return None
