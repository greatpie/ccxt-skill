# ccxt skill

A Claude Code / Claude Agent SDK [skill](https://docs.claude.com/en/docs/claude-code/skills) that teaches Claude how to use the [CCXT](https://github.com/ccxt/ccxt) library correctly when integrating with crypto exchanges.

It focuses on the things ccxt users keep getting wrong:

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

### Recommended — via [`vercel-labs/skills`](https://github.com/vercel-labs/skills) CLI

The fastest way. Works with Claude Code, Codex, Cursor, OpenCode, and ~15 other agent runtimes.

**Project-scoped (added under `.claude/skills/` in the current repo):**

```bash
npx skills add greatpie/ccxt-skill
```

**User-scoped (available in every project on this machine):**

```bash
npx skills add -g greatpie/ccxt-skill
```

**Target Claude Code only** (skip other agent layouts):

```bash
npx skills add greatpie/ccxt-skill -a claude-code
```

**Verify and manage:**

```bash
npx skills list           # list installed skills
npx skills update         # pull updates from this repo
npx skills remove ccxt    # uninstall
```

> The CLI auto-discovers `SKILL.md` at the repo root, so no extra path argument is needed.

### Manual install (no CLI)

If you'd rather not use the CLI, just drop the directory where Claude looks for skills.

**Claude Code, user-level (every project):**

```bash
git clone https://github.com/greatpie/ccxt-skill ~/.claude/skills/ccxt
```

**Claude Code, project-level (committed alongside your project):**

```bash
git clone https://github.com/greatpie/ccxt-skill .claude/skills/ccxt
```

**Claude Agent SDK:**

```python
from claude_agent_sdk import Agent

agent = Agent(skills=["./skills/ccxt"])
```

Or set `CLAUDE_SKILLS_DIR` to a parent directory containing `ccxt/`.

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

Each example is a [PEP 723](https://peps.python.org/pep-0723/) self-contained script with inline dependency metadata, so [`uv`](https://docs.astral.sh/uv/) can run them in an ephemeral venv with no setup:

```bash
uv run examples/websocket_orderbook.py
uv run examples/async_with_proxy.py
uv run examples/binance_demo_trading.py
uv run examples/markets_caching.py
```

Configuration is loaded from environment variables (or a `.env` file in the working directory) via `pydantic-settings`:

| Example | Required env vars |
|---|---|
| `websocket_orderbook.py` | none |
| `async_with_proxy.py` | `CCXT_PROXY_URL=socks5h://user:pass@host:port` |
| `binance_demo_trading.py` | `BINANCE_DEMO_API_KEY`, `BINANCE_DEMO_SECRET` (from your Binance demo trading account) |
| `markets_caching.py` | `REDIS_URL=redis://localhost:6379` |

If you'd rather manage deps yourself with `uv add` in an existing project:

```bash
uv add ccxt aiohttp_socks redis pydantic-settings
uv run python examples/websocket_orderbook.py
```

## Contributing

The skill format is just markdown + a YAML frontmatter block. To extend it:

1. Edit `SKILL.md` — keep it under ~500 lines so it loads quickly
2. Add new runnable examples under `examples/` and link them from the relevant section
3. Update the `description:` in the frontmatter if you add new triggering keywords
4. Test by asking Claude a relevant question and confirming the skill activates

## License

MIT. See `LICENSE`.
