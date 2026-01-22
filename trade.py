#!/usr/bin/env python3
"""
Trade Executor - Simple CLI for Polymarket trading
===================================================
Usage:
  python trade.py event <slug>
  python trade.py buy <market_id> <price> <size>
  python trade.py sell <market_id> <price> <size>
  python trade.py ladder <market_id> <side> <start> <end> <num> <size>
  python trade.py orders
  python trade.py cancel [order_id|all]
  python trade.py positions
"""
import sys
from polymarket_api import *

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "event":
        # Show event: python trade.py event us-forces-seize-another-oil-tanker-by
        if len(sys.argv) < 3:
            print("Usage: python trade.py event <slug>")
            return
        show_event(sys.argv[2])

    elif cmd == "buy":
        # Buy: python trade.py buy 1230810 0.35 5
        if len(sys.argv) < 5:
            print("Usage: python trade.py buy <market_id> <price> <size>")
            return
        market_id = sys.argv[2]
        price = float(sys.argv[3])
        size = int(sys.argv[4])

        print(f"BUY {size} shares @ {price*100:.0f}¢ in market {market_id}")
        result = place_order(market_id, "BUY", price, size)
        print(f"Result: {result.get('status')} | Order: {result.get('orderID', 'N/A')[:40]}...")

    elif cmd == "sell":
        # Sell: python trade.py sell 1230810 0.40 5
        if len(sys.argv) < 5:
            print("Usage: python trade.py sell <market_id> <price> <size>")
            return
        market_id = sys.argv[2]
        price = float(sys.argv[3])
        size = int(sys.argv[4])

        print(f"SELL {size} shares @ {price*100:.0f}¢ in market {market_id}")
        result = place_order(market_id, "SELL", price, size)
        print(f"Result: {result.get('status')} | Order: {result.get('orderID', 'N/A')[:40]}...")

    elif cmd == "ladder":
        # Ladder: python trade.py ladder 1230810 BUY 0.40 0.35 5 10
        if len(sys.argv) < 8:
            print("Usage: python trade.py ladder <market_id> <side> <start> <end> <num_orders> <shares_per>")
            print("Example: python trade.py ladder 1230810 BUY 0.40 0.35 5 10")
            return
        market_id = sys.argv[2]
        side = sys.argv[3].upper()
        start = float(sys.argv[4])
        end = float(sys.argv[5])
        num = int(sys.argv[6])
        size = int(sys.argv[7])

        print(f"LADDER {side}: {num} orders from {start*100:.0f}¢ to {end*100:.0f}¢, {size} shares each")
        results = place_ladder(market_id, side, start, end, num, size)
        for r in results:
            status = r.get('status', r.get('error', 'unknown'))
            print(f"  {r['price']:.0f}¢ x {r.get('size', size)} -> {status}")

    elif cmd == "orders":
        # Show orders
        show_orders()

    elif cmd == "cancel":
        # Cancel: python trade.py cancel all  OR  python trade.py cancel <order_id>
        if len(sys.argv) < 3:
            print("Usage: python trade.py cancel all|<order_id>")
            return

        if sys.argv[2].lower() == "all":
            print("Cancelling all orders...")
            result = cancel_all_orders()
            print(f"Result: {result}")
        else:
            order_id = sys.argv[2]
            print(f"Cancelling order {order_id[:30]}...")
            result = cancel_order(order_id)
            print(f"Result: {result}")

    elif cmd == "positions":
        # Show positions
        positions = get_positions()
        if not positions:
            print("No open positions")
        else:
            print(f"Positions ({len(positions)}):")
            for p in positions:
                print(f"  {p}")

    elif cmd == "price":
        # Check price: python trade.py price 1230810
        if len(sys.argv) < 3:
            print("Usage: python trade.py price <market_id>")
            return
        market_id = sys.argv[2]
        price = get_price(market_id)
        best = get_best_prices(market_id)
        print(f"Market {market_id}:")
        print(f"  Gamma Price: YES={price['yes']*100:.0f}¢")
        print(f"  Best Bid: {best['best_bid']*100:.0f}¢")
        print(f"  Best Ask: {best['best_ask']*100:.0f}¢")
        print(f"  Spread: {best['spread']*100:.0f}¢ {'(liquid)' if best['liquid'] else '(wide)'}")

    elif cmd == "search":
        # Search: python trade.py search "bitcoin"
        if len(sys.argv) < 3:
            print("Usage: python trade.py search <query>")
            return
        query = " ".join(sys.argv[2:])
        results = search_markets(query, limit=10)
        print(f"Search: '{query}' ({len(results)} results)")
        for r in results[:10]:
            mid = r.get('id')
            q = r.get('question', '')[:50]
            print(f"  {mid}: {q}...")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

if __name__ == "__main__":
    main()
