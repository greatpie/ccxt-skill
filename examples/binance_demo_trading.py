# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ccxt",
#     "pydantic-settings",
# ]
# ///
"""
Binance demo trading via CCXT — the modern replacement for testnet.

Run with:
    BINANCE_DEMO_API_KEY=... BINANCE_DEMO_SECRET=... \\
        uv run examples/binance_demo_trading.py

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

import ccxt
from pydantic_settings import BaseSettings, SettingsConfigDict


class DemoSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    binance_demo_api_key: str
    binance_demo_secret: str


def main() -> None:
    settings = DemoSettings()  # raises if env vars are missing

    exchange = ccxt.binance({
        "apiKey": settings.binance_demo_api_key,
        "secret": settings.binance_demo_secret,
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
