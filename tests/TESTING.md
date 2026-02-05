# Trading Infrastructure Testing Guide

## Quick Test

```bash
# Full automated test suite
~/Rufus/scripts/test-trading.sh

# Or manually:
cd ~/Rufus/projects/claude-trader
source .venv/bin/activate
python tests/test_full_stack.py
```

---

## Test Phases

### Phase 1: Environment
Verifies setup is correct:
- Python version (≥3.10)
- Required files exist
- Config file valid
- Dependencies installed

### Phase 2: API Connectivity
Tests network access to Polymarket:
- Gamma API (market data)
- CLOB API (trading)
- Data API (trades, positions)

### Phase 3: Market Data
Tests data fetching:
- Top volume markets
- Market search
- Price fetching
- Orderbook retrieval
- Recent trades

### Phase 4: Account
Tests authenticated operations:
- CLOB client initialization
- Balance check
- Positions fetch
- Open orders fetch

### Phase 5: Trading Logic (Dry Run)
Tests order building without execution:
- Order argument validation
- Price formatting
- Ladder price calculation
- Market buy simulation

### Phase 6: Automation (Dry Run)
Tests automated strategies:
- Whale follow (dry run)
- Top volume bet (dry run)
- Opportunity scanner
- Trader profile lookup

### Phase 7: Integration
End-to-end flows:
- Full research flow
- Full automation flow
- Display functions

---

## Manual Testing Checklist

### 1. API Connection Test
```bash
cd ~/Rufus/projects/claude-trader && source .venv/bin/activate
python -c "
from polymarket_api import get_balances, get_positions, get_open_orders
print('Balance:', get_balances())
print('Positions:', len(get_positions()))
print('Orders:', len(get_open_orders()))
"
```

### 2. Market Data Test
```bash
python -c "
from polymarket_api import show_event
show_event('trump-cabinet-confirmations')  # Or any active event slug
"
```

### 3. Orderbook Test
```bash
python -c "
from polymarket_api import show_orderbook
from auto import fetch_top_volume
markets = fetch_top_volume(1)
if markets:
    show_orderbook(str(markets[0]['id']))
"
```

### 4. Whale Follow Test (Dry Run)
```bash
python -c "
from auto import whale_follow
whale_follow(min_usd=5000, bet=5, max_trades=3, dry_run=True)
"
```

### 5. Top Volume Test (Dry Run)
```bash
python -c "
from auto import top_volume_bet
top_volume_bet(bet=5, count=3, dry_run=True)
"
```

### 6. Opportunity Scanner
```bash
python -c "
from auto import scan_opportunities
scan_opportunities(min_volume=100000, max_price=0.30)
"
```

---

## Live Trading Test (USE CAUTION)

**Only run after all dry-run tests pass.**

### Minimal Live Test ($1 bet)
```python
from polymarket_api import *
from auto import fetch_top_volume

# Find a liquid market
markets = fetch_top_volume(10)
for m in markets:
    prices = m.get('outcomePrices', '[]')
    if isinstance(prices, str):
        import json
        prices = json.loads(prices) if prices else [0.5]
    price = float(prices[0]) if prices else 0.5

    # Find market with decent spread
    if 0.20 < price < 0.80:
        market_id = str(m['id'])
        print(f"Testing with: {m['question'][:50]}")
        print(f"Market ID: {market_id}")
        print(f"Price: {price*100:.0f}¢")

        # Get orderbook
        best = get_best_prices(market_id)
        print(f"Bid: {best['best_bid']*100:.0f}¢, Ask: {best['best_ask']*100:.0f}¢")

        # CONFIRM before proceeding
        confirm = input("Place $1 test order? (yes/no): ")
        if confirm.lower() == 'yes':
            # Place at best ask (will fill immediately)
            result = place_order(market_id, 'BUY', best['best_ask'], 1)
            print(f"Result: {result}")
        break
```

---

## Interpreting Results

### All Passed
```
✓ Passed:  28
✗ Failed:  0
⊘ Skipped: 2
```
Everything works. Skipped tests are OK (usually means no matching data).

### Some Failed
Check the failure messages:
- **Environment failures**: Fix dependencies or config
- **API failures**: Check internet connection
- **Account failures**: Check credentials in `.trading_config.json`
- **Trading failures**: May need to refresh token IDs

### Common Issues

| Error | Cause | Fix |
|-------|-------|-----|
| `Config not found` | Missing config file | Run `python setup_wizard.py` |
| `py-clob-client not installed` | Missing dependency | `pip install py-clob-client` |
| `Status 403` | Rate limited | Wait 1 min, retry |
| `No token IDs` | Market doesn't have CLOB | Skip this market |
| `not enough balance` | Insufficient USDC | Deposit funds |

---

## Continuous Testing

Add to crontab for daily health check:
```bash
# Run tests daily at 9 AM
0 9 * * * ~/Rufus/scripts/test-trading.sh >> ~/Rufus/logs/trading-tests.log 2>&1
```

---

## Results File

Test results saved to: `tests/last_run.json`

```json
{
  "timestamp": "2026-01-31T12:00:00",
  "summary": {
    "passed": 28,
    "failed": 0,
    "skipped": 2
  },
  "tests": [
    {"name": "Python version >= 3.10", "phase": "environment", "status": "PASS"},
    ...
  ]
}
```

---

*Last updated: 2026-01-31*
