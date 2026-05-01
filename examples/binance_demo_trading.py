"""
Binance demo trading via CCXT — the modern replacement for testnet.

Key points:
- `enable_demo_trading(True)` is the official switch. Do NOT manually override
  URLs to point at testnet.binance.vision — that path is deprecated.
- Demo trading uses real market data but simulated balances. Order placement
  exercises the same code path as production, so it's the right mode for
  validating the order-submission pipeline.
- For pure strategy validation that doesn't need order submission, prefer
  freqtrade's dry-run mode (no API keys required at all).
"""

from __future__ import annotations

import os

import ccxt


def main() -> None:
    api_key = os.environ["BINANCE_DEMO_API_KEY"]
    secret = os.environ["BINANCE_DEMO_SECRET"]

    exchange = ccxt.binance({
        "apiKey": api_key,
        "secret": secret,
        "enableRateLimit": True,
        "options": {
            "defaultType": "future",  # or "spot"
        },
    })
    exchange.enable_demo_trading(True)

    balance = exchange.fetch_balance()
    print("Demo balance:", balance.get("USDT", {}))

    # Place a small simulated market order on the demo account.
    order = exchange.create_order(
        symbol="BTC/USDT",
        type="market",
        side="buy",
        amount=0.001,
    )
    print("Demo order:", order["id"], order["status"])


if __name__ == "__main__":
    main()
