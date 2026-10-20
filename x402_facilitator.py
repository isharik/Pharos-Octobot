"""Atlantic testnet x402 demo facilitator and protected resource server.

This Pharos-native transfer profile accepts user-signed native PHRS transfers.
The wallet broadcasts the transfer; this service verifies the mined receipt and
records settlement. It never receives or stores a user's private key.
"""
from __future__ import annotations

import base64
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

CHAIN_ID = 688689
NETWORK = "eip155:688689"
RPC_URL = os.getenv("PHAROS_TESTNET_RPC_URL", "https://atlantic.dplabs-internal.com")
EXPLORER_URL = os.getenv("PHAROS_TESTNET_EXPLORER_URL", "https://atlantic.pharosscan.xyz")
PAYTO = os.getenv("X402_PAYTO_ADDRESS", "").strip()
FREE_ROUTE = "/health"
ROUTE_PRICES = {"/data": 0.005, "/premium": 0.01}
DB_PATH = Path(os.getenv("X402_FACILITATOR_DB") or str(Path.home() / ".local" / "share" / "OctoBot" / "x402_facilitator.sqlite3"))
WEI = 10**18
SCHEME = "pharos-native-transfer"

app = FastAPI(title="OctoBot Pharos Atlantic x402 Facilitator", version="1.0.0")


def _db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("CREATE TABLE IF NOT EXISTS settlements (tx_hash TEXT PRIMARY KEY, payer TEXT NOT NULL, pay_to TEXT NOT NULL, amount_wei TEXT NOT NULL, amount_phrs TEXT NOT NULL, resource TEXT NOT NULL, chain_id INTEGER NOT NULL, block_number INTEGER NOT NULL, settled_at INTEGER NOT NULL)")
    return con


def _rpc(method: str, params: list[Any]) -> Any:
    response = requests.post(RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=12)
    response.raise_for_status()
    payload = response.json()
    if payload.get("error"):
        raise RuntimeError(payload["error"].get("message", "Pharos RPC error"))
    return payload.get("result")


def _challenge(path: str) -> dict[str, Any]:
    return {
        "x402Version": 2,
        "error": "Payment required",
        "resource": path,
        "accepts": [{
            "scheme": SCHEME,
            "network": NETWORK,
            "asset": "native:PHRS",
            "amount": str(int(ROUTE_PRICES[path] * WEI)),
            "amountFormatted": f"{ROUTE_PRICES[path]:.3f} PHRS",
            "payTo": PAYTO,
            "maxTimeoutSeconds": 120,
            "extra": {"chainId": CHAIN_ID, "explorerUrl": EXPLORER_URL},
        }],
    }


def _read_signature(value: str) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        raw = base64.b64decode(value, validate=True)
        data = json.loads(raw.decode("utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        try:
            data = json.loads(value)
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    return None


def verify_payment(payment: dict[str, Any], resource: str) -> dict[str, Any]:
    if not PAYTO or not (len(PAYTO) == 42 and PAYTO.startswith("0x")):
        return {"isValid": False, "invalidReason": "X402_PAYTO_ADDRESS is not configured"}
    if resource not in ROUTE_PRICES:
        return {"isValid": False, "invalidReason": "Unsupported paid route"}
    if payment.get("x402Version") not in (1, 2):
        return {"isValid": False, "invalidReason": "Unsupported x402 version"}
    if payment.get("scheme") != SCHEME or payment.get("network") != NETWORK:
        return {"isValid": False, "invalidReason": "Payment scheme or network does not match Atlantic testnet"}
    payload = payment.get("payload") or {}
    tx_hash = str(payload.get("txHash", ""))
    if len(tx_hash) != 66 or not tx_hash.startswith("0x"):
        return {"isValid": False, "invalidReason": "A valid signed transaction hash is required"}
    try:
        int(tx_hash[2:], 16)
        tx = _rpc("eth_getTransactionByHash", [tx_hash])
        receipt = _rpc("eth_getTransactionReceipt", [tx_hash])
        chain_id = int(_rpc("eth_chainId", []), 16)
    except Exception as exc:
        return {"isValid": False, "invalidReason": f"Pharos RPC verification failed: {exc}"}
    if tx is None or receipt is None:
        return {"isValid": False, "invalidReason": "Transaction is not mined yet"}
    if chain_id != CHAIN_ID:
        return {"isValid": False, "invalidReason": "RPC is not connected to Atlantic testnet"}
    if int(receipt.get("status", "0x0"), 16) != 1:
        return {"isValid": False, "invalidReason": "Transaction failed on-chain"}
    if (tx.get("to") or "").lower() != PAYTO.lower():
        return {"isValid": False, "invalidReason": "Transaction recipient does not match the challenge"}
    declared_payer = str(payload.get("payer", ""))
    if declared_payer and declared_payer.lower() != str(tx.get("from", "")).lower():
        return {"isValid": False, "invalidReason": "Payment proof payer does not match the signed transaction"}
    amount_wei = int(tx.get("value", "0x0"), 16)
    required_wei = int(ROUTE_PRICES[resource] * WEI)
    if amount_wei < required_wei:
        return {"isValid": False, "invalidReason": f"Underpaid: required {ROUTE_PRICES[resource]:.3f} PHRS"}
    tx_chain = tx.get("chainId")
    if tx_chain and int(tx_chain, 16) != CHAIN_ID:
        return {"isValid": False, "invalidReason": "Transaction was not signed for Atlantic testnet"}
    details = {
        "txHash": tx_hash,
        "payer": tx.get("from", ""),
        "payTo": PAYTO,
        "amountWei": str(amount_wei),
        "amount": f"{amount_wei / WEI:.6f}",
        "resource": resource,
        "network": NETWORK,
        "chainId": CHAIN_ID,
        "blockNumber": int(receipt.get("blockNumber", "0x0"), 16),
    }
    return {"isValid": True, "details": details}


def settle_payment(payment: dict[str, Any], resource: str) -> dict[str, Any]:
    check = verify_payment(payment, resource)
    if not check.get("isValid"):
        return check
    d = check["details"]
    try:
        with _db() as con:
            existing = con.execute("SELECT * FROM settlements WHERE tx_hash=?", (d["txHash"].lower(),)).fetchone()
            if existing:
                if existing["resource"] != resource:
                    return {"isValid": False, "invalidReason": "This transaction was already used for another resource"}
                saved = dict(existing)
                return {"success": True, "details": {**d, "settledAt": saved["settled_at"]}}
            con.execute("INSERT INTO settlements(tx_hash,payer,pay_to,amount_wei,amount_phrs,resource,chain_id,block_number,settled_at) VALUES(?,?,?,?,?,?,?,?,?)",
                        (d["txHash"].lower(), d["payer"], d["payTo"], d["amountWei"], d["amount"], resource, CHAIN_ID, d["blockNumber"], int(time.time())))
    except sqlite3.IntegrityError:
        return {"isValid": False, "invalidReason": "This transaction has already been settled"}
    d["settledAt"] = int(time.time())
    return {"success": True, "details": d}


def _payment_for_request(request: Request) -> dict[str, Any] | None:
    return _read_signature(request.headers.get("PAYMENT-SIGNATURE", ""))


def _paid_response(request: Request, resource: str):
    payment = _payment_for_request(request)
    if not payment:
        challenge = _challenge(resource)
        encoded = base64.b64encode(json.dumps(challenge, separators=(",", ":")).encode()).decode()
        return JSONResponse(challenge, status_code=402, headers={"PAYMENT-REQUIRED": encoded})
    result = settle_payment(payment, resource)
    if not result.get("success"):
        challenge = _challenge(resource)
        challenge["error"] = result.get("invalidReason", "Payment verification failed")
        encoded = base64.b64encode(json.dumps(challenge, separators=(",", ":")).encode()).decode()
        return JSONResponse(challenge, status_code=402, headers={"PAYMENT-REQUIRED": encoded})
    details = result["details"]
    receipt = {"success": True, "network": NETWORK, "transaction": details["txHash"], "amount": details["amount"], "asset": "PHRS", "payer": details["payer"], "resource": resource, "blockNumber": details["blockNumber"]}
    encoded_receipt = base64.b64encode(json.dumps(receipt, separators=(",", ":")).encode()).decode()
    return JSONResponse({"ok": True, "resource": resource, "message": "Payment settled and resource unlocked", "settlement": receipt}, headers={"PAYMENT-RESPONSE": encoded_receipt})


@app.get("/health")
def health():
    return {"ok": True, "route": FREE_ROUTE, "network": NETWORK, "chainId": CHAIN_ID, "paid": False}


@app.get("/supported")
def supported():
    return {"x402Version": 2, "network": NETWORK, "chainId": CHAIN_ID, "nativeAsset": "PHRS", "payToConfigured": bool(PAYTO), "accepts": [{"scheme": SCHEME, "network": NETWORK, "asset": "native:PHRS"}], "facilitator": {"verify": "/verify", "settle": "/settle", "supported": "/supported", "reports": "/reports"}, "routes": [{"path": path, "method": "GET", "amount": f"{price:.3f}", "asset": "PHRS"} for path, price in ROUTE_PRICES.items()] + [{"path": FREE_ROUTE, "method": "GET", "amount": "0", "asset": "PHRS"}]}


@app.post("/verify")
async def verify_endpoint(request: Request):
    body = await request.json()
    resource = str(body.get("resource", "/premium"))
    payment = body.get("payment") or _read_signature(request.headers.get("PAYMENT-SIGNATURE", "")) or {}
    return verify_payment(payment, resource)


@app.post("/settle")
async def settle_endpoint(request: Request):
    body = await request.json()
    resource = str(body.get("resource", "/premium"))
    payment = body.get("payment") or _read_signature(request.headers.get("PAYMENT-SIGNATURE", "")) or {}
    result = settle_payment(payment, resource)
    if not result.get("success"):
        return JSONResponse(result, status_code=402)
    details = result["details"]
    return {"success": True, **details, "explorerUrl": f"{EXPLORER_URL}/tx/{details['txHash']}"}


@app.get("/data")
def paid_data(request: Request):
    return _paid_response(request, "/data")


@app.get("/premium")
def paid_premium(request: Request):
    return _paid_response(request, "/premium")


@app.get("/reports")
def reports(limit: int = 100):
    with _db() as con:
        rows = con.execute("SELECT * FROM settlements ORDER BY settled_at DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["explorerUrl"] = f"{EXPLORER_URL}/tx/{item['tx_hash']}"
        items.append(item)
    return {"count": len(items), "network": NETWORK, "settlements": items}

