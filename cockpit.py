#!/usr/bin/env python3
"""
Polymarket Trading Cockpit
==========================
Professional trading interface for Claude Code.
- Clear previews before any trade
- Confirmation required for execution
- Smart research with related market discovery
"""
import json
from pathlib import Path

# Import API functions
from polymarket_api import (
    get_event_by_slug, get_gamma_market, get_price, get_best_prices,
    get_orderbook, place_order, cancel_order, cancel_all_orders,
    get_balances, get_positions, get_open_orders, search_markets
)
from market_db import search_db, get_trending, get_categories, db_stats

# =============================================================================
# STATE MANAGEMENT
# =============================================================================

STATE = {
    "active_event": None,
    "active_markets": [],
    "market_map": {},
    "pending_trades": [],
}

# =============================================================================
# TABLE BUILDING
# =============================================================================

def table(headers: list, rows: list, title: str = None) -> str:
    """Build ASCII table with box drawing"""
    if not rows:
        return "  (no data)"

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(str(cell)))

    # Add padding
    widths = [w + 2 for w in widths]

    # Build table
    lines = []

    # Title
    if title:
        total_width = sum(widths) + len(widths) + 1
        lines.append(f"┌{'─' * (total_width - 2)}┐")
        lines.append(f"│ {title:<{total_width - 4}} │")

    # Header separator
    sep_top = "┌" + "┬".join("─" * w for w in widths) + "┐"
    sep_mid = "├" + "┼".join("─" * w for w in widths) + "┤"
    sep_bot = "└" + "┴".join("─" * w for w in widths) + "┘"

    if title:
        lines.append("├" + "┬".join("─" * w for w in widths) + "┤")
    else:
        lines.append(sep_top)

    # Header row
    header_cells = [f" {h:^{widths[i]-2}} " for i, h in enumerate(headers)]
    lines.append("│" + "│".join(header_cells) + "│")
    lines.append(sep_mid)

    # Data rows
    for row in rows:
        cells = [f" {str(c):<{widths[i]-2}} " for i, c in enumerate(row)]
        lines.append("│" + "│".join(cells) + "│")

    lines.append(sep_bot)

    return "\n".join(lines)


def fmt_price(p: float) -> str:
    """Format price as cents"""
    if p is None or p == 0:
        return "──"
    return f"{p*100:.0f}¢"


def fmt_usd(amount: float) -> str:
    """Format as USD"""
    return f"${amount:.2f}"


def fmt_vol(v) -> str:
    """Format volume"""
    if v is None:
        return "──"
    try:
        v = float(v)
    except:
        return "──"
    if v == 0:
        return "──"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    elif v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def spread_label(spread: float) -> str:
    """Get spread quality label"""
    if spread < 0.02:
        return "TIGHT"
    elif spread < 0.10:
        return "OK"
    return "WIDE"


# =============================================================================
# DISPLAY FUNCTIONS (READ-ONLY)
# =============================================================================

def show_event(slug: str) -> str:
    """Display event with all markets"""
    event = get_event_by_slug(slug)
    if not event:
        return f"Event not found: {slug}"

    STATE["active_event"] = slug
    STATE["active_markets"] = []
    STATE["market_map"] = {}

    title = event.get('title', slug)
    rows = []

    for m in event.get('markets', []):
        mid = m.get('id')
        question = m.get('question', '')[:35]

        price = get_price(mid)
        prices = get_best_prices(mid)

        yes = price['yes']
        bid = prices['best_bid']
        ask = prices['best_ask']
        spread = prices['spread']

        rows.append([
            mid,
            question,
            fmt_price(yes),
            fmt_price(bid),
            fmt_price(ask),
            spread_label(spread)
        ])

        STATE["active_markets"].append(mid)
        STATE["market_map"][mid] = {
            "question": m.get('question', ''),
            "yes": yes,
            "bid": bid,
            "ask": ask
        }

    return table(
        ["ID", "Market", "YES", "Bid", "Ask", "Spread"],
        rows,
        title=title
    )


def show_market(market_id: str) -> str:
    """Display single market with orderbook"""
    market = get_gamma_market(market_id)
    if not market:
        return f"Market not found: {market_id}"

    question = market.get('question', market.get('title', ''))
    prices = get_best_prices(market_id)

    lines = []
    lines.append(f"┌{'─'*60}┐")
    lines.append(f"│ {question[:58]:<58} │")
    lines.append(f"├{'─'*60}┤")
    lines.append(f"│ ID: {market_id:<54} │")
    lines.append(f"│ Bid: {fmt_price(prices['best_bid']):<10} Ask: {fmt_price(prices['best_ask']):<10} Spread: {spread_label(prices['spread']):<10} │")
    lines.append(f"└{'─'*60}┘")

    # Mini orderbook
    try:
        ob = get_orderbook(market_id)
        bids = sorted([{"p": float(b.price), "s": float(b.size)} for b in ob.bids], key=lambda x: x['p'], reverse=True)[:5]
        asks = sorted([{"p": float(a.price), "s": float(a.size)} for a in ob.asks], key=lambda x: x['p'])[:5]

        lines.append("")
        lines.append("  BIDS              │  ASKS")
        lines.append("  ──────────────────┼──────────────────")
        for i in range(max(len(bids), len(asks))):
            bid_str = f"{bids[i]['s']:>6.0f} @ {bids[i]['p']*100:.0f}¢" if i < len(bids) else ""
            ask_str = f"{asks[i]['p']*100:.0f}¢ @ {asks[i]['s']:<6.0f}" if i < len(asks) else ""
            lines.append(f"  {bid_str:<18}│  {ask_str}")
    except:
        pass

    return "\n".join(lines)


def show_portfolio() -> str:
    """Display positions, orders, and balance"""
    lines = []

    # Balance
    bal = get_balances()
    lines.append("┌─────────────────────────────────────────┐")
    lines.append("│ PORTFOLIO                               │")
    lines.append("├─────────────────────────────────────────┤")

    if isinstance(bal, dict) and 'balance' in str(bal).lower():
        lines.append(f"│ Balance: {str(bal):<30} │")
    else:
        lines.append(f"│ Balance: Check Polymarket UI            │")

    lines.append("└─────────────────────────────────────────┘")

    # Positions
    positions = get_positions()
    if positions:
        rows = []
        for p in positions[:10]:
            rows.append([
                str(p.get('asset', ''))[:8] + "...",
                p.get('side', 'YES'),
                p.get('size', 0),
                fmt_price(float(p.get('avgPrice', 0)))
            ])
        lines.append("")
        lines.append(table(["Token", "Side", "Size", "Avg"], rows, title="POSITIONS"))

    # Orders
    orders = get_open_orders()
    if orders:
        rows = []
        for o in orders[:10]:
            rows.append([
                o.get('side', 'BUY'),
                fmt_price(float(o.get('price', 0))),
                o.get('original_size', o.get('size', 0)),
                str(o.get('id', ''))[:12] + "..."
            ])
        lines.append("")
        lines.append(table(["Side", "Price", "Size", "Order ID"], rows, title="OPEN ORDERS"))

    if not positions and not orders:
        lines.append("")
        lines.append("  No positions or open orders")

    return "\n".join(lines)


def search(query: str) -> str:
    """Search markets with smart discovery"""
    # Search local DB first (fast)
    db_results = search_db(query, limit=10)

    # Also search API for fresh data
    api_results = search_markets(query, limit=10)

    # Combine and dedupe
    seen = set()
    results = []

    for m in db_results:
        if m['id'] not in seen:
            seen.add(m['id'])
            results.append({
                'id': m['id'],
                'title': m['title'][:40],
                'yes': m.get('yes_price', 0.5),
                'vol': m.get('volume', 0),
                'source': 'db'
            })

    for m in api_results:
        mid = str(m.get('id', ''))
        if mid and mid not in seen:
            seen.add(mid)
            prices = m.get('outcomePrices', '[0.5, 0.5]')
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except:
                    prices = [0.5, 0.5]
            results.append({
                'id': mid,
                'title': m.get('question', m.get('title', ''))[:40],
                'yes': float(prices[0]) if prices else 0.5,
                'vol': m.get('volume', 0),
                'source': 'api'
            })

    if not results:
        return f"No markets found for: {query}"

    rows = [[r['id'], r['title'], fmt_price(r['yes']), fmt_vol(r['vol'])] for r in results[:15]]
    return table(["ID", "Market", "YES", "Volume"], rows, title=f"SEARCH: {query}")


# =============================================================================
# TRADING FUNCTIONS (WITH PREVIEW)
# =============================================================================

def preview_buy(market_id: str, size: int, price: float = None, outcome: str = "yes") -> str:
    """Preview a buy order (NO EXECUTION)"""
    if price is None:
        prices = get_best_prices(market_id, outcome)
        price = prices['best_ask']

    cost = size * price
    market_info = STATE["market_map"].get(market_id, {})
    question = market_info.get('question', f'Market {market_id}')[:30]

    STATE["pending_trades"] = [{
        "action": "BUY",
        "outcome": outcome.upper(),
        "market_id": market_id,
        "size": size,
        "price": price,
        "cost": cost
    }]

    rows = [
        ["BUY " + outcome.upper(), f"{size} @ {fmt_price(price)} ({fmt_usd(cost)})", "pending"],
        ["Market", f"{market_id} - {question}", ""]
    ]

    output = table(["Action", "Details", "Status"], rows)
    output += "\n\nConfirm? (say 'yes', 'go', or 'confirm' to execute)"
    return output


def preview_sell(market_id: str, size: int, price: float = None, outcome: str = "yes") -> str:
    """Preview a sell order (NO EXECUTION)"""
    if price is None:
        prices = get_best_prices(market_id, outcome)
        price = prices['best_bid']

    proceeds = size * price
    market_info = STATE["market_map"].get(market_id, {})
    question = market_info.get('question', f'Market {market_id}')[:30]

    STATE["pending_trades"] = [{
        "action": "SELL",
        "outcome": outcome.upper(),
        "market_id": market_id,
        "size": size,
        "price": price,
        "proceeds": proceeds
    }]

    rows = [
        ["SELL " + outcome.upper(), f"{size} @ {fmt_price(price)} ({fmt_usd(proceeds)})", "pending"],
        ["Market", f"{market_id} - {question}", ""]
    ]

    output = table(["Action", "Details", "Status"], rows)
    output += "\n\nConfirm? (say 'yes', 'go', or 'confirm' to execute)"
    return output


def preview_market_buy(market_id: str, usd_amount: float, outcome: str = "yes") -> str:
    """Preview market buy for $X (NO EXECUTION)"""
    prices = get_best_prices(market_id, outcome)
    ask = prices['best_ask']

    if ask <= 0 or ask >= 1:
        return f"Cannot buy - invalid ask price: {ask}"

    size = int(usd_amount / ask)
    cost = size * ask

    STATE["pending_trades"] = [{
        "action": "BUY",
        "outcome": outcome.upper(),
        "market_id": market_id,
        "size": size,
        "price": ask,
        "cost": cost,
        "market_order": True
    }]

    rows = [
        ["BUY " + outcome.upper(), f"{size} @ {fmt_price(ask)} ({fmt_usd(cost)})", "pending"],
        ["Market", market_id, "MARKET ORDER"]
    ]

    output = table(["Action", "Details", "Status"], rows)
    output += "\n\nConfirm? (say 'yes', 'go', or 'confirm' to execute)"
    return output


def preview_market_sell(market_id: str, size: int, outcome: str = "yes") -> str:
    """Preview market sell (NO EXECUTION)"""
    prices = get_best_prices(market_id, outcome)
    bid = prices['best_bid']

    if bid <= 0:
        return f"Cannot sell - no bids available"

    proceeds = size * bid

    STATE["pending_trades"] = [{
        "action": "SELL",
        "outcome": outcome.upper(),
        "market_id": market_id,
        "size": size,
        "price": bid,
        "proceeds": proceeds,
        "market_order": True
    }]

    rows = [
        ["SELL " + outcome.upper(), f"{size} @ {fmt_price(bid)} ({fmt_usd(proceeds)})", "pending"],
        ["Market", market_id, "MARKET ORDER"]
    ]

    output = table(["Action", "Details", "Status"], rows)
    output += "\n\nConfirm? (say 'yes', 'go', or 'confirm' to execute)"
    return output


# =============================================================================
# EXECUTION (AFTER CONFIRMATION)
# =============================================================================

def execute_pending() -> str:
    """Execute pending trades after user confirmation"""
    if not STATE["pending_trades"]:
        return "No pending trades to execute"

    results = []
    for trade in STATE["pending_trades"]:
        try:
            result = place_order(
                trade["market_id"],
                trade["action"],
                trade["price"],
                trade["size"],
                trade["outcome"].lower()
            )
            status = result.get("status", "unknown")
            results.append([
                f"{trade['action']} {trade['outcome']}",
                f"{trade['size']} @ {fmt_price(trade['price'])}",
                f"✓ {status}"
            ])
        except Exception as e:
            results.append([
                f"{trade['action']} {trade['outcome']}",
                f"{trade['size']} @ {fmt_price(trade['price'])}",
                f"✗ {str(e)[:20]}"
            ])

    STATE["pending_trades"] = []
    return table(["Action", "Details", "Status"], results)


def cancel_pending() -> str:
    """Cancel pending trades"""
    count = len(STATE["pending_trades"])
    STATE["pending_trades"] = []
    return f"Cancelled {count} pending trade(s)"


# =============================================================================
# DIRECT EXECUTION (FOR CLAUDE TO USE AFTER CONFIRMATION)
# =============================================================================

def do_buy(market_id: str, size: int, price: float, outcome: str = "yes") -> str:
    """Direct buy execution"""
    try:
        result = place_order(market_id, "BUY", price, size, outcome)
        status = result.get("status", "unknown")
        return table(
            ["Action", "Details", "Status"],
            [[f"BUY {outcome.upper()}", f"{size} @ {fmt_price(price)}", f"✓ {status}"]]
        )
    except Exception as e:
        return f"Order failed: {e}"


def do_sell(market_id: str, size: int, price: float, outcome: str = "yes") -> str:
    """Direct sell execution"""
    try:
        result = place_order(market_id, "SELL", price, size, outcome)
        status = result.get("status", "unknown")
        return table(
            ["Action", "Details", "Status"],
            [[f"SELL {outcome.upper()}", f"{size} @ {fmt_price(price)}", f"✓ {status}"]]
        )
    except Exception as e:
        return f"Order failed: {e}"


def do_cancel(order_id: str = None) -> str:
    """Cancel order(s)"""
    try:
        if order_id:
            cancel_order(order_id)
            return f"Cancelled order: {order_id}"
        else:
            cancel_all_orders()
            return "Cancelled all orders"
    except Exception as e:
        return f"Cancel failed: {e}"


# =============================================================================
# QUICK STATUS
# =============================================================================

def status() -> str:
    """Quick status overview"""
    lines = []

    # DB stats
    stats = db_stats()
    lines.append(f"Database: {stats['active']} active markets")

    # Active event
    if STATE["active_event"]:
        lines.append(f"Active event: {STATE['active_event']}")
        lines.append(f"Markets loaded: {len(STATE['active_markets'])}")

    # Pending trades
    if STATE["pending_trades"]:
        lines.append(f"Pending trades: {len(STATE['pending_trades'])}")

    # Portfolio summary
    positions = get_positions()
    orders = get_open_orders()
    lines.append(f"Positions: {len(positions)}")
    lines.append(f"Open orders: {len(orders)}")

    return "\n".join(lines)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    print("Polymarket Trading Cockpit")
    print("=" * 40)
    print(status())
    print()

    # Test table
    print(table(
        ["Action", "Details", "Status"],
        [
            ["BUY YES", "10 @ 35¢ ($3.50)", "pending"],
            ["SELL NO", "5 @ 60¢ ($3.00)", "pending"]
        ],
        title="Sample Trade Preview"
    ))
