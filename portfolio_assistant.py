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
    """Answer only from the supplied block-pinned snapshot; explain coverage limits."""
    q = str(question or "").strip().lower()
    balances = snapshot.get("balances", [])
    positions_all = snapshot.get("positions", [])
    positions = [row for row in positions_all if row.get("available")]
    failed_balances = [row for row in balances if row.get("amount") is None]
    failed_positions = [row for row in positions_all if not row.get("available")]

    def source_line(row: dict[str, Any]) -> str:
        source = row.get("source_contract") or "Unknown contract"
        block = row.get("block_number", snapshot.get("block_number", "unknown"))
        return f"Source: {source} · block {block}"

    def fmt(amount: Any) -> str:
        return f"{float(amount):,.8g}"

    def token_key(row: dict[str, Any], is_vault: bool = False) -> str:
        address = row.get("asset_address") if is_vault else row.get("token_address")
        if address:
            return str(address).lower()
        return "native:pros"

    known_symbols = sorted(
        {str(row.get("symbol", "")).strip().lower() for row in balances if row.get("symbol")}
        | {str(row.get("asset_symbol", "")).strip().lower() for row in positions if row.get("asset_symbol")},
        key=len, reverse=True,
    )
    requested = next((symbol for symbol in known_symbols if re.search(
        rf"(?<![a-z0-9]){re.escape(symbol)}(?![a-z0-9])", q,
    )), None)

    if any(word in q for word in ("apy", "apr", "yield", "earning", "earnings", "rewards", "interest", "returns", "profit", "income")):
        if not positions:
            message = "I can’t calculate earnings: no configured vault position was readable in this snapshot."
        else:
            message = (
                "I can read the configured vault balances, but this snapshot doesn’t include a verified "
                "APY, accrued-reward, or interest adapter. ERC-4626 share conversion alone does not prove "
                "how much yield you earned, so I won’t estimate it."
            )
        if positions:
            message += "\nReadable vaults checked:\n" + "\n".join(
                f"- {row['protocol']}: {fmt(row['assets'])} {row['asset_symbol']} "
                f"({fmt(row['shares'])} shares); {source_line(row)}"
                for row in positions
            )
        if failed_positions:
            message += f"\n{len(failed_positions)} configured vault read(s) failed, so those positions were not included."
        return message

    if any(term in q for term in ("worth", "usd value", "value in usd", "portfolio value", "net worth", "dollar value")):
        return (
            "I can report token amounts, but this snapshot has no verified, block-matched price feed. "
            "I can’t calculate a trustworthy USD portfolio value from these balances, so I won’t guess."
        )

    if any(word in q for word in ("biggest", "largest", "most", "highest")):
        rank_balances = balances
        rank_positions = positions
        if requested:
            rank_balances = [row for row in balances if str(row.get("symbol", "")).strip().lower() == requested]
            rank_positions = [row for row in positions if str(row.get("asset_symbol", "")).strip().lower() == requested]
        candidates = [
            {**row, "_asset_key": token_key(row)}
            for row in rank_balances if row.get("amount") is not None and row["amount"] > 0
        ]
        candidates.extend(
            {**row, "symbol": row["asset_symbol"], "amount": row["assets"],
             "_asset_key": token_key(row, is_vault=True)}
            for row in rank_positions if row.get("assets") is not None and row["assets"] > 0
        )
        if not candidates:
            message = "I can’t rank positions because this snapshot has no readable, non-zero balances."
            if failed_balances or failed_positions:
                message += " Some reads failed, so the available data may be incomplete."
            return message
        asset_keys = {row["_asset_key"] for row in candidates}
        if len(asset_keys) != 1:
            return (
                "I can’t identify one largest position from these figures. They use different token "
                "contracts or assets, and the snapshot has no complete, block-matched price data to "
                "compare their values. I won’t compare unlike token amounts."
            )
        top = max(candidates, key=lambda row: row["amount"])
        location = top.get("protocol", "wallet")
        answer = (
            f"The largest readable position is {location}: {fmt(top['amount'])} {top['symbol']} "
            f"by token units. This compares the same token only; it is not a USD ranking.\n"
            f"{source_line(top)}"
        )
        if failed_balances or failed_positions:
            answer += "\nSome configured reads failed, so an unreadable position could be larger."
        return answer

    if requested:
        wallet_rows = [row for row in balances if str(row.get("symbol", "")).strip().lower() == requested]
        vault_rows = [row for row in positions if str(row.get("asset_symbol", "")).strip().lower() == requested]
        unavailable_wallet = [row for row in wallet_rows if row.get("amount") is None]
        readable_wallet = [row for row in wallet_rows if row.get("amount") is not None]
        if not wallet_rows and not vault_rows:
            message = (
                f"I don’t have a readable {requested.upper()} entry in this snapshot. "
                "The app checks its tracked token list and the vaults configured on this page; "
                "that doesn’t prove the wallet has no other tokens."
            )
            if failed_positions:
                message += f" {len(failed_positions)} configured vault read(s) also failed, so I can’t rule out a position there."
            return message

        wallet_only = any(term in q for term in ("in my wallet", "in the wallet", "wallet only", "wallet balance"))
        is_total = any(term in q for term in ("total", "altogether", "in all", "across", "combined", "how much"))
        if wallet_only:
            vault_rows = []
            is_total = False
        rows_for_sum = [(row, token_key(row)) for row in readable_wallet]
        rows_for_sum.extend((row, token_key(row, is_vault=True)) for row in vault_rows)
        identities = {key for _, key in rows_for_sum}
        wants_location = any(term in q for term in ("where", "held", "holding", "holdings", "located", "which protocol"))

        if is_total and len(identities) > 1:
            return (
                f"I found entries labeled {requested.upper()}, but they point to different token contracts. "
                "I can list them separately, but can’t safely add them into one total."
            )

        lines = []
        if wants_location:
            lines.append(f"Here’s where {requested.upper()} appears in the readable snapshot:")
        else:
            lines.append(f"Readable {requested.upper()} amounts in this snapshot:")
        for row in readable_wallet:
            lines.append(f"- Wallet: {fmt(row['amount'])} {row['symbol']}")
            lines.append(f"  {source_line(row)}")
        for row in vault_rows:
            lines.append(
                f"- {row['protocol']} vault: {fmt(row['assets'])} {row['asset_symbol']} "
                f"backed by {fmt(row['shares'])} shares"
            )
            lines.append(f"  {source_line(row)}")

        if is_total and rows_for_sum and len(identities) == 1:
            total = sum(float(row["amount"] if "amount" in row else row["assets"]) for row, _ in rows_for_sum)
            lines.append(f"Total across these locations: {fmt(total)} {requested.upper()}.")
        if unavailable_wallet:
            lines.append(
                f"I couldn’t read {requested.upper()} from {len(unavailable_wallet)} token contract read(s); "
                "those values are unavailable, not zero."
            )
            lines.extend(source_line(row) for row in unavailable_wallet)
        if failed_positions and (is_total or wants_location):
            lines.append(
                f"Note: {len(failed_positions)} configured vault read(s) failed. "
                "The listed amounts may not include every configured vault."
            )
        return "\n".join(lines)

    if any(word in q for word in ("position", "vault", "deposited", "invested", "protocol")):
        if not positions_all:
            return (
                "No vaults are configured in this snapshot, so I can’t report protocol positions. "
                "Add the vault contract addresses and read the portfolio again."
            )
        lines = ["Configured vault reads (only the contracts listed here were checked; this is not a complete protocol scan. Assets shown use ERC-4626 convertToAssets at this block, not an APY or redemption quote):"]
        for row in positions_all:
            if not row.get("available"):
                lines.append(f"- {row['protocol']}: unavailable ({row.get('error', 'contract read failed')}). {source_line(row)}")
            elif row.get("shares", 0) == 0:
                lines.append(f"- {row['protocol']}: no shares held at this block.")
                lines.append(f"  {source_line(row)}")
            else:
                lines.append(
                    f"- {row['protocol']}: {fmt(row['assets'])} {row['asset_symbol']} "
                    f"from {fmt(row['shares'])} shares."
                )
                lines.append(f"  {source_line(row)}")
        return "\n".join(lines)

    if any(word in q for word in ("balance", "balances", "holdings", "portfolio", "wallet", "assets")):
        readable = [row for row in balances if row.get("amount") is not None]
        if not readable:
            return "I couldn’t read any tracked wallet balances at this snapshot block."
        lines = ["Tracked wallet balances:"]
        for row in readable:
            lines.append(f"- {fmt(row['amount'])} {row['symbol']} ({row.get('label', 'wallet balance')})")
            lines.append(f"  {source_line(row)}")
        if failed_balances:
            lines.append(
                f"{len(failed_balances)} tracked token balance(s) could not be read; "
                "they’re shown as unavailable, not zero."
            )
            lines.extend(f"- {row['symbol']}: {source_line(row)}" for row in failed_balances)
        if "portfolio" in q:
            lines.append("These are token amounts, not a USD portfolio valuation; no verified price feed is available in this snapshot.")
        return "\n".join(lines)

    return (
        "I can answer from this snapshot about tracked wallet balances, a tracked token’s locations, "
        "configured ERC-4626 vault positions, comparable same-token amounts, and whether yield data "
        "is available. This snapshot doesn’t support the question as asked, so I can’t verify an answer."
    )
