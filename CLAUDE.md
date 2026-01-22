# CLAUDE.md

> Instructions for Claude Code and other AI agents working with this codebase.

## What is this?

Claude Trader enables natural language trading on Polymarket. You parse user intent and execute trades using the provided functions.

## Quick start

```bash
# Setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run setup wizard for credentials
python setup_wizard.py

# Interactive mode
python interactive.py
```

## Core functions (polymarket_api.py)

```python
from polymarket_api import *

# View event
show_event('trump-election-2024')

# Place order
place_order('1230810', 'BUY', 0.35, 10)  # BUY 10 @ 35¢

# Quick market orders
quick_buy('1230810', size=5)
quick_sell('1230810', size=5)

# Ladder orders
place_ladder('1230810', 'BUY', 0.40, 0.35, 5, 10)  # 5 orders, 40¢→35¢

# Manage orders
show_orders()
cancel_order('0x123...')
cancel_all_orders()

# Account
get_positions()
get_balances()
```

## Trading flow

1. **Always preview first** - Show user what will happen
2. **Wait for confirmation** - "yes", "confirm", "go"
3. **Execute** - Only after explicit confirmation
4. **Show results** - Confirm what happened

```python
from cockpit import *

# Step 1: Preview (no execution)
print(preview_buy('1230810', 10, 0.35))

# Step 2: User says "yes"

# Step 3: Execute
print(execute_pending())
```

## Price format

- Internal: `0.35` (decimal)
- Display: `35¢` (cents)
- NEVER use percentages

```python
price = 0.35
display = f"{price*100:.0f}¢"  # "35¢"
```

## Ladder direction

**BUY ladders**: HIGH → LOW (waiting for price to drop)
```python
place_ladder(id, 'BUY', 0.40, 0.35, 5, 10)
# Orders at: 40¢, 39¢, 38¢, 37¢, 36¢, 35¢
```

**SELL ladders**: LOW → HIGH (waiting for price to rise)
```python
place_ladder(id, 'SELL', 0.60, 0.70, 5, 10)
# Orders at: 60¢, 62¢, 64¢, 66¢, 68¢, 70¢
```

## File map

| File | Purpose |
|------|---------|
| `polymarket_api.py` | Core API functions - import this |
| `cockpit.py` | Display helpers, preview/confirm flow |
| `interactive.py` | Interactive CLI mode |
| `trade.py` | Direct CLI commands |
| `auto.py` | Automation (whale following, etc.) |
| `setup_wizard.py` | Credential setup |
| `crypto.py` | Key encryption |
| `PLAYBOOK.md` | Proven patterns, quick reference |

## Automation (auto.py)

```python
from auto import *

# Follow whale trades
whale_follow(min_usd=5000, bet=5, only_profitable=True)

# Top volume markets
top_volume_bet(bet=5, count=3)

# Sports whales
sport_whale_hunt(bet=5, count=2, min_usd=1000)
```

## Config

Credentials in `data/.trading_config.json`:
```json
{
  "private_key": "0x...",
  "api_key": "...",
  "api_secret": "...",
  "passphrase": "...",
  "funder": "0x..."
}
```

## API endpoints

```python
# Gamma (market data)
"https://gamma-api.polymarket.com/markets"
"https://gamma-api.polymarket.com/events"

# CLOB (trading)
"https://clob.polymarket.com/book"
"https://clob.polymarket.com/orders"

# Data
"https://data-api.polymarket.com/trades"
"https://data-api.polymarket.com/profile/{address}"
```

## Do

- Always preview before executing
- Wait for user confirmation
- Use decimal prices (0.35 not 35)
- Handle API errors gracefully

## Don't

- Don't execute without confirmation
- Don't commit credentials
- Don't spam APIs (rate limits)
- Don't confuse price (0.35) with percentage (35%)
