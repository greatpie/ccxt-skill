# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "ccxt",
#     "aiohttp_socks",
#     "pydantic-settings",
# ]
# ///
"""
Async CCXT + socks5 proxy — the standard way to route Binance/OKX/etc.
through a proxy when running async code.

Run with:
    CCXT_PROXY_URL=socks5h://user:pass@host:1080 uv run examples/async_with_proxy.py

Key points:
- Async ccxt runs on aiohttp; the plain `proxies` dict does NOT work.
- You must build an aiohttp_socks.ProxyConnector and pass an aiohttp session
  built on top of it into ccxt as `session`.
- Use `socks5h://` so the proxy resolves DNS (avoids local DNS leaks /
  poisoned resolvers).
- The same connector tunnels both REST and WebSocket (wss).
"""

from __future__ import annotations

import asyncio

import aiohttp
import ccxt.pro as ccxtpro
from aiohttp_socks import ProxyConnector
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProxySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ccxt_proxy_url: str = "socks5h://user:pass@proxy-host:1080"


async def main() -> None:
    settings = ProxySettings()

    connector = ProxyConnector.from_url(settings.ccxt_proxy_url)
    session = aiohttp.ClientSession(connector=connector)

    exchange = ccxtpro.binance({
        "enableRateLimit": True,
        "session": session,  # inject the socks5-backed aiohttp session
    })

    try:
        ticker = await exchange.fetch_ticker("BTC/USDT")
        print(f"REST via proxy — BTC/USDT last: {ticker['last']}")

        ob = await exchange.watch_order_book("BTC/USDT")
        print(f"WSS via proxy — best bid/ask: {ob['bids'][0][0]} / {ob['asks'][0][0]}")
    finally:
        await exchange.close()
        await session.close()


if __name__ == "__main__":
    asyncio.run(main())
