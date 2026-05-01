# ccxt skill

A Claude Code / Claude Agent SDK [skill](https://docs.claude.com/en/docs/claude-code/skills) that teaches Claude how to use the [CCXT](https://github.com/ccxt/ccxt) library correctly when integrating with crypto exchanges.

It captures lessons learned from real production code (a multi-tenant trading service running freqtrade-ms + Aster DEX), focused on the things ccxt users keep getting wrong:

- The `ccxt.pro` import path after the package merge
- WebSocket (`watch_*`) over REST polling (`fetch_*`) for rate-limit safety
- Async ccxt + `aiohttp_socks` socks5 proxies (the plain `proxies` dict doesn't work with async)
- Binance **demo trading** as the modern replacement for testnet
- Caching `load_markets()` in Redis instead of reloading on every request

## When does it trigger?

The description is tuned to fire whenever the user mentions:

- `ccxt`, `ccxt.pro`, or specific exchanges (`binance`, `okx`, `bybit`, `aster`, …)
- WebSocket / streaming market data, `watch_order_book`, `watch_ticker`
- Order placement, demo trading, testnet, `enable_demo_trading`
- `load_markets`, market metadata caching
- Async ccxt + proxy / socks5 / aiohttp issues

Example queries that should activate it:

> "Why am I getting `No module named ccxtpro`?"
> "Help me subscribe to BTC/USDT order book on Binance via WebSocket"
> "What's the best way to use ccxt async with a socks5 proxy?"
> "How do I cache `load_markets()` across processes?"
> "Is Binance testnet still the right way to test order placement?"

## Installation

This is a plain skill directory — drop it anywhere Claude scans for skills.

### Claude Code

**User-level (available in every project):**

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/<your-fork>/ccxt-skill ~/.claude/skills/ccxt
```

**Project-level (committed alongside the project):**

```bash
mkdir -p .claude/skills
git clone https://github.com/<your-fork>/ccxt-skill .claude/skills/ccxt
```

Either layout works — Claude Code reads `SKILL.md` from any subdirectory under those roots.

### Claude Agent SDK

Pass the skill directory to the agent at startup:

```python
from claude_agent_sdk import Agent

agent = Agent(skills=["./skills/ccxt"])
```

Or set the `CLAUDE_SKILLS_DIR` environment variable to a parent directory containing `ccxt/`.

### Verify it loaded

In Claude Code, run:

```
/skills
```

`ccxt` should appear in the list. To force-trigger it for a sanity check, ask Claude:

> "How do I import ccxt.pro WebSocket support?"

If the skill is active, the answer will reflect the post-merge import pattern (`import ccxt.pro as ccxtpro`) without you having to specify it.

## What's inside

```
ccxt/
├── SKILL.md                       # The actual skill (loaded into Claude's context)
├── README.md                      # This file (human-facing)
└── examples/
    ├── websocket_orderbook.py     # Minimal watch_order_book loop
    ├── async_with_proxy.py        # Async ccxt + aiohttp_socks ProxyConnector
    ├── binance_demo_trading.py    # enable_demo_trading(True) pattern
    └── markets_caching.py         # Redis-backed load_markets cache
```

`SKILL.md` is the file Claude reads. The `examples/` directory contains runnable Python scripts the skill links to so Claude can show concrete code patterns when relevant.

## Running the examples locally

```bash
pip install ccxt aiohttp_socks redis
python examples/websocket_orderbook.py
```

For `async_with_proxy.py`, set `APP_PROXY_URL=socks5h://user:pass@host:port`.
For `binance_demo_trading.py`, set `BINANCE_DEMO_API_KEY` and `BINANCE_DEMO_SECRET` (obtain from your Binance demo trading account).
For `markets_caching.py`, point `APP_REDIS_URL` at a running Redis instance.

## Contributing

The skill format is just markdown + a YAML frontmatter block. To extend it:

1. Edit `SKILL.md` — keep it under ~500 lines so it loads quickly
2. Add new runnable examples under `examples/` and link them from the relevant section
3. Update the `description:` in the frontmatter if you add new triggering keywords
4. Test by asking Claude a relevant question and confirming the skill activates

## License

MIT. See `LICENSE`.
