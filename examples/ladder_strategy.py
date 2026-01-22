#!/usr/bin/env python3
"""
Ladder Strategy Example
=======================
Advanced trading with multiple orders at different price levels.

Ladders are used to:
- Accumulate positions gradually (buy ladder)
- Exit positions at multiple prices (sell ladder)
- Capture price volatility

Prerequisites:
    python setup_wizard.py  # Configure credentials first

Usage:
    python examples/ladder_strategy.py
"""

import sys
import time
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def explain_ladder_concept():
    """Explain ladder trading."""
    print("""
┌─────────────────────────────────────────────────────────────┐
│  LADDER TRADING EXPLAINED                                   │
└─────────────────────────────────────────────────────────────┘

A ladder is multiple orders at different price levels:

BUY LADDER (Accumulating)
─────────────────────────
Place orders BELOW current price, wait for dips.

    Current price: 50¢

    Order 1: BUY 10 @ 48¢
    Order 2: BUY 10 @ 46¢
    Order 3: BUY 10 @ 44¢
    Order 4: BUY 10 @ 42¢
    Order 5: BUY 10 @ 40¢

    → If price drops to 44¢, you've accumulated 30 shares
      at average price of 46¢


SELL LADDER (Distributing)
──────────────────────────
Place orders ABOVE current price, capture rises.

    Current price: 50¢

    Order 1: SELL 10 @ 52¢
    Order 2: SELL 10 @ 54¢
    Order 3: SELL 10 @ 56¢
    Order 4: SELL 10 @ 58¢
    Order 5: SELL 10 @ 60¢

    → If price rises to 56¢, you've sold 30 shares
      at average price of 54¢
    """)


def demo_place_ladder():
    """Demonstrate placing ladder orders."""
    print("""
━━━ PLACING LADDERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WITH CLAUDE CODE (NATURAL LANGUAGE):

    "create buy ladder from 40c to 48c, 5 orders, 10 shares each"

    "sell ladder from 52c to 60c for my trump shares"

    "ladder 50 shares from 12c to 18c with 1c increments"


WITH PYTHON:

    from polymarket_api import place_ladder

    # Buy ladder: 5 orders from 48¢ down to 40¢
    # (BUY ladders go HIGH → LOW)
    place_ladder(
        market_id='1234567',
        side='BUY',
        start_price=0.48,  # Start high
        end_price=0.40,    # End low
        num_orders=5,
        shares_per=10
    )

    # Sell ladder: 5 orders from 52¢ up to 60¢
    # (SELL ladders go LOW → HIGH)
    place_ladder(
        market_id='1234567',
        side='SELL',
        start_price=0.52,  # Start low
        end_price=0.60,    # End high
        num_orders=5,
        shares_per=10
    )
    """)


def demo_granular_ladder():
    """Demonstrate 1-cent increment ladders."""
    print("""
━━━ GRANULAR LADDERS (1¢ INCREMENTS) ━━━━━━━━━━━━━━━━━━━━━━━━━

For volatile markets, use 1¢ increments to catch every move:

EXAMPLE: Elon Tweet Market Sell Ladder

    You hold: 700 shares of "360-379 tweets"
    Current price: 11¢
    Strategy: Sell as price rises

    Claude Code:
    "create sell ladder from 12c to 18c, 100 shares per order"

    Result:
    ┌──────────┬─────────────────────────────────────────┬─────────┐
    │ Market   │ Details                                 │ Status  │
    ├──────────┼─────────────────────────────────────────┼─────────┤
    │ 360-379  │ SELL 100 @ 12¢                          │ ✓ live  │
    │ 360-379  │ SELL 100 @ 13¢                          │ ✓ live  │
    │ 360-379  │ SELL 100 @ 14¢                          │ ✓ live  │
    │ 360-379  │ SELL 100 @ 15¢                          │ ✓ live  │
    │ 360-379  │ SELL 100 @ 16¢                          │ ✓ live  │
    │ 360-379  │ SELL 100 @ 17¢                          │ ✓ live  │
    │ 360-379  │ SELL 100 @ 18¢                          │ ✓ live  │
    └──────────┴─────────────────────────────────────────┴─────────┘
    7 orders placed, 700 shares total

    → Captures profit at each 1¢ price movement
    """)


def demo_manual_ladder():
    """Show how to build a ladder manually."""
    print("""
━━━ BUILDING LADDERS MANUALLY ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For custom logic, build ladders with a loop:

    from polymarket_api import place_order
    import time

    market_id = '1234567'
    shares_per_order = 100

    # Sell ladder: 12¢ to 18¢ in 1¢ increments
    prices = [0.12, 0.13, 0.14, 0.15, 0.16, 0.17, 0.18]

    results = []
    for price in prices:
        result = place_order(market_id, 'SELL', price, shares_per_order)
        results.append(result)
        time.sleep(0.1)  # Small delay to avoid rate limits

    # Check results
    matched = sum(1 for r in results if r.get('status') == 'matched')
    live = sum(1 for r in results if r.get('status') == 'live')
    print(f"✓ {matched} matched, {live} live")


VARIABLE SIZE LADDER:

    # More shares at better prices
    ladder = [
        (0.40, 20),   # 20 shares @ 40¢
        (0.38, 30),   # 30 shares @ 38¢
        (0.36, 50),   # 50 shares @ 36¢
        (0.34, 70),   # 70 shares @ 34¢
        (0.32, 100),  # 100 shares @ 32¢
    ]

    for price, size in ladder:
        place_order(market_id, 'BUY', price, size)
        time.sleep(0.1)
    """)


def demo_grid_strategy():
    """Demonstrate grid trading."""
    print("""
━━━ GRID STRATEGY (BUY + SELL LADDERS) ━━━━━━━━━━━━━━━━━━━━━━━

Grid trading places BOTH buy and sell ladders around current price:

    Current price: 50¢

    BUY LADDER (below):     SELL LADDER (above):
    ┌─────────────────┐     ┌─────────────────┐
    │ BUY 10 @ 48¢    │     │ SELL 10 @ 52¢   │
    │ BUY 10 @ 46¢    │     │ SELL 10 @ 54¢   │
    │ BUY 10 @ 44¢    │     │ SELL 10 @ 56¢   │
    │ BUY 10 @ 42¢    │     │ SELL 10 @ 58¢   │
    │ BUY 10 @ 40¢    │     │ SELL 10 @ 60¢   │
    └─────────────────┘     └─────────────────┘

    → Profits from price movement in EITHER direction
    → Requires existing position for sell side


IMPLEMENTATION:

    # Grid around 50¢ current price
    center = 0.50
    spread = 0.02  # 2¢ increments
    levels = 5
    size = 10

    # Buy ladder
    for i in range(1, levels + 1):
        price = center - (spread * i)
        place_order(market_id, 'BUY', price, size)

    # Sell ladder (if you have shares)
    for i in range(1, levels + 1):
        price = center + (spread * i)
        place_order(market_id, 'SELL', price, size)
    """)


def main():
    """Run ladder strategy demos."""
    print("""
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE POLYMARKET TRADING - LADDER STRATEGIES              │
└─────────────────────────────────────────────────────────────┘
    """)

    explain_ladder_concept()
    demo_place_ladder()
    demo_granular_ladder()
    demo_manual_ladder()
    demo_grid_strategy()

    print("""
━━━ TIPS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Start with wider spreads (2-5¢) in low-volatility markets
2. Use 1¢ increments for active/volatile markets
3. Monitor your orders - cancel unfilled ones before resolution
4. Consider your total exposure across all ladder levels
5. Use Claude Code for quick ladder creation:
   "create sell ladder from 12c to 18c, 100 shares each"
    """)


if __name__ == "__main__":
    main()
