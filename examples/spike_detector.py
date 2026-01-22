#!/usr/bin/env python3
"""
Spike Detector Example
======================
Monitor markets for sudden price movements and alert/trade automatically.

A "spike" is a significant price movement (default: 5%+) within a short time.
This can indicate:
- Breaking news affecting the market
- Large order execution
- Market sentiment shift

Prerequisites:
    python setup_wizard.py  # Configure credentials first

Usage:
    python examples/spike_detector.py [--market MARKET_ID] [--threshold 0.05]
"""

import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class PricePoint:
    """Single price observation."""
    timestamp: datetime
    price: float
    bid: float
    ask: float


@dataclass
class SpikeEvent:
    """Detected price spike."""
    market_id: str
    old_price: float
    new_price: float
    change_pct: float
    direction: str  # "UP" or "DOWN"
    timestamp: datetime


@dataclass
class SpikeDetector:
    """
    Monitors a market for price spikes.

    Attributes:
        market_id: Market to monitor
        threshold: Minimum % change to trigger (default: 5%)
        lookback: Seconds of history to compare (default: 60)
        cooldown: Seconds between alerts (default: 300)
    """
    market_id: str
    threshold: float = 0.05
    lookback: int = 60
    cooldown: int = 300
    price_history: List[PricePoint] = field(default_factory=list)
    last_alert: Optional[datetime] = None

    def add_price(self, price: float, bid: float = 0, ask: float = 0) -> Optional[SpikeEvent]:
        """
        Add a price point and check for spike.

        Returns:
            SpikeEvent if spike detected, None otherwise
        """
        now = datetime.now()

        # Add to history
        self.price_history.append(PricePoint(
            timestamp=now,
            price=price,
            bid=bid,
            ask=ask
        ))

        # Trim old history
        cutoff = now - timedelta(seconds=self.lookback * 2)
        self.price_history = [p for p in self.price_history if p.timestamp > cutoff]

        # Need at least 2 points to compare
        if len(self.price_history) < 2:
            return None

        # Check cooldown
        if self.last_alert and (now - self.last_alert).total_seconds() < self.cooldown:
            return None

        # Find price from lookback period
        lookback_time = now - timedelta(seconds=self.lookback)
        old_prices = [p for p in self.price_history if p.timestamp <= lookback_time]

        if not old_prices:
            # Use oldest available price
            old_price = self.price_history[0].price
        else:
            old_price = old_prices[-1].price

        # Calculate change
        if old_price == 0:
            return None

        change = (price - old_price) / old_price
        change_pct = abs(change)

        # Check threshold
        if change_pct >= self.threshold:
            self.last_alert = now
            return SpikeEvent(
                market_id=self.market_id,
                old_price=old_price,
                new_price=price,
                change_pct=change_pct,
                direction="UP" if change > 0 else "DOWN",
                timestamp=now
            )

        return None


def format_spike_alert(spike: SpikeEvent) -> str:
    """Format spike event as alert string."""
    arrow = "↑" if spike.direction == "UP" else "↓"
    return f"""
┌─────────────────────────────────────────────────────────────┐
│  🚨 SPIKE DETECTED                                          │
├─────────────────────────────────────────────────────────────┤
│  Market:    {spike.market_id:<46}│
│  Direction: {spike.direction} {arrow:<45}│
│  Change:    {spike.change_pct*100:+.1f}%{' '*42}│
│  Price:     {spike.old_price*100:.0f}¢ → {spike.new_price*100:.0f}¢{' '*35}│
│  Time:      {spike.timestamp.strftime('%H:%M:%S'):<46}│
└─────────────────────────────────────────────────────────────┘
"""


def demo_spike_detection():
    """Demonstrate spike detection concept."""
    print("""
┌─────────────────────────────────────────────────────────────┐
│  SPIKE DETECTION EXPLAINED                                  │
└─────────────────────────────────────────────────────────────┘

A spike detector monitors price changes over time:

    Time    Price   Change (from 60s ago)
    ─────────────────────────────────────
    10:00   45¢     -
    10:01   46¢     +2.2%
    10:02   47¢     +4.4%
    10:03   52¢     +15.5% ← SPIKE DETECTED!

Configuration:
    - threshold: Minimum % change (default: 5%)
    - lookback:  Compare against price N seconds ago
    - cooldown:  Minimum time between alerts


USE CASES:

1. ALERT ONLY
   Get notified when a market moves significantly.
   Useful for news-driven markets.

2. AUTO-TRADE
   Automatically place orders on spike detection.
   Example: Buy on upward spike, expecting momentum.

3. MEAN REVERSION
   Trade against spikes expecting price to return.
   Example: Sell on upward spike if you think it's overreaction.
    """)


def demo_live_monitoring():
    """Show how to run live monitoring."""
    print("""
━━━ LIVE MONITORING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BASIC MONITORING LOOP:

    from polymarket_api import get_best_prices
    import time

    market_id = '1234567'
    detector = SpikeDetector(
        market_id=market_id,
        threshold=0.05,    # 5% spike
        lookback=60,       # Compare to 60s ago
        cooldown=300       # 5 min between alerts
    )

    print(f"Monitoring market {market_id}...")
    while True:
        try:
            prices = get_best_prices(market_id)
            current_price = (prices['best_bid'] + prices['best_ask']) / 2

            spike = detector.add_price(
                price=current_price,
                bid=prices['best_bid'],
                ask=prices['best_ask']
            )

            if spike:
                print(format_spike_alert(spike))
                # Optional: Execute trade here

            time.sleep(5)  # Check every 5 seconds

        except KeyboardInterrupt:
            print("\\nStopped monitoring.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)
    """)


def demo_auto_trading():
    """Show auto-trading on spike detection."""
    print("""
━━━ AUTO-TRADING ON SPIKES ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️  WARNING: Auto-trading carries significant risk!
    Always use position limits and stop-losses.

MOMENTUM STRATEGY (Trade with spike):

    if spike.direction == "UP":
        # Price going up - buy expecting continuation
        place_order(market_id, 'BUY', current_price, size)
    else:
        # Price going down - sell expecting continuation
        place_order(market_id, 'SELL', current_price, size)


MEAN REVERSION STRATEGY (Trade against spike):

    if spike.direction == "UP":
        # Price spiked up - expect it to come back down
        place_order(market_id, 'SELL', current_price * 0.98, size)
    else:
        # Price spiked down - expect it to recover
        place_order(market_id, 'BUY', current_price * 1.02, size)


RISK MANAGEMENT:

    # Configuration in config.py
    trading:
        max_position_size: 100    # Max shares per position
        max_daily_loss: 50        # Stop trading after $50 loss
        take_profit: 0.10         # Exit at 10% profit
        stop_loss: 0.05           # Exit at 5% loss
        cooldown_seconds: 300     # Wait 5 min between trades
    """)


def demo_multi_market():
    """Show monitoring multiple markets."""
    print("""
━━━ MULTI-MARKET MONITORING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Monitor multiple markets simultaneously:

    from concurrent.futures import ThreadPoolExecutor

    markets = ['1234567', '1234568', '1234569']
    detectors = {m: SpikeDetector(m, threshold=0.05) for m in markets}

    def check_market(market_id):
        prices = get_best_prices(market_id)
        price = (prices['best_bid'] + prices['best_ask']) / 2
        return detectors[market_id].add_price(price)

    while True:
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(check_market, markets))

        for spike in results:
            if spike:
                print(format_spike_alert(spike))

        time.sleep(5)
    """)


def run_demo_monitor():
    """Run a simulated monitoring demo."""
    print("""
━━━ SIMULATED SPIKE DETECTION ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Simulating price movements to demonstrate spike detection:
    """)

    detector = SpikeDetector(
        market_id="DEMO_MARKET",
        threshold=0.05,  # 5% spike
        lookback=3,      # Short lookback for demo
        cooldown=1       # Short cooldown for demo
    )

    # Simulated price series with a spike
    prices = [0.50, 0.51, 0.50, 0.52, 0.51, 0.58, 0.57, 0.48, 0.49, 0.50]

    for i, price in enumerate(prices):
        print(f"  Price update: {price*100:.0f}¢")
        spike = detector.add_price(price)
        if spike:
            print(format_spike_alert(spike))
        time.sleep(0.5)

    print("\nDemo complete!")


def main():
    """Run spike detector demos."""
    parser = argparse.ArgumentParser(description="Spike Detection Demo")
    parser.add_argument("--market", type=str, help="Market ID to monitor")
    parser.add_argument("--threshold", type=float, default=0.05, help="Spike threshold (default: 0.05)")
    parser.add_argument("--live", action="store_true", help="Run live monitoring")
    args = parser.parse_args()

    print("""
┌─────────────────────────────────────────────────────────────┐
│  CLAUDE POLYMARKET TRADING - SPIKE DETECTOR                 │
└─────────────────────────────────────────────────────────────┘
    """)

    if args.live and args.market:
        # Run live monitoring
        print(f"Starting live monitoring for market {args.market}")
        print(f"Threshold: {args.threshold*100}%")
        print("Press Ctrl+C to stop\n")

        try:
            from polymarket_api import get_best_prices

            detector = SpikeDetector(
                market_id=args.market,
                threshold=args.threshold
            )

            while True:
                try:
                    prices = get_best_prices(args.market)
                    current = (prices['best_bid'] + prices['best_ask']) / 2
                    print(f"  {datetime.now().strftime('%H:%M:%S')} - {current*100:.1f}¢", end='\r')

                    spike = detector.add_price(current, prices['best_bid'], prices['best_ask'])
                    if spike:
                        print()  # New line
                        print(format_spike_alert(spike))

                    time.sleep(5)

                except Exception as e:
                    print(f"\nError: {e}")
                    time.sleep(10)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped.")

    else:
        # Show demos
        demo_spike_detection()
        demo_live_monitoring()
        demo_auto_trading()
        demo_multi_market()
        run_demo_monitor()

        print("""
━━━ TO RUN LIVE MONITORING ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    python examples/spike_detector.py --live --market 1234567

Or ask Claude Code:
    "monitor market 1234567 for spikes"
    "alert me if trump market moves more than 5%"
        """)


if __name__ == "__main__":
    main()
