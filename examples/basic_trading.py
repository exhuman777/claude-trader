#!/usr/bin/env python3
"""
Basic Trading Example
=====================
Common trading operations with Claude Polymarket Cockpit.

This example demonstrates:
- Loading events from Polymarket URLs
- Viewing orderbooks
- Placing limit orders
- Placing market orders
- Checking positions
- Canceling orders

Prerequisites:
    python setup_wizard.py  # Configure credentials first

Usage:
    python examples/basic_trading.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def demo_event_loading():
    """Demonstrate loading an event."""
    print("""
━━━ LOADING EVENTS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

From Polymarket URL: https://polymarket.com/event/trump-2024

    from cockpit import show_event

    # Extract slug from URL
    print(show_event('trump-2024'))

Output:
    ┌─────────┬───────────────────────────────────────┬───────┬────────┐
    │ ID      │ Market                                │ YES   │ Volume │
    ├─────────┼───────────────────────────────────────┼───────┼────────┤
    │ 1234567 │ Trump wins 2024                       │ 52¢   │ $1.2M  │
    │ 1234568 │ Trump wins popular vote               │ 48¢   │ $450K  │
    └─────────┴───────────────────────────────────────┴───────┴────────┘
    """)


def demo_orderbook():
    """Demonstrate checking orderbook."""
    print("""
━━━ CHECKING ORDERBOOK ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    from polymarket_api import get_best_prices, get_orderbook

    # Quick price check
    prices = get_best_prices('1234567')
    print(f"Bid: {prices['best_bid']*100:.0f}¢")
    print(f"Ask: {prices['best_ask']*100:.0f}¢")
    print(f"Spread: {prices['spread']*100:.1f}¢")

    # Full orderbook
    book = get_orderbook('1234567')
    # Returns bids and asks with size at each price level
    """)


def demo_limit_order():
    """Demonstrate placing limit orders."""
    print("""
━━━ PLACING LIMIT ORDERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

With Claude Code (natural language):
    "buy 10 shares at 35 cents"
    "sell 5 shares at 60 cents"

With Python:
    from polymarket_api import place_order

    # Buy 10 YES shares at 35 cents
    result = place_order(
        market_id='1234567',
        side='BUY',
        price=0.35,
        size=10
    )
    print(result)  # {'status': 'matched', 'order_id': '0x...'}

    # Sell 5 YES shares at 60 cents
    result = place_order(
        market_id='1234567',
        side='SELL',
        price=0.60,
        size=5
    )
    """)


def demo_market_order():
    """Demonstrate market orders."""
    print("""
━━━ MARKET ORDERS (IMMEDIATE EXECUTION) ━━━━━━━━━━━━━━━━━━━━━━

With Claude Code:
    "market buy 10 shares"
    "sell all at market"

With Python:
    from polymarket_api import quick_buy, quick_sell

    # Buy at best ask (immediate)
    result = quick_buy('1234567', size=10)

    # Sell at best bid (immediate)
    result = quick_sell('1234567', size=5)

    # Or place at best price manually:
    prices = get_best_prices('1234567')
    place_order('1234567', 'BUY', prices['best_ask'], 10)
    """)


def demo_positions():
    """Demonstrate checking positions."""
    print("""
━━━ CHECKING POSITIONS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

With Claude Code:
    "show my positions"
    "what am I holding?"

With Python:
    from polymarket_api import get_positions, get_balances

    # Get USDC balance
    balance = get_balances()
    print(f"Balance: ${balance}")

    # Get all positions
    positions = get_positions()
    for pos in positions:
        print(f"{pos['market']}: {pos['size']} shares")
    """)


def demo_cancel_orders():
    """Demonstrate canceling orders."""
    print("""
━━━ CANCELING ORDERS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

With Claude Code:
    "cancel all orders"
    "cancel orders for market 1234567"

With Python:
    from polymarket_api import cancel_order, cancel_all_orders, show_orders

    # View open orders first
    show_orders()

    # Cancel specific order
    cancel_order('0xOrderId...')

    # Cancel ALL open orders
    cancel_all_orders()
    """)


def demo_preview_workflow():
    """Demonstrate the preview-confirm workflow."""
    print("""
━━━ PREVIEW-CONFIRM WORKFLOW (CLAUDE CODE) ━━━━━━━━━━━━━━━━━━━

1. User: "buy 10 at 35c"

2. Claude shows preview:
    ┌───────────┬─────────────────────────┬─────────┐
    │  Action   │        Details          │ Status  │
    ├───────────┼─────────────────────────┼─────────┤
    │ BUY YES   │ 10 @ 35¢ ($3.50)        │ pending │
    └───────────┴─────────────────────────┴─────────┘
    Confirm?

3. User: "yes"

4. Claude executes and shows result:
    ┌───────────┬─────────────────────────┬───────────┐
    │  Action   │        Details          │  Status   │
    ├───────────┼─────────────────────────┼───────────┤
    │ BUY YES   │ 10 @ 35¢ ($3.50)        │ ✓ matched │
    └───────────┴─────────────────────────┴───────────┘

This workflow is enforced in the cockpit - no trades execute without confirmation!
    """)


def main():
    """Run all demos."""
    print("""
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE POLYMARKET TRADING - BASIC EXAMPLES                 │
└─────────────────────────────────────────────────────────────┘
    """)

    demo_event_loading()
    demo_orderbook()
    demo_limit_order()
    demo_market_order()
    demo_positions()
    demo_cancel_orders()
    demo_preview_workflow()

    print("""
━━━ NEXT STEPS ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Try ladder strategies:
   python examples/ladder_strategy.py

2. Set up spike detection:
   python examples/spike_detector.py

3. Start Claude Code and trade:
   claude
   "search trump markets"
   "buy 10 at 35c"
    """)


if __name__ == "__main__":
    main()
