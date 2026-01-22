# Trading Playbook - Proven Patterns

## Auto-Trading (auto.py)

```python
from auto import *

# Follow whale trades > $5K (dry run first!)
whale_follow(min_usd=5000, bet=5, max_trades=5)

# Real trades
whale_follow(min_usd=5000, bet=5, dry_run=False)

# Top volume markets
top_volume_bet(bet=5, count=3)

# Elon/tweet markets
elon_volume_bet(bet=5, count=3)

# Find opportunities (high vol, low price)
scan_opportunities(min_volume=500000, max_price=0.25)
```

## Quick Lookups

### Find Market ID from Name/Slug
```python
# From slug (fastest)
resp = requests.get(f'https://gamma-api.polymarket.com/markets?slug={slug}')
market_id = resp.json()[0]['id']

# From condition ID
resp = requests.get(f'https://gamma-api.polymarket.com/markets?condition_id={cond_id}')
```

### Top Volume Markets
```python
url = 'https://gamma-api.polymarket.com/markets?limit=20&order=volume24hr&ascending=false&active=true&closed=false'
# Filter: price > 2¢ and < 98¢ to skip resolved
```

### Recent Large Trades
```python
resp = requests.get('https://data-api.polymarket.com/trades?limit=200')
# Has: side, price, size, title, conditionId, slug
# USD value = price * size
```

## Order Management

### Find Orders by Market
```python
orders = get_open_orders()
# Group by asset_id prefix (first 20 chars)
# Known prefixes:
#   81376898... = Elon 420-439
#   66924366... = Elon 380-399
#   62845222... = Elon 400-419
```

### Cancel + Replace Pattern
```python
# 1. Get orders by asset prefix
orders_target = [o for o in orders if o['asset_id'].startswith('PREFIX')]
# 2. Cancel each with 0.3s delay
for o in orders_target:
    cancel_order(o['id'])
    time.sleep(0.3)
# 3. Wait 3s for settlement
# 4. Place new orders
```

## Market Buy ($X worth)
```python
prices = get_best_prices(market_id)
ask = prices['best_ask']
shares = int(budget / ask)
place_order(market_id, 'BUY', ask, shares)
```

## Display Formats
```python
# Price: 35¢ not 0.35
f"{price*100:.0f}¢"

# Volume
if vol >= 1_000_000: f"${vol/1_000_000:.1f}M"
elif vol >= 1_000: f"${vol/1_000:.0f}K"
```

## API Endpoints (Working)

| Purpose | Endpoint |
|---------|----------|
| Market by ID | `gamma-api.polymarket.com/markets/{id}` |
| Market by slug | `gamma-api.polymarket.com/markets?slug=X` |
| Top volume | `gamma-api.polymarket.com/markets?order=volume24hr` |
| Recent trades | `data-api.polymarket.com/trades?limit=N` |
| Event by slug | `gamma-api.polymarket.com/events?slug=X` |
| Orderbook | `clob.polymarket.com/book?token_id=X` |

## Elon Market IDs (Jan 16-23, 2026)
```
360-379: 1172391 (asset: ?)
380-399: 1172392 (asset: 66924366...)
400-419: 1172393 (asset: 62845222...)
420-439: 1172394 (asset: 81376898...)
```

## Common Errors
- "not enough balance/allowance" → reduce size, shares locked in pending orders
- Empty orderbook → market resolved or inactive
- Stale positions API → trust user over API (1-5 min delay)
