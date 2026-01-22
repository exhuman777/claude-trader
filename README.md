# Claude Trader

**Trade Polymarket using natural language with Claude Code.**

Instead of clicking around or writing code, just tell Claude what you want:

```
> buy 10 shares of "Trump wins" at 45 cents
> show me the orderbook
> what's my position?
> cancel all my orders
```

## Why this exists

I use [Claude Code](https://claude.ai/code) for development and wanted to trade Polymarket without leaving the terminal. This gives Claude the tools to understand markets and execute trades on my behalf.

## Who this is for

- **Claude Code users** who trade prediction markets
- **Developers** building AI trading tools
- **NOT for beginners** - you should understand Polymarket first

## Quick look

```
User: "buy 10 at 35c for the Trump market"

Claude:
┌───────────┬─────────────────────────┬─────────┐
│  Action   │        Details          │ Status  │
├───────────┼─────────────────────────┼─────────┤
│ BUY YES   │ 10 @ 35¢ ($3.50)        │ pending │
│ Market    │ Trump wins 2024         │         │
└───────────┴─────────────────────────┴─────────┘
Confirm? (y/n)

User: "yes"

Claude: ✓ Order matched
```

## Install

```bash
git clone https://github.com/exhuman777/claude-trader.git
cd claude-trader

python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Setup credentials (guided wizard)
python setup_wizard.py

# Start Claude Code
claude
```

## What you can say

**View markets:**
```
"Load the Trump election event"
"Show me the orderbook for market 1230810"
"What are the best bid and ask?"
```

**Trade:**
```
"Buy 5 YES at 35 cents"
"Sell 10 at 60 cents"
"Quick buy $50 worth at market price"
```

**Ladders:**
```
"Set up a buy ladder from 30 to 40 cents, 5 orders, 10 shares each"
"Ladder sell from 60 to 70, 5 orders"
```

**Manage:**
```
"Show my open orders"
"Cancel order 0x123..."
"Cancel all orders"
"What's my USDC balance?"
"Show my positions"
```

## Available functions

| Function | Purpose |
|----------|---------|
| `show_event(slug)` | Load event from URL |
| `place_order(id, side, price, size)` | Limit order |
| `place_ladder(...)` | Multiple orders |
| `quick_buy(id, size)` | Buy at ask |
| `quick_sell(id, size)` | Sell at bid |
| `show_orders()` | Open orders |
| `cancel_order(id)` | Cancel one |
| `cancel_all_orders()` | Cancel all |
| `get_positions()` | Your positions |
| `get_balances()` | USDC balance |

## Interactive mode

For a guided CLI experience:

```bash
python interactive.py
```

Then:
```
trade> https://polymarket.com/event/trump-election
trade> buy 5 jan 25 at 35c
trade> ladder sell from 60 to 70 jan 31 5 orders 5 shares
trade> orders
trade> cancel all
```

## Price format

- Prices are decimals: `0.35` = 35 cents
- Display shows: `35¢`
- NEVER use percentages (35% means something different)

## Automation (auto.py)

Follow whale trades:
```python
from auto import whale_follow
whale_follow(min_usd=5000, bet=5, only_profitable=True)
```

Top volume betting:
```python
from auto import top_volume_bet
top_volume_bet(bet=5, count=3)
```

## Files

```
├── polymarket_api.py   # Core API (import this)
├── interactive.py      # Interactive CLI
├── trade.py            # Direct CLI
├── auto.py             # Automation
├── cockpit.py          # Display helpers
├── setup_wizard.py     # Credential setup
├── CLAUDE.md           # AI agent instructions
└── PLAYBOOK.md         # Proven patterns
```

## Security

- Credentials stored in `data/.trading_config.json` (gitignored)
- Optional password encryption for private key
- Never commit secrets

## Limitations

- Polymarket only
- Requires Claude Code or similar AI assistant
- You're responsible for your trades
- API rate limits apply

## Related

- [yesno-events](https://github.com/exhuman777/yesno-events) - Full trading terminal with TUI
- [polymarket-python](https://github.com/exhuman777/polymarket-python) - Clean API wrapper

## License

MIT - Do what you want.
