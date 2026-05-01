"""
Caching CCXT load_markets() output in Redis, plus the consumer-side helper
to hydrate a fresh exchange instance from that cache without hitting the
network.

Why:
- load_markets() returns metadata for every symbol on the exchange. For
  Binance spot+futures it's hundreds of KB to several MB and takes 1–3
  seconds, plus a sizeable rate-limit weight cost.
- An exchange instance caches markets in-process automatically, but multi-
  process / multi-instance deployments will reload on every boot.
- Caching the result in Redis lets every consumer (API server, worker
  processes, downstream services) hydrate from one source instead of hitting
  the exchange.

Pattern:
    1. A single loader populates Redis on a schedule (or at startup).
    2. Consumers read from Redis and call hydrate_markets_from_cache() on
       each new exchange instance, which uses ccxt's public `set_markets()`
       API to populate `markets`, `markets_by_id`, `symbols`, `ids`, and
       `currencies` correctly.

Why set_markets() instead of `exchange.markets = ...`:
- ccxt considers an instance "loaded" only when several mirror dicts
  (`markets_by_id`, `symbols`, `ids`, `currencies_by_id`, ...) are all in
  sync. Setting `markets` alone leaves these stale, and the first call
  that touches a market id (order placement, normalization) triggers an
  implicit `load_markets()` anyway — defeating the cache.
- `set_markets(markets, currencies)` is the official entry point and
  populates every mirror correctly.
"""

from __future__ import annotations

import asyncio
import json
import os

import ccxt.async_support as ccxt
import redis.asyncio as aioredis

CACHE_KEY_MARKETS = "ccxt:markets:binance"
CACHE_KEY_CURRENCIES = "ccxt:currencies:binance"
CACHE_TTL_SECONDS = 60 * 60  # 1 hour


async def load_and_cache_markets(redis: aioredis.Redis) -> tuple[dict, dict]:
    """Load markets from the exchange ONCE and write to Redis.

    Run this on a schedule (or startup of a single 'cache warmer' process),
    not from request handlers.
    """
    exchange = ccxt.binance({"enableRateLimit": True})
    try:
        markets = await exchange.load_markets()
        currencies = exchange.currencies or {}
    finally:
        await exchange.close()

    pipe = redis.pipeline()
    pipe.set(CACHE_KEY_MARKETS, json.dumps(markets), ex=CACHE_TTL_SECONDS)
    pipe.set(CACHE_KEY_CURRENCIES, json.dumps(currencies), ex=CACHE_TTL_SECONDS)
    await pipe.execute()

    return markets, currencies


async def read_cached_markets(
    redis: aioredis.Redis,
) -> tuple[dict, dict] | None:
    """Read markets + currencies from Redis. Returns None on cache miss."""
    raw_markets = await redis.get(CACHE_KEY_MARKETS)
    if not raw_markets:
        return None
    raw_currencies = await redis.get(CACHE_KEY_CURRENCIES)
    return json.loads(raw_markets), json.loads(raw_currencies or "{}")


def hydrate_markets_from_cache(
    exchange: ccxt.Exchange,
    markets: dict,
    currencies: dict | None = None,
) -> None:
    """Inject cached markets into an exchange instance without hitting the API.

    After this call, the exchange behaves as if `await load_markets()` had
    completed: `markets`, `markets_by_id`, `symbols`, `ids`, and the
    currency mirrors are all populated.
    """
    exchange.set_markets(markets, currencies)


async def main() -> None:
    redis = aioredis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
    try:
        cached = await read_cached_markets(redis)
        if cached is None:
            print("Cache miss — loading from exchange...")
            markets, currencies = await load_and_cache_markets(redis)
            source = "exchange"
        else:
            markets, currencies = cached
            source = "cache"
        print(f"Loaded {len(markets)} markets from {source}")

        # Consumer side: hydrate a fresh exchange without a network roundtrip.
        consumer = ccxt.binance({"enableRateLimit": True})
        try:
            hydrate_markets_from_cache(consumer, markets, currencies)
            assert consumer.markets, "markets not populated"
            assert consumer.markets_by_id, "markets_by_id not populated"
            assert "BTC/USDT" in consumer.symbols
            print(
                f"Consumer hydrated: {len(consumer.symbols)} symbols, "
                f"{len(consumer.markets_by_id)} ids, "
                f"BTC/USDT precision={consumer.market('BTC/USDT')['precision']}"
            )
        finally:
            await consumer.close()
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())
