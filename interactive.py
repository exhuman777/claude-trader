#!/usr/bin/env python3
"""
Interactive Polymarket Trading Session
======================================
Simple REPL for trading. Type commands, Claude-style.
"""
import readline  # For command history
from polymarket_api import *

# Store current event context
current_event = None
current_markets = {}

def parse_date(text):
    """Extract date like 'jan 25' from text"""
    import re
    # Pattern 1: "jan 25"
    m = re.search(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*(\d{1,2})', text.lower())
    if m:
        return f"{m.group(1)} {m.group(2)}"
    # Pattern 2: "25 jan"
    m = re.search(r'(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', text.lower())
    if m:
        return f"{m.group(2)} {m.group(1)}"
    return None

def find_market_by_date(date_hint):
    """Find market ID from current event by date"""
    if not current_markets:
        return None
    date_lower = date_hint.lower()
    month_map = {"jan": "january", "feb": "february", "mar": "march", "apr": "april",
                 "may": "may", "jun": "june", "jul": "july", "aug": "august",
                 "sep": "september", "oct": "october", "nov": "november", "dec": "december"}

    parts = date_lower.split()
    month = month_map.get(parts[0][:3], parts[0]) if parts else None
    day = parts[1] if len(parts) > 1 else None

    for mid, info in current_markets.items():
        q = info.get('question', '').lower()
        if month and day and f"{month} {day}" in q:
            return mid
    return None

def process_command(cmd):
    """Process user command"""
    global current_event, current_markets

    cmd = cmd.strip()
    if not cmd:
        return

    parts = cmd.lower().split()
    if not parts:
        return

    # URL - load event
    if 'polymarket.com' in cmd:
        import re
        m = re.search(r'polymarket\.com/event/([a-z0-9-]+)', cmd)
        if m:
            slug = m.group(1)
            print(f"\nLoading event: {slug}")
            markets = show_event(slug)
            if markets:
                current_event = slug
                current_markets = {m['id']: m for m in markets}
                print(f"[Context set: {len(markets)} markets loaded]")
            return

    # Show event
    if parts[0] == 'event':
        slug = parts[1] if len(parts) > 1 else current_event
        if slug:
            markets = show_event(slug)
            if markets:
                current_event = slug
                current_markets = {m['id']: m for m in markets}
        else:
            print("Usage: event <slug>")
        return

    # Orders
    if parts[0] in ['orders', 'order']:
        show_orders()
        return

    # Positions
    if parts[0] in ['positions', 'pos', 'portfolio']:
        positions = get_positions()
        if positions:
            print(f"Positions: {len(positions)}")
            for p in positions:
                print(f"  {p}")
        else:
            print("No positions")
        return

    # Cancel
    if parts[0] == 'cancel':
        if len(parts) > 1 and parts[1] == 'all':
            print("Cancelling all orders...")
            result = cancel_all_orders()
            print(f"Done: {result}")
        elif len(parts) > 1:
            cancel_order(parts[1])
        else:
            print("Usage: cancel all  OR  cancel <order_id>")
        return

    # Price check
    if parts[0] == 'price':
        market_id = parts[1] if len(parts) > 1 else None
        if not market_id:
            # Try to get from date
            date = parse_date(cmd)
            if date:
                market_id = find_market_by_date(date)
        if market_id:
            price = get_price(market_id)
            best = get_best_prices(market_id)
            print(f"Market {market_id}:")
            print(f"  YES: {price['yes']*100:.0f}¢")
            print(f"  Bid: {best['best_bid']*100:.0f}¢  Ask: {best['best_ask']*100:.0f}¢")
        else:
            print("Usage: price <market_id> or price jan 25")
        return

    # Buy command
    if 'buy' in cmd:
        import re
        # Extract size
        size_m = re.search(r'buy\s+(\d+)', cmd)
        size = int(size_m.group(1)) if size_m else 5

        # Extract price
        price_m = re.search(r'(?:at|@)\s*(\d+(?:\.\d+)?)\s*(?:c|¢|cents?)?', cmd)
        price = float(price_m.group(1)) if price_m else None
        if price and price > 1:
            price = price / 100  # Convert cents to decimal

        # Extract market from date
        date = parse_date(cmd)
        market_id = None
        if date:
            market_id = find_market_by_date(date)
        if not market_id and len(parts) > 1:
            # Try direct market ID
            for p in parts:
                if p.isdigit() and len(p) > 4:
                    market_id = p
                    break

        if not market_id:
            print("Could not find market. Specify date (jan 25) or market ID")
            print(f"Current markets: {list(current_markets.keys())}")
            return

        # Get market info
        info = current_markets.get(market_id, {})
        q = info.get('question', market_id)[:50]

        # Get best ask if no price
        if price is None or 'market' in cmd:
            best = get_best_prices(market_id)
            price = best['best_ask']
            print(f"Using best ask: {price*100:.0f}¢")

        print(f"\n{'='*50}")
        print(f"  BUY ORDER")
        print(f"{'='*50}")
        print(f"  Market: {q}...")
        print(f"  ID: {market_id}")
        print(f"  Size: {size} shares")
        print(f"  Price: {price*100:.0f}¢")
        print(f"  Total: ${size * price:.2f}")
        print(f"{'='*50}")

        confirm = input("\nConfirm? [y/N]: ").strip().lower()
        if confirm in ['y', 'yes']:
            result = place_order(market_id, 'BUY', price, size)
            print(f"Result: {result.get('status')} | {result.get('orderID', 'N/A')[:40]}...")
        else:
            print("Cancelled")
        return

    # Sell command
    if 'sell' in cmd:
        import re
        # Extract size
        size_m = re.search(r'sell\s+(\d+)', cmd)
        size = int(size_m.group(1)) if size_m else 5

        # Extract price
        price_m = re.search(r'(?:at|@)\s*(\d+(?:\.\d+)?)\s*(?:c|¢|cents?)?', cmd)
        price = float(price_m.group(1)) if price_m else None
        if price and price > 1:
            price = price / 100

        # Extract market from date
        date = parse_date(cmd)
        market_id = find_market_by_date(date) if date else None

        if not market_id:
            print("Could not find market. Specify date (jan 25) or market ID")
            return

        info = current_markets.get(market_id, {})
        q = info.get('question', market_id)[:50]

        if price is None:
            best = get_best_prices(market_id)
            price = best['best_bid']
            print(f"Using best bid: {price*100:.0f}¢")

        print(f"\n{'='*50}")
        print(f"  SELL ORDER")
        print(f"{'='*50}")
        print(f"  Market: {q}...")
        print(f"  Size: {size} shares")
        print(f"  Price: {price*100:.0f}¢")
        print(f"{'='*50}")

        confirm = input("\nConfirm? [y/N]: ").strip().lower()
        if confirm in ['y', 'yes']:
            result = place_order(market_id, 'SELL', price, size)
            print(f"Result: {result.get('status')}")
        else:
            print("Cancelled")
        return

    # Ladder command
    if 'ladder' in cmd or 'orders from' in cmd:
        import re

        # Determine side
        side = 'SELL' if 'sell' in cmd else 'BUY'

        # Extract price range
        range_m = re.search(r'from\s+(\d+(?:\.\d+)?)\s*(?:c|¢)?\s*(?:to|-|->)\s*(\d+(?:\.\d+)?)', cmd)
        if not range_m:
            print("Usage: ladder buy from 40 to 35  OR  create 5 sell orders from 60 to 65")
            return

        p1 = float(range_m.group(1))
        p2 = float(range_m.group(2))
        if p1 > 1: p1 = p1 / 100
        if p2 > 1: p2 = p2 / 100

        # Smart direction
        if side == 'BUY':
            start, end = max(p1, p2), min(p1, p2)
        else:
            start, end = min(p1, p2), max(p1, p2)

        # Extract count
        count_m = re.search(r'(\d+)\s*(?:orders?|limit)', cmd)
        num_orders = int(count_m.group(1)) if count_m else 5

        # Extract size per order
        size_m = re.search(r'(\d+)\s*shares?\s*(?:each|per)', cmd)
        if not size_m:
            size_m = re.search(r'each\s+(\d+)', cmd)
        shares_per = int(size_m.group(1)) if size_m else 5

        # Find market
        date = parse_date(cmd)
        market_id = find_market_by_date(date) if date else None

        if not market_id and current_markets:
            # Use first market as default
            market_id = list(current_markets.keys())[0]
            print(f"Using default market: {market_id}")

        if not market_id:
            print("Could not find market. Load event first or specify date")
            return

        info = current_markets.get(market_id, {})
        q = info.get('question', market_id)[:50]

        print(f"\n{'='*50}")
        print(f"  LADDER ORDER")
        print(f"{'='*50}")
        print(f"  Market: {q}...")
        print(f"  ID: {market_id}")
        print(f"  Side: {side}")
        print(f"  Range: {start*100:.0f}¢ → {end*100:.0f}¢")
        print(f"  Orders: {num_orders} @ {shares_per} shares each")
        print(f"  Total: {num_orders * shares_per} shares")
        print(f"{'='*50}")

        confirm = input("\nConfirm? [y/N]: ").strip().lower()
        if confirm in ['y', 'yes']:
            results = place_ladder(market_id, side, start, end, num_orders, shares_per)
            print("\nResults:")
            for r in results:
                status = r.get('status', r.get('error', '?'))
                print(f"  {r['price']:.0f}¢ x {shares_per} -> {status}")
        else:
            print("Cancelled")
        return

    # Help
    if parts[0] in ['help', '?']:
        print("""
Commands:
  <URL>                      - Load event from Polymarket URL
  event <slug>               - Load event
  buy <size> jan 25 at <price> - Buy shares
  sell <size> jan 31 at <price> - Sell shares
  ladder buy from 40 to 35    - Create ladder orders
  orders                     - Show open orders
  positions                  - Show positions
  cancel all                 - Cancel all orders
  price jan 25               - Check price
  quit/exit                  - Exit
        """)
        return

    print(f"Unknown command. Type 'help' for commands.")

def main():
    print("="*60)
    print("  Polymarket Interactive Trading")
    print("="*60)
    print("Type 'help' for commands, 'quit' to exit")
    print("Paste a Polymarket URL to start")
    print()

    while True:
        try:
            cmd = input("trade> ").strip()
            if cmd.lower() in ['quit', 'exit', 'q']:
                print("Bye!")
                break
            process_command(cmd)
        except KeyboardInterrupt:
            print("\nUse 'quit' to exit")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
