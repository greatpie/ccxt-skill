"""
Caching CCXT load_markets() output in Redis.

Why:
- load_markets() returns metadata for every symbol on the exchange. For
  Binance spot+futures it's hundreds of KB to several MB and takes 1–3
  seconds, plus a sizeable rate-limit weight cost.
- An exchange instance caches markets in-process automatically, but multi-
  process / multi-instance deployments will reload on every boot.
- Caching the result in Redis lets every consumer (API server, workers,
  freqtrade-ms) hydrate from one source instead of hitting the exchange.

Pattern:
    1. A single loader populates Redis on a schedule (or at startup).
    2. Consumers read from Redis. If the cache is empty they fall back to
       calling load_markets() themselves and write the result back.
"""

from __future__ import annotations

import asyncio
import json
import os

import ccxt.async_support as ccxt
import redis.asyncio as aioredis

CACHE_KEY = "ccxt:markets:binance"
CACHE_TTL_SECONDS = 60 * 60  # 1 hour


async def load_markets_cached(redis: aioredis.Redis) -> dict:
    cached = await redis.get(CACHE_KEY)
    if cached:
        return json.loads(cached)

    exchange = ccxt.binance({"enableRateLimit": True})
    try:
        markets = await exchange.load_markets()
    finally:
        await exchange.close()

    await redis.set(CACHE_KEY, json.dumps(markets), ex=CACHE_TTL_SECONDS)
    return markets


async def main() -> None:
    redis = aioredis.from_url(os.environ.get("APP_REDIS_URL", "redis://localhost:6379"))
    try:
        markets = await load_markets_cached(redis)
        print(f"Loaded {len(markets)} markets (from {'cache' if markets else 'exchange'})")
        sample = markets.get("BTC/USDT")
        if sample:
            print("BTC/USDT precision:", sample.get("precision"))
            print("BTC/USDT limits:", sample.get("limits"))
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
