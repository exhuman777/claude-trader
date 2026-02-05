# AGENTS.md

## Overview

Natural language trading on Polymarket. Parse user intent and execute trades with confirmation flow.

## Commands

```bash
# Setup
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python setup_wizard.py  # Credentials

# Run
python interactive.py   # Interactive mode
python trade.py         # Direct CLI
python cockpit_web.py   # Web cockpit
```

## Trading Flow

1. **Preview** - Show what will happen (no execution)
2. **Confirm** - Wait for "yes", "confirm", "go"
3. **Execute** - Only after explicit confirmation
4. **Report** - Show results

```python
from cockpit import preview_buy, execute_pending
print(preview_buy('1230810', 10, 0.35))
# User says "yes"
print(execute_pending())
```

## File Map

| File | Purpose |
|------|---------|
| `polymarket_api.py` | Core API functions |
| `cockpit.py` | Display helpers, preview/confirm |
| `interactive.py` | Interactive CLI |
| `trade.py` | Direct CLI commands |
| `auto.py` | Automation (whale following) |
| `crypto.py` | Key encryption |

## Price Format

- Internal: `0.35` (decimal)
- Display: `35¢` (cents)
- NEVER use percentages

## Code Style

- Python: `ruff format` + `ruff check`
- Always preview before execute
- Handle API errors gracefully

## Don't

- Execute without user confirmation
- Commit credentials (`data/.trading_config.json`)
- Spam APIs (rate limits)
- Confuse price (0.35) with percentage (35%)

## Related

- `~/Rufus/projects/yesno-events/` - Trading terminal
- `~/Rufus/projects/polymarket-python/` - API client
