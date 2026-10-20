"""Read-only, block-pinned portfolio reads for Pharos Pacific mainnet.

The module intentionally supports only standard EVM account balances and
ERC-4626 vault views. Protocol-specific yield metrics require an explicit,
reviewed adapter; they are never inferred from share prices or marketing APY.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

import requests


ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")
_SELECTORS = {
    "asset": "0x38d52e0f",
    "balance_of": "0x70a08231",
    "convert_to_assets": "0x07a2d13a",
    "decimals": "0x313ce567",
    "symbol": "0x95d89b41",
}


class PortfolioReadError(RuntimeError):
    """Raised when a required, wallet-wide snapshot read cannot be trusted."""


def is_address(value: str) -> bool:
    return bool(ADDRESS_RE.fullmatch(str(value or "").strip()))


def _word_address(address: str) -> str:
    return address.lower().removeprefix("0x").rjust(64, "0")


def _decode_uint(value: str) -> int:
    if not isinstance(value, str) or not value.startswith("0x") or len(value) < 66:
        raise ValueError("Contract returned an invalid uint256 value")
    return int(value[2:66], 16)


def _decode_address(value: str) -> str:
    if not isinstance(value, str) or len(value) < 66:
        raise ValueError("Contract returned an invalid address")
    address = "0x" + value[-40:]
    if not is_address(address):
        raise ValueError("Contract returned an invalid address")
    return address


def _decode_string(value: str) -> str | None:
    """Decode common ABI string and bytes32 symbol encodings."""
    if not isinstance(value, str) or not value.startswith("0x"):
        return None
    raw = bytes.fromhex(value[2:])
    try:
        if len(raw) == 32:  # Older ERC-20s return bytes32.
            return raw.rstrip(b"\0").decode("utf-8").strip() or None
        if len(raw) < 64:
            return None
        offset = int.from_bytes(raw[:32], "big")
        if offset + 32 > len(raw):
            return None
        length = int.from_bytes(raw[offset:offset + 32], "big")
        start = offset + 32
        if length > len(raw) - start:
            return None
        return raw[start:start + length].decode("utf-8").strip() or None
    except (UnicodeDecodeError, ValueError):
        return None


class _Rpc:
    def __init__(self, url: str, timeout: float = 8.0):
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self._request_id = 0

    def call(self, method: str, params: list[Any]) -> Any:
        self._request_id += 1
        response = self.session.post(
            self.url,
            json={"jsonrpc": "2.0", "id": self._request_id, "method": method, "params": params},
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            message = payload["error"].get("message", "RPC request failed")
            raise PortfolioReadError(str(message)[:240])
        if "result" not in payload:
            raise PortfolioReadError("RPC response did not contain a result")
        return payload["result"]

    def eth_call(self, target: str, data: str, block_tag: str) -> str:
        result = self.call("eth_call", [{"to": target, "data": data}, block_tag])
        if not isinstance(result, str) or not result.startswith("0x"):
            raise PortfolioReadError("Contract call returned no data")
        return result


def _token_metadata(rpc: _Rpc, address: str, block_tag: str,
                    known: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if address.lower() in known:
        return known[address.lower()]
    symbol = None
    decimals = None
    try:
        symbol = _decode_string(rpc.eth_call(address, _SELECTORS["symbol"], block_tag))
    except Exception:
        pass
    try:
        decimals = _decode_uint(rpc.eth_call(address, _SELECTORS["decimals"], block_tag))
    except Exception:
        pass
    if decimals is None or decimals > 36:
        raise PortfolioReadError("Underlying token does not expose valid ERC-20 decimals")
    return {"symbol": symbol or "Unknown token", "decimals": decimals, "address": address}


def read_wallet_snapshot(
    wallet: str,
    tokens: Iterable[tuple[str, str, int, str]],
    vaults: Iterable[dict[str, str]],
    rpc_url: str,
    explorer_url: str,
) -> dict[str, Any]:
    """Read balances and configured ERC-4626 shares against one exact block.

    A vault row is retained with an explicit error if that contract is not a
    readable ERC-4626 vault. Other rows remain usable. No transaction method
    is exposed by this module.
    """
    wallet = str(wallet or "").strip()
    if not is_address(wallet):
        raise PortfolioReadError("Enter a valid EVM wallet address")
    rpc = _Rpc(rpc_url)
    try:
        block_hex = rpc.call("eth_blockNumber", [])
        block_number = int(block_hex, 16)
    except Exception as exc:
        raise PortfolioReadError("Could not determine the snapshot block: " + str(exc)[:200]) from exc
    block_tag = hex(block_number)
    source_base = {"network": "Pharos Pacific Mainnet", "chain_id": 1672,
                   "block_number": block_number, "block_tag": block_tag,
                   "rpc_url": rpc_url, "explorer_url": explorer_url}

    known: dict[str, dict[str, Any]] = {}
    for symbol, address, decimals, label in tokens:
        if is_address(address) and 0 <= int(decimals) <= 36:
            known[address.lower()] = {"symbol": str(symbol), "decimals": int(decimals),
                                      "address": address, "label": str(label)}

    try:
        native_hex = rpc.call("eth_getBalance", [wallet, block_tag])
        native_balance = int(native_hex, 16) / 10**18
    except Exception as exc:
        raise PortfolioReadError("Could not read the native balance at the snapshot block: " + str(exc)[:200]) from exc

    balances = [{
        "kind": "wallet balance", "symbol": "PROS", "label": "Native PROS",
        "amount": native_balance, "token_address": None,
        "source_contract": "Native account balance", **source_base,
    }]
    for symbol, address, decimals, label in tokens:
        if not is_address(address):
            continue
        try:
            result = rpc.eth_call(address, _SELECTORS["balance_of"] + _word_address(wallet), block_tag)
            amount = _decode_uint(result) / 10**int(decimals)
            balances.append({
                "kind": "wallet balance", "symbol": str(symbol), "label": str(label),
                "amount": amount, "token_address": address,
                "source_contract": address, **source_base,
            })
        except Exception as exc:
            balances.append({
                "kind": "unavailable token balance", "symbol": str(symbol),
                "label": str(label), "amount": None, "token_address": address,
                "source_contract": address, "error": str(exc)[:200], **source_base,
            })

    positions = []
    seen_vaults: set[str] = set()
    for config in vaults:
        vault_address = str(config.get("address", "")).strip()
        protocol = str(config.get("protocol", "Configured vault")).strip() or "Configured vault"
        if not is_address(vault_address) or vault_address.lower() in seen_vaults:
            continue
        seen_vaults.add(vault_address.lower())
        position: dict[str, Any] = {
            "kind": "vault position", "protocol": protocol,
            "vault_address": vault_address, "source_contract": vault_address,
            "yield_status": "Not exposed by the standard ERC-4626 interface",
            **source_base,
        }
        try:
            asset_address = _decode_address(rpc.eth_call(vault_address, _SELECTORS["asset"], block_tag))
            if asset_address.lower() == "0x" + "0" * 40:
                raise PortfolioReadError("Native-asset vaults are not supported by the ERC-4626 reader")
            share_decimals = _decode_uint(rpc.eth_call(vault_address, _SELECTORS["decimals"], block_tag))
            if share_decimals > 36:
                raise PortfolioReadError("Vault returned invalid share decimals")
            share_raw = _decode_uint(rpc.eth_call(
                vault_address, _SELECTORS["balance_of"] + _word_address(wallet), block_tag,
            ))
            assets_raw = _decode_uint(rpc.eth_call(
                vault_address,
                _SELECTORS["convert_to_assets"] + format(share_raw, "064x"), block_tag,
            ))
            asset = _token_metadata(rpc, asset_address, block_tag, known)
            position.update({
                "available": True,
                "asset_address": asset_address,
                "asset_symbol": asset["symbol"],
                "asset_decimals": asset["decimals"],
                "shares": share_raw / 10**share_decimals,
                "share_decimals": share_decimals,
                "assets": assets_raw / 10**asset["decimals"],
            })
        except Exception as exc:
            position.update({"available": False, "error": str(exc)[:240]})
        positions.append(position)

    return {
        "wallet": wallet, "network": source_base["network"],
        "chain_id": 1672, "block_number": block_number,
        "block_tag": block_tag, "balances": balances,
        "positions": positions, "read_only": True,
    }


def answer_portfolio_question(question: str, snapshot: dict[str, Any]) -> str:
    """Answer common portfolio questions from snapshot data only."""
    q = str(question or "").strip().lower()
    balances = snapshot.get("balances", [])
    positions = [p for p in snapshot.get("positions", []) if p.get("available")]
    known_symbols = sorted({str(row.get("symbol", "")).lower() for row in balances}
                           | {str(row.get("asset_symbol", "")).lower() for row in positions},
                           key=len, reverse=True)

    def refs(rows: list[dict[str, Any]]) -> str:
        return "\n".join(
            f"- Source: {row.get('source_contract')} · block {row.get('block_number')}"
            for row in rows
        )

    requested = next((symbol for symbol in known_symbols if symbol and re.search(
        rf"(?<![a-z0-9]){re.escape(symbol)}(?![a-z0-9])", q)), None)
    if any(term in q for term in ("earning", "yield", "apy", "apr", "rewards", "interest")):
        if not positions:
            return ("I can’t determine earnings because no configured ERC-4626 vault position was readable. "
                    "No yield figure is available from this snapshot.")
        return ("I can read your configured vault share positions, but ERC-4626 does not standardize "
                "current APY or accrued rewards. This snapshot has no reviewed protocol-specific yield "
                "adapter, so I can’t verify what you’re earning and won’t estimate it.\n\n" + refs(positions))

    if any(term in q for term in ("where", "held", "holding", "holdings", "located", "which protocol")) and requested:
        token_rows = [row for row in balances if row.get("symbol", "").lower() == requested]
        vault_rows = [row for row in positions if row.get("asset_symbol", "").lower() == requested]
        failed_rows = [row for row in token_rows if row.get("amount") is None]
        if failed_rows and not any(row.get("amount") is not None for row in token_rows) and not vault_rows:
            return (f"I couldn’t read the {requested.upper()} balance from its token contract at block "
                    f"{failed_rows[0]['block_number']}. The value is unavailable, not zero.\n" + refs(failed_rows))
        if not token_rows and not vault_rows:
            return f"No readable {requested.upper()} balance or configured vault position was found in this snapshot."
        lines = [f"{requested.upper()} locations in this snapshot:"]
        lines.extend(f"- Wallet: {row['amount']:.8g} {row['symbol']}" for row in token_rows
                     if row.get("amount") is not None)
        lines.extend(f"- {row['protocol']} vault: {row['assets']:.8g} {row['asset_symbol']} "
                     f"({row['shares']:.8g} shares)" for row in vault_rows)
        lines.append(refs([row for row in token_rows if row.get("amount") is not None] + vault_rows))
        return "\n".join(lines)

    if any(term in q for term in ("position", "vault", "deposited", "invested")):
        if not positions:
            return ("No configured ERC-4626 vault positions were readable. Add vault contract addresses "
                    "on this page; unsupported contracts are reported instead of treated as positions.")
        lines = ["Readable configured vault positions:"]
        lines.extend(f"- {p['protocol']}: {p['assets']:.8g} {p['asset_symbol']} "
                f"backed by {p['shares']:.8g} shares" for p in positions)
        lines.append(refs(positions))
        return "\n".join(lines)

    if any(term in q for term in ("balance", "balances", "holdings", "portfolio")):
        rows = [row for row in balances if row.get("amount") is not None]
        if not rows:
            return "No wallet token balances were readable in this snapshot."
        lines = ["Readable wallet balances:"]
        lines.extend(f"- {row['amount']:.8g} {row['symbol']}" for row in rows)
        lines.append(refs(rows))
        failed = [row for row in balances if row.get("amount") is None]
        if failed:
            lines.append("Unavailable token reads (not treated as zero): " + ", ".join(row["symbol"] for row in failed))
        return "\n".join(lines)

    if any(term in q for term in ("biggest", "largest", "most")):
        rows = ([row for row in balances if row.get("amount") is not None and row["amount"] > 0]
                + [{"symbol": p["asset_symbol"], "amount": p["assets"],
                   "source_contract": p["source_contract"], "block_number": p["block_number"],
                   "protocol": p["protocol"]} for p in positions])
        symbols = {row["symbol"] for row in rows}
        if len(symbols) != 1:
            return ("I can’t rank positions across different assets without verified prices at the same "
                    "valuation time. This snapshot has no complete, sourced price set, so I won’t call "
                    "one position the largest.")
        if not rows:
            return "There are no readable balances or vault positions to rank."
        top = max(rows, key=lambda row: row["amount"])
        label = top.get("protocol", "wallet")
        return (f"Largest position by {top['symbol']} units: {top['amount']:.8g} {top['symbol']} "
                f"at {label}.\n- Source: {top['source_contract']} · block {top['block_number']}")

    if requested:
        rows = [row for row in balances if row.get("symbol", "").lower() == requested]
        if not rows:
            return f"No readable {requested.upper()} wallet balance was found in this snapshot."
        row = rows[0]
        if row.get("amount") is None:
            return f"The {requested.upper()} balance read failed: {row.get('error', 'RPC unavailable')}"
        return (f"Wallet balance: {row['amount']:.8g} {row['symbol']} ({row['label']}).\n"
                f"- Source: {row['source_contract']} · block {row['block_number']}")

    return ("I can answer wallet token balances, where a tracked token is held, configured ERC-4626 "
            "positions, largest positions when comparable in the same asset, and whether yield data "
            "is available. This request doesn’t match one of those supported reads; I haven’t guessed.")
