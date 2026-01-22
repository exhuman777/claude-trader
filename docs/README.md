# Claude Polymarket Trading Cockpit

> Trade Polymarket prediction markets directly through Claude Code with professional-grade tooling.

```
┌─────────────────────────────────────────────────────────────────┐
│  CLAUDE POLYMARKET TRADING COCKPIT                              │
├─────────┬─────────────────────────────────┬───────┬─────────────┤
│ Market  │ Description                     │ Price │ Status      │
├─────────┼─────────────────────────────────┼───────┼─────────────┤
│ 1172391 │ Elon 360-379 tweets             │ 12¢   │ ✓ live      │
│ 1172392 │ Elon 380-399 tweets             │ 20¢   │ ✓ live      │
└─────────┴─────────────────────────────────┴───────┴─────────────┘
```

## Features

- **Natural Language Trading** - "buy 10 yes at 35c" just works
- **Preview Before Execute** - See exactly what will happen before confirming
- **Ladder Orders** - Place multiple orders across price ranges in seconds
- **Smart Search** - Search 1,330+ indexed markets instantly
- **Position Tracking** - View portfolio, orders, and P&L
- **Learning Memory** - Claude remembers your trading patterns

## Quick Start

```bash
# Clone and setup
git clone https://github.com/yourusername/claude-polymarket-trading
cd claude-polymarket-trading
pip install py-clob-client

# Configure credentials
cp config.example.json data/.trading_config.json
# Edit with your Polymarket API keys

# Start trading with Claude Code
claude
```

Then just talk:
```
You: show me elon tweet markets
You: buy 100 shares of 360-379 at 12c
You: create sell ladder from 15c to 20c, 50 shares each
```

## How It Works

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   You Talk   │ ──► │ Claude Plans │ ──► │   Preview    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Results    │ ◄── │   Execute    │ ◄── │  You Confirm │
└──────────────┘     └──────────────┘     └──────────────┘
```

1. **You describe** what you want to trade
2. **Claude shows preview** with exact orders planned
3. **You confirm** ("yes", "go", "confirm")
4. **Claude executes** and shows results

## Example Session

```
You: https://polymarket.com/event/elon-musk-of-tweets-january-16-january-23
     i have 786 shares of 360-379, create sell ladder from 12c to 18c

Claude:
┌──────────┬─────────────────────────────────────────────┬─────────┐
│ Market   │ Details                                     │ Status  │
├──────────┼─────────────────────────────────────────────┼─────────┤
│ 360-379  │ SELL 100 each @ 12,13,14,15,16,17,18¢       │ pending │
│          │ 7 orders = 700 shares                       │         │
└──────────┴─────────────────────────────────────────────┴─────────┘
Confirm?

You: yes

Claude:
┌──────────┬─────────────────────────────────────────────┬───────────┐
│ Market   │ Details                                     │ Status    │
├──────────┼─────────────────────────────────────────────┼───────────┤
│ 360-379  │ SELL 100 @ 12¢                              │ ✓ matched │
│ 360-379  │ SELL 100 each @ 13-18¢ (6 orders)           │ ✓ live    │
└──────────┴─────────────────────────────────────────────┴───────────┘
```

## Project Structure

```
claude-polymarket-trading/
├── polymarket_api.py    # Core API (trading, prices, orderbook)
├── cockpit.py           # Trading interface (preview, execute, display)
├── market_db.py         # Fast SQLite market lookups
├── TRADING_MEMORY.md    # Claude's learned patterns & preferences
├── CLAUDE.md            # Instructions for Claude Code
└── data/
    ├── .trading_config.json   # Your API credentials (gitignored)
    └── markets.db             # 1,330+ indexed markets
```

## Documentation

- [Installation Guide](docs/INSTALLATION.md) - Setup from scratch
- [About](docs/ABOUT.md) - Project background and philosophy
- [API Reference](docs/API.md) - All available functions

## Requirements

- Python 3.10+
- Claude Code CLI
- Polymarket account with API access
- `py-clob-client` package

## Safety Features

- **No execution without confirmation** - Every trade requires explicit "yes"
- **Preview tables** - See exact orders before they're placed
- **Position awareness** - Shows your holdings before selling
- **Rate limiting** - 0.1s delay between orders to avoid API limits

## Contributing

PRs welcome. Please read `CONTRIBUTING.md` first.

## License

MIT License - See `LICENSE` file.

## Disclaimer

This software is for educational purposes. Trading prediction markets involves risk.
Never trade more than you can afford to lose. This is not financial advice.

---

Built with Claude Code | [Documentation](docs/) | [Report Issues](https://github.com/yourusername/claude-polymarket-trading/issues)
