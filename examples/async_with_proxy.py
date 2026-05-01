"""
Async CCXT + socks5 proxy — the project's standard way to reach Binance/OKX
through a proxy.

Dependencies:
    pip install ccxt aiohttp_socks

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
import os

import aiohttp
import ccxt.pro as ccxtpro
from aiohttp_socks import ProxyConnector


async def main() -> None:
    proxy_url = os.environ.get("APP_PROXY_URL", "socks5h://user:pass@proxy-host:1080")

    connector = ProxyConnector.from_url(proxy_url)
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
