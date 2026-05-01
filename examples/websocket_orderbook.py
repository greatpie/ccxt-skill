"""
Minimal CCXT Pro WebSocket order-book example.

Key points:
- Use the ccxt.pro namespace even after the package merge.
- watch_order_book is async and returns when the exchange pushes an update —
  no manual sleep / rate limiting needed.
- Always await exchange.close() to release the connection pool.
"""

from __future__ import annotations

import asyncio

import ccxt.pro as ccxtpro


async def main() -> None:
    exchange = ccxtpro.binance({
        "enableRateLimit": True,
    })

    symbol = "BTC/USDT"
    print(f"Subscribing to live order book for {symbol}...")

    try:
        while True:
            orderbook = await exchange.watch_order_book(symbol)
            best_bid = orderbook["bids"][0][0]
            best_ask = orderbook["asks"][0][0]
            print(
                f"time={orderbook['datetime']} "
                f"bid={best_bid} ask={best_ask}"
            )
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down...")
    finally:
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(main())
