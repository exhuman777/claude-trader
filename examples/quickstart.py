#!/usr/bin/env python3
"""
Quickstart Example
==================
The simplest possible example to get trading.

Prerequisites:
    1. pip install py-clob-client
    2. Set up credentials in data/.trading_config.json or environment

Usage:
    python examples/quickstart.py
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config


def check_environment() -> bool:
    """Verify required credentials are configured."""
    config = Config.load()

    if not config.is_configured():
        print("""
┌─────────────────────────────────────────────────────────────┐
│  SETUP REQUIRED                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Missing credentials. Set up in one of these ways:         │
│                                                             │
│  Option 1: Environment variables                            │
│    export POLY_PRIVATE_KEY="your_private_key"              │
│    export POLY_FUNDER="0xYourWalletAddress"                │
│                                                             │
│  Option 2: Run setup wizard                                 │
│    python setup_wizard.py                                   │
│                                                             │
│  Option 3: Create data/.trading_config.json                │
│    {                                                        │
│      "private_key": "your_key",                            │
│      "funder": "0xYourAddress",                            │
│      "host": "https://clob.polymarket.com",                │
│      "chain_id": 137,                                      │
│      "signature_type": 2                                   │
│    }                                                        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
        """)
        return False

    print(f"✓ Credentials loaded")
    print(f"  Wallet: {config.funder[:10]}...{config.funder[-4:]}")
    return True


def main():
    """Quickstart demo."""
    print("""
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE POLYMARKET TRADING - QUICKSTART                     │
└─────────────────────────────────────────────────────────────┘
    """)

    # Step 1: Check environment
    print("Step 1: Checking credentials...")
    if not check_environment():
        return

    # Step 2: Import trading functions
    print("\nStep 2: Loading trading module...")
    try:
        from polymarket_api import (
            get_balances,
            search_markets,
            get_best_prices,
        )
        print("✓ Trading module loaded")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("  Make sure py-clob-client is installed:")
        print("  pip install py-clob-client")
        return

    # Step 3: Check balance
    print("\nStep 3: Checking balance...")
    try:
        balance = get_balances()
        if balance:
            print(f"✓ Balance: {balance}")
        else:
            print("  Could not fetch balance (may still work)")
    except Exception as e:
        print(f"  Balance check failed: {e}")

    # Step 4: Search for a market
    print("\nStep 4: Searching markets...")
    try:
        markets = search_markets("trump", limit=3)
        print(f"✓ Found {len(markets)} markets")
        for m in markets[:3]:
            title = m.get('question', m.get('title', 'Unknown'))[:50]
            print(f"  - {title}...")
    except Exception as e:
        print(f"  Search failed: {e}")

    # Step 5: Get prices
    print("\nStep 5: Getting sample prices...")
    if markets:
        try:
            market_id = markets[0].get('id') or markets[0].get('condition_id')
            if market_id:
                prices = get_best_prices(str(market_id))
                if prices:
                    bid = prices.get('best_bid', 0)
                    ask = prices.get('best_ask', 0)
                    print(f"✓ Sample market prices:")
                    print(f"  Bid: {bid*100:.0f}¢")
                    print(f"  Ask: {ask*100:.0f}¢")
        except Exception as e:
            print(f"  Price fetch failed: {e}")

    # Done
    print("""
┌─────────────────────────────────────────────────────────────┐
│  NEXT STEPS                                                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. View markets:                                           │
│     from cockpit import show_event                          │
│     print(show_event('trump-2024'))                         │
│                                                             │
│  2. Place an order (with Claude Code):                      │
│     "buy 10 shares at 35 cents"                             │
│                                                             │
│  3. Try more examples:                                      │
│     python examples/basic_trading.py                        │
│     python examples/ladder_strategy.py                      │
│     python examples/spike_detector.py                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    """)


if __name__ == "__main__":
    main()
