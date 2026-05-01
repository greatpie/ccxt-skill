---
name: ccxt
description: Best-practices guide for using the CCXT library to interact with crypto exchanges (market data subscription, order placement, account queries, etc.). Use this skill proactively whenever the user mentions ccxt, ccxt.pro, exchange integration (Binance/OKX/Bybit/Aster), WebSocket market feeds, order endpoints, demo trading, testnet, load_markets, or exchange proxy issues. Covers the post-merge ccxt.pro import pattern, WebSocket-first strategy, Binance demo trading replacing testnet, async + socks5 proxy setup, and load_markets caching.
---

# CCXT Usage Guide

CCXT is a unified Python/JS wrapper around many crypto exchange APIs. This skill captures the things people most commonly get wrong when integrating it — read it before writing new exchange integration code so you don't re-discover the same pitfalls.

---

## 1. CCXT Pro is now part of the main CCXT package

`ccxt.pro` is no longer a separate PyPI package — it has been merged into `ccxt`. WebSocket methods (everything starting with `watch_`) still need to be accessed through the `ccxt.pro` namespace, however.

```bash
pip install ccxt   # do NOT install ccxt.pro — it's already bundled
```

```python
# WebSocket / Pro features
import ccxt.pro as ccxtpro

# Plain synchronous REST
import ccxt
```

**Why this matters**: treating Pro as a separate package leads to `ModuleNotFoundError: No module named 'ccxtpro'` — the most common breakage when upgrading from ccxt 1.x to 2.x+.

See [`examples/websocket_orderbook.py`](examples/websocket_orderbook.py).

---

## 2. Prefer WebSocket over REST polling

REST endpoints have strict rate limits (Binance ≈ 1200 req/min per IP). High-frequency polling will get you throttled or IP-banned. **If the exchange exposes a WebSocket channel, use `watch_*` instead of `fetch_*`.**

| REST (avoid for high-frequency loops) | WebSocket (preferred) |
|---|---|
| `fetch_order_book(symbol)` | `watch_order_book(symbol)` |
| `fetch_ticker(symbol)` | `watch_ticker(symbol)` |
| `fetch_ohlcv(symbol, tf)` | `watch_ohlcv(symbol, tf)` |
| `fetch_trades(symbol)` | `watch_trades(symbol)` |
| `fetch_balance()` | `watch_balance()` (where supported) |
| `fetch_orders()` | `watch_orders()` |

WebSocket data is push-based — no manual rate limiting needed, and **does not count against the REST rate limit budget**.

---

## 3. Prefer async CCXT

Synchronous CCXT blocks the event loop and integrates poorly with FastAPI / asyncio. **For any IO-bound exchange code, use `ccxt.async_support` or `ccxt.pro`** (the latter is async by definition).

```python
import ccxt.async_support as ccxt   # async REST
import ccxt.pro as ccxtpro          # async WebSocket (also exposes all REST methods)
```

**Always `await exchange.close()`** at shutdown, otherwise you'll see `Unclosed client session` warnings from aiohttp and leak connections.

See [`examples/async_with_proxy.py`](examples/async_with_proxy.py).

---

## 4. Async CCXT requires an async HTTP proxy — use socks5

Sync ccxt accepts a `proxies` dict for plain HTTP proxies, but **async CCXT does not** — it runs on `aiohttp`, which needs an async-compatible connector.

**Use socks5**, because:
- It handles both HTTP and WebSocket (HTTP proxies don't tunnel `wss`)
- `aiohttp_socks` provides a battle-tested connector
- A single `socks5h://user:pass@host:port` URL covers REST and streaming traffic uniformly

```python
from aiohttp_socks import ProxyConnector
import aiohttp
import ccxt.pro as ccxtpro

connector = ProxyConnector.from_url('socks5h://user:pass@proxy-host:port')
session = aiohttp.ClientSession(connector=connector)

exchange = ccxtpro.binance({
    'enableRateLimit': True,
    'session': session,   # inject the session backed by the socks5 connector
})
```

**`socks5h` vs `socks5`**: `socks5h` resolves DNS on the proxy server, avoiding local DNS leaks and DNS poisoning. Always use `socks5h://` in production.

---

## 5. Binance testnet is superseded by demo trading

Binance's old testnet (`https://testnet.binance.vision`) is not fully removed but is **no longer the recommended path**. Use demo trading instead.

```python
import ccxt
exchange = ccxt.binance({
    'apiKey': 'YOUR_DEMO_KEY',
    'secret': 'YOUR_DEMO_SECRET',
})
exchange.enable_demo_trading(True)   # the key switch
```

**Practical guidance:**
- Don't manually override the API base URL to point at `testnet.binance.vision` — that path is deprecated and leads to inconsistent behavior between spot and futures
- For pure strategy validation, prefer simulated/dry-run modes that need no API keys at all (e.g. freqtrade's dry-run mode)
- Use demo trading only when you specifically need to exercise the order placement path end-to-end

See [`examples/binance_demo_trading.py`](examples/binance_demo_trading.py).

---

## 6. Cache `load_markets()` — never call it repeatedly

`load_markets()` returns metadata for every symbol on the exchange: precision, limits, fees, margin tiers, etc. For Binance spot + futures combined this is **hundreds of KB to several MB**, takes 1–3 seconds, and consumes a chunk of your weight budget.

**Caching strategy:**
- In-process: an exchange instance caches `markets` automatically — but **multi-process / multi-instance deployments will reload it every time**
- Cross-process: write to Redis (or another shared cache) under a key like `ccxt:markets:binance:future`, TTL of a few hours to a day
- Pass the cached payload to downstream consumers (other services, subprocesses, freqtrade configs) so they can hydrate without their own `load_markets` call

**Anti-pattern (reloads on every request — guaranteed rate-limit hit):**
```python
async def get_price(symbol):
    ex = ccxtpro.binance()
    await ex.load_markets()       # WRONG: reloaded each call
    ...
```

**Correct (load once at startup, hand off to consumers):**
```python
# Producer (one cache-warmer process / scheduled job):
markets = await ex.load_markets()
redis.set('ccxt:markets:binance', json.dumps(markets), ex=3600)
redis.set('ccxt:currencies:binance', json.dumps(ex.currencies), ex=3600)

# Consumer (every other process):
consumer = ccxt.binance(...)
consumer.set_markets(markets, currencies)   # official hydration API
# consumer.markets, .markets_by_id, .symbols, .ids, .currencies are now all populated
```

**Use `set_markets(markets, currencies)`, not `exchange.markets = markets`.** ccxt
considers an instance "loaded" only when several mirror dicts (`markets_by_id`,
`symbols`, `ids`, `currencies_by_id`) are all in sync. Setting `markets` alone
leaves these stale, and the first call that touches a market id (order
placement, symbol normalization) will trigger an implicit `load_markets()`
anyway — defeating the cache.

See [`examples/markets_caching.py`](examples/markets_caching.py) for a complete
producer + consumer pair, including a `hydrate_markets_from_cache(exchange,
markets, currencies)` helper.

---

## Quick reference

| Need | Do |
|---|---|
| Import WebSocket | `import ccxt.pro as ccxtpro` |
| Avoid rate limits | Use `watch_*` instead of polling `fetch_*` |
| Async integration | `ccxt.async_support` / `ccxt.pro`, always `await ex.close()` |
| Proxy | `socks5h://` + `aiohttp_socks.ProxyConnector` injected as `session` |
| Binance test mode | dry-run for strategies; `enable_demo_trading(True)` for order-path testing |
| Markets metadata | Load once at startup → cache in Redis → inject into downstream consumers |
