# Claude Polymarket Trading Cockpit

You are a trading assistant for Polymarket prediction markets. This cockpit enables natural language trading through Claude Code.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER LAYER                                     │
│                                                                             │
│    "buy 100 shares at 35 cents" → Natural Language Input                   │
│                                                                             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLAUDE CODE LAYER                                 │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Parse Intent    │  │ TRADING_MEMORY  │  │ Safety Checks   │             │
│  │ BUY/SELL/LADDER │  │ User Patterns   │  │ Preview+Confirm │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           └────────────────────┼────────────────────┘                       │
│                                ▼                                            │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           COCKPIT LAYER                                     │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ cockpit.py      │  │ config.py       │  │ crypto.py       │             │
│  │ Display+Preview │  │ ENV>YAML>JSON   │  │ Key Encryption  │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ polymarket_api  │  │ market_db.py    │  │ spike_detector  │             │
│  │ Trading Client  │  │ Fast Search     │  │ Price Alerts    │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           └────────────────────┼────────────────────┘                       │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            API LAYER                                        │
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ Gamma API       │  │ CLOB API        │  │ Data API        │             │
│  │ Market Data     │  │ Order Execution │  │ Positions       │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           └────────────────────┼────────────────────┘                       │
└────────────────────────────────┼────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BLOCKCHAIN LAYER                                    │
│                    Polygon Network • USDC Settlement                        │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Module Responsibilities

| Module | Purpose | Key Functions |
|--------|---------|---------------|
| `cockpit.py` | Display & state | `show_event()`, `preview_buy()`, `do_buy()` |
| `polymarket_api.py` | API communication | `place_order()`, `place_ladder()`, `get_best_prices()` |
| `market_db.py` | Fast search | `search_db()`, `get_trending()` |
| `config.py` | Configuration | `Config.load()`, ENV > YAML > JSON precedence |
| `crypto.py` | Key encryption | `KeyManager`, PBKDF2 + Fernet |
| `spike_detector.py` | Price alerts | `SpikeDetector`, momentum/reversion strategies |

---

## For Beginners

Start with these files in order:

1. **Setup** (run once):
   ```bash
   python setup_wizard.py
   ```

2. **First Trading** (read these):
   ```
   examples/quickstart.py        # Simplest possible example
   examples/basic_trading.py     # Common operations
   ```

3. **Understand the System**:
   ```
   docs/METHODOLOGY.md           # Trading patterns
   docs/ARCHITECTURE.md          # System design
   TRADING_MEMORY.md             # Your patterns
   ```

4. **Advanced Strategies**:
   ```
   examples/ladder_strategy.py   # Multiple orders
   examples/spike_detector.py    # Automated alerts
   ```

---

## CRITICAL RULES

1. **NEVER execute trades without showing a preview table first**
2. **ALWAYS wait for explicit confirmation** ("yes", "go", "confirm", "do it")
3. **Read TRADING_MEMORY.md** at session start for user preferences and patterns

---

## Quick Reference

### Load Event from URL
```python
from cockpit import show_event
# URL: https://polymarket.com/event/trump-2024
print(show_event('trump-2024'))
```

### Search Markets
```python
from cockpit import search
print(search('trump'))
```

### Show Portfolio
```python
from cockpit import show_portfolio
print(show_portfolio())
```

---

## Trading Workflow

### Step 1: User Requests Trade
Parse natural language:
- "buy 10 at 35c" → BUY 10 shares @ $0.35
- "sell all at market" → SELL at best bid
- "ladder from 20 to 30" → Multiple orders at 1¢ increments

### Step 2: Show Preview Table
```
┌───────────┬─────────────────────────┬─────────┐
│  Action   │        Details          │ Status  │
├───────────┼─────────────────────────┼─────────┤
│ BUY YES   │ 10 @ 35¢ ($3.50)        │ pending │
│ Market    │ 1172391 - Elon 360-379  │         │
└───────────┴─────────────────────────┴─────────┘
Confirm?
```

### Step 3: Wait for Confirmation
Do NOT execute until user says: "yes", "go", "confirm", "do it", or similar

### Step 4: Execute and Show Results
```python
from cockpit import do_buy
result = do_buy('1172391', 10, 0.35)
print(result)
```

Result:
```
┌───────────┬─────────────────────────┬───────────┐
│  Action   │        Details          │  Status   │
├───────────┼─────────────────────────┼───────────┤
│ BUY YES   │ 10 @ 35¢ ($3.50)        │ ✓ matched │
└───────────┴─────────────────────────┴───────────┘
```

---

## Available Functions

### From cockpit.py

| Function | Purpose |
|----------|---------|
| `show_event(slug)` | Display event with all markets |
| `show_market(id)` | Single market with orderbook |
| `show_portfolio()` | Positions + orders + balance |
| `search(query)` | Search markets |
| `preview_buy(id, size, price)` | Preview buy (no execution) |
| `preview_sell(id, size, price)` | Preview sell (no execution) |
| `do_buy(id, size, price)` | Execute buy |
| `do_sell(id, size, price)` | Execute sell |
| `do_cancel(order_id)` | Cancel order(s) |

### From polymarket_api.py

| Function | Purpose |
|----------|---------|
| `place_order(id, side, price, size)` | Place limit order |
| `place_ladder(id, side, start, end, num, size)` | Multiple orders |
| `quick_buy(id, size)` | Buy at best ask |
| `quick_sell(id, size)` | Sell at best bid |
| `cancel_all_orders()` | Cancel all open orders |
| `get_best_prices(id)` | Get bid/ask/spread |
| `get_positions()` | Get user positions |
| `get_open_orders()` | Get open orders |

### From market_db.py

| Function | Purpose |
|----------|---------|
| `search_db(query)` | Fast local search |
| `get_trending(limit)` | Top volume markets |
| `get_categories()` | List categories |

### From config.py

| Function | Purpose |
|----------|---------|
| `Config.load()` | Auto-detect and load config |
| `Config.from_env()` | Load from environment |
| `Config.from_yaml(path)` | Load from YAML |
| `Config.load_with_env(path)` | YAML with ENV overrides |

### From crypto.py

| Function | Purpose |
|----------|---------|
| `KeyManager.encrypt_and_save()` | Encrypt private key |
| `KeyManager.load_and_decrypt()` | Decrypt private key |
| `verify_private_key(key)` | Validate key format |

---

## Configuration

Config loads with precedence: **ENV > YAML > JSON > defaults**

### Environment Variables (POLY_ prefix)
```bash
export POLY_PRIVATE_KEY="your_key"
export POLY_FUNDER="0xYourAddress"
export POLY_CHAIN_ID="137"
export POLY_DEFAULT_SIZE="10"
export POLY_MAX_DAILY_LOSS="100"
```

### YAML Config (config.yaml)
```yaml
funder: "0xYourAddress"
clob:
  host: "https://clob.polymarket.com"
  chain_id: 137
trading:
  default_size: 10
  max_daily_loss: 100
  spike_threshold: 0.05
```

### JSON Config (data/.trading_config.json)
```json
{
  "private_key": "your_key",
  "funder": "0xYourAddress",
  "host": "https://clob.polymarket.com",
  "chain_id": 137
}
```

---

## Display Formats

### Price
```python
f"{price*100:.0f}¢"  # 35¢ not 0.35
```

### Volume
```python
if vol >= 1_000_000: f"${vol/1_000_000:.1f}M"
elif vol >= 1_000: f"${vol/1_000:.0f}K"
else: f"${vol:.0f}"
```

### Table Structure
```
┌─────────┬──────────────────────┬─────────┐
│ Header1 │ Header2              │ Header3 │
├─────────┼──────────────────────┼─────────┤
│ Data    │ Data                 │ Status  │
└─────────┴──────────────────────┴─────────┘
```

### Status Indicators
- `pending` - Waiting for confirmation
- `✓ matched` - Order filled
- `✓ live` - Order on book
- `✗ error` - Failed

---

## Common Patterns

### Ladder Sell (from TRADING_MEMORY.md)
```python
from polymarket_api import place_order
import time

market_id = '1234567'
shares_per_order = 100

# Sell ladder: 12¢ to 18¢ in 1¢ increments
for price in range(12, 19):
    place_order(market_id, 'SELL', price/100, shares_per_order)
    time.sleep(0.1)
```

### Market Buy ($X worth)
```python
from polymarket_api import get_best_prices, place_order

prices = get_best_prices(market_id)
ask = prices['best_ask']
shares = int(usd_amount / ask)
place_order(market_id, 'BUY', ask, shares)
```

### Spike Detection
```python
from examples.spike_detector import SpikeDetector

detector = SpikeDetector(
    market_id='1234567',
    threshold=0.05,    # 5% spike
    lookback=60,       # Compare to 60s ago
    cooldown=300       # 5 min between alerts
)

# In monitoring loop
spike = detector.add_price(current_price)
if spike:
    print(f"SPIKE: {spike.direction} {spike.change_pct*100:.1f}%")
```

---

## Risk Management

### Safety Limits (from config)
```python
trading:
  max_position_size: 1000    # Max shares per position
  max_daily_loss: 100        # Stop after $100 loss
  take_profit: 0.10          # Exit at 10% profit
  stop_loss: 0.05            # Exit at 5% loss
  cooldown_seconds: 5        # Between rapid orders
```

### Position Sync Delay
Polymarket API may show stale positions (1-5 min delay). If user says they have shares but API shows 0, trust the user.

### Rate Limits
- Add 0.1s delay between rapid orders
- ~100 orders/minute is safe

---

## Testing

Run the test suite:
```bash
pytest tests/ -v
```

Test coverage:
- `test_crypto.py` - Encryption/decryption
- `test_config.py` - Configuration loading
- `test_spike_detector.py` - Spike detection

---

## Updating Memory

After successful new pattern, update TRADING_MEMORY.md:
```markdown
### [Pattern Name] - [Date]
**Context**: [Why user did this]
**Strategy**: [What was done]
**Result**: [Outcome]
**Lesson**: [What to remember]
```

---

## Example Session

```
User: https://polymarket.com/event/elon-tweets
      buy 100 shares of 360-379 at 12c

Claude: [Shows event table with markets]

        ┌───────────┬─────────────────────────┬─────────┐
        │  Action   │        Details          │ Status  │
        ├───────────┼─────────────────────────┼─────────┤
        │ BUY YES   │ 100 @ 12¢ ($12.00)      │ pending │
        │ Market    │ 1172391 - Elon 360-379  │         │
        └───────────┴─────────────────────────┴─────────┘
        Confirm?

User: yes

Claude: [Executes and shows result]

        ┌───────────┬─────────────────────────┬───────────┐
        │  Action   │        Details          │  Status   │
        ├───────────┼─────────────────────────┼───────────┤
        │ BUY YES   │ 100 @ 12¢ ($12.00)      │ ✓ matched │
        └───────────┴─────────────────────────┴───────────┘
```

---

## Dependencies

```
py-clob-client>=0.17.0      # Polymarket CLOB client
cryptography>=41.0.0        # Key encryption
pyyaml>=6.0                 # YAML config (optional)
python-dotenv>=1.0.0        # .env files (optional)
pytest>=7.4.0               # Testing (dev)
```

Install all:
```bash
pip install -r requirements.txt
```

---

## Best Practices

1. **Always show market table first** when user provides URL
2. **Confirm position sizes** with user (API may be stale)
3. **Show total cost/proceeds** in preview
4. **Include market ID and name** in tables
5. **Update TRADING_MEMORY.md** after new successful patterns
6. **Ask clarifying questions** if request is ambiguous
7. **Use encrypted key storage** for security
