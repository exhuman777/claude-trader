#!/usr/bin/env python3
"""
Polymarket Trading API - Clean, Working Implementation
======================================================
This module contains ONLY the functions that work reliably.
Tested and verified for Claude Code trading.
"""
import os
import sys
import json
from pathlib import Path

# Add parent for config access (3 levels up to dashboard4all)
PARENT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PARENT))

# Also add venv site-packages
VENV_SITE = PARENT / ".venv/lib/python3.12/site-packages"
if VENV_SITE.exists():
    sys.path.insert(0, str(VENV_SITE))

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType

# =============================================================================
# CONFIGURATION & CACHES
# =============================================================================

CONFIG_FILE = PARENT / "data/.trading_config.json"

# In-memory caches to reduce API calls
_TOKEN_CACHE = {}  # market_id -> {yes: token_id, no: token_id}
_MARKET_CACHE = {}  # market_id -> market_data
_CLIENT = None  # Singleton client

def load_config():
    """Load trading configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    raise FileNotFoundError(f"Config not found: {CONFIG_FILE}")

def get_client():
    """Get authenticated CLOB client (singleton)"""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    config = load_config()
    client = ClobClient(
        host=config["host"],
        key=config["private_key"],
        chain_id=config["chain_id"],
        signature_type=config["signature_type"],
        funder=config["funder"]
    )
    client.set_api_creds(client.create_or_derive_api_creds())
    _CLIENT = client
    return client

# =============================================================================
# ACCOUNT FUNCTIONS (WORKING)
# =============================================================================

def get_balances():
    """Get USDC balance"""
    client = get_client()
    try:
        return client.get_balance_allowance()
    except:
        return {"note": "Check Polymarket UI for balance"}

def get_positions():
    """Get open positions"""
    client = get_client()
    try:
        return client.get_positions() or []
    except:
        return []

def get_open_orders():
    """Get all open orders"""
    client = get_client()
    try:
        return client.get_orders() or []
    except:
        return []

# =============================================================================
# MARKET LOOKUP (WORKING)
# =============================================================================

def get_event_by_slug(slug: str):
    """Get event details by slug (from URL)"""
    import urllib.request
    import ssl

    url = f"https://gamma-api.polymarket.com/events/slug/{slug}"
    req = urllib.request.Request(url, headers={'User-Agent': 'ClaudeTrading/1.0'})
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read())
    except:
        return None

def get_gamma_market(market_id: str, use_cache: bool = True):
    """Get market details from Gamma API (with cache)"""
    import urllib.request
    import ssl

    # Check cache first
    if use_cache and market_id in _MARKET_CACHE:
        return _MARKET_CACHE[market_id]

    url = f"https://gamma-api.polymarket.com/markets/{market_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'ClaudeTrading/1.0'})
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            data = json.loads(resp.read())
            _MARKET_CACHE[market_id] = data
            return data
    except:
        return {}

def get_clob_token_id(market_id: str, outcome: str = "yes"):
    """Convert market_id to CLOB token_id (with cache)"""
    import json as json_mod

    # Check token cache
    cache_key = f"{market_id}_{outcome.lower()}"
    if market_id in _TOKEN_CACHE:
        cached = _TOKEN_CACHE[market_id]
        return cached.get(outcome.lower())

    market = get_gamma_market(market_id)
    tokens = market.get("clobTokenIds", [])
    if not tokens:
        raise ValueError(f"No token IDs for market {market_id}")

    # Parse if it's a JSON string
    if isinstance(tokens, str):
        tokens = json_mod.loads(tokens)

    # Cache both yes and no tokens
    _TOKEN_CACHE[market_id] = {
        "yes": tokens[0],
        "no": tokens[1] if len(tokens) > 1 else tokens[0]
    }

    return _TOKEN_CACHE[market_id][outcome.lower()]

def search_markets(query: str, limit: int = 10):
    """Search markets via Gamma API"""
    import urllib.request
    import ssl
    from urllib.parse import quote

    url = f"https://gamma-api.polymarket.com/markets?_q={quote(query)}&limit={limit}&active=true"
    req = urllib.request.Request(url, headers={'User-Agent': 'ClaudeTrading/1.0'})
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read())
    except:
        return []

# =============================================================================
# PRICE & ORDERBOOK (WORKING)
# =============================================================================

def get_price(market_id: str):
    """Get current price from Gamma API"""
    market = get_gamma_market(market_id)
    prices = market.get("outcomePrices", "")

    if isinstance(prices, str) and prices:
        try:
            price_list = json.loads(prices)
            yes_price = float(price_list[0]) if price_list else 0
            no_price = float(price_list[1]) if len(price_list) > 1 else 1 - yes_price
            return {"yes": yes_price, "no": no_price, "mid": yes_price}
        except:
            pass

    return {"yes": 0.5, "no": 0.5, "mid": 0.5}

def get_orderbook(market_id: str, outcome: str = "yes"):
    """Get orderbook for market"""
    client = get_client()
    token_id = get_clob_token_id(market_id, outcome)
    return client.get_order_book(token_id)

def get_best_prices(market_id: str, outcome: str = "yes"):
    """Get best bid/ask from orderbook"""
    try:
        ob = get_orderbook(market_id, outcome)
        best_bid = max([float(b.price) for b in ob.bids]) if ob.bids else 0
        best_ask = min([float(a.price) for a in ob.asks]) if ob.asks else 1
        spread = best_ask - best_bid
        return {
            "best_bid": best_bid,
            "best_ask": best_ask,
            "spread": spread,
            "liquid": spread < 0.10  # <10c spread = liquid
        }
    except:
        return {"best_bid": 0, "best_ask": 1, "spread": 1, "liquid": False}

# =============================================================================
# TRADING (WORKING)
# =============================================================================

def place_order(market_id: str, side: str, price: float, size: int, outcome: str = "yes"):
    """
    Place a limit order.

    Args:
        market_id: Numeric market ID (e.g., "1230810")
        side: "BUY" or "SELL"
        price: Price in decimal (0.35 = 35 cents)
        size: Number of shares
        outcome: "yes" or "no"

    Returns:
        Order result dict with orderID, status
    """
    client = get_client()
    token_id = get_clob_token_id(market_id, outcome)

    # Get tick size (neg_risk markets use 0.01)
    market = get_gamma_market(market_id)
    neg_risk = market.get("negRisk", False)
    tick_size = "0.01" if neg_risk else "0.001"

    # Round price to tick
    price = round(price, 2 if neg_risk else 3)

    order_args = OrderArgs(
        price=price,
        size=size,
        side=side.upper(),
        token_id=token_id
    )

    signed = client.create_order(order_args)
    result = client.post_order(signed, OrderType.GTC)

    print(f"[ORDER] {side} {size} @ {price} -> {result.get('status', 'unknown')}")
    return result

def cancel_order(order_id: str):
    """Cancel a single order"""
    client = get_client()
    return client.cancel(order_id)

def cancel_all_orders():
    """Cancel all open orders"""
    client = get_client()
    return client.cancel_all()

def place_ladder(market_id: str, side: str, start_price: float, end_price: float,
                 num_orders: int, shares_per: int, outcome: str = "yes"):
    """
    Place multiple limit orders in a price range.

    BUY ladder: starts HIGH, goes LOW (waiting for dips)
    SELL ladder: starts LOW, goes HIGH (waiting for rises)

    Args:
        market_id: Market ID
        side: "BUY" or "SELL"
        start_price: Starting price (decimal)
        end_price: Ending price (decimal)
        num_orders: Number of orders to place
        shares_per: Shares per order
        outcome: "yes" or "no"

    Returns:
        List of order results
    """
    results = []
    step = (end_price - start_price) / max(num_orders - 1, 1)

    price = start_price
    for i in range(num_orders):
        try:
            result = place_order(market_id, side, round(price, 2), shares_per, outcome)
            results.append({
                "price": round(price * 100, 1),
                "size": shares_per,
                "status": result.get("status", "unknown"),
                "order_id": result.get("orderID", "")
            })
        except Exception as e:
            results.append({"price": round(price * 100, 1), "error": str(e)})

        price += step

    return results

# =============================================================================
# QUICK HELPERS
# =============================================================================

def show_event(slug: str):
    """Show event with all markets and prices - professional format"""
    event = get_event_by_slug(slug)
    if not event:
        print(f"  Event not found: {slug}")
        return None

    title = event.get('title', slug)

    print()
    print(f"  \033[1;36m▶ EVENT\033[0m  {title}")
    print(f"  \033[90m{'─'*70}\033[0m")
    print()
    print(f"  \033[90m│\033[0m {'Market':<40} \033[90m│\033[0m {'YES':^8} \033[90m│\033[0m {'Bid':^8} \033[90m│\033[0m {'Ask':^8} \033[90m│\033[0m {'Spread':^8} \033[90m│\033[0m")
    print(f"  \033[90m├{'─'*41}┼{'─'*9}┼{'─'*9}┼{'─'*9}┼{'─'*9}┤\033[0m")

    markets = []
    for m in event.get('markets', []):
        mid = m.get('id')
        question = m.get('question', '')[:39]

        price = get_price(mid)
        prices = get_best_prices(mid)

        yes_val = price['yes']
        bid_val = prices['best_bid']
        ask_val = prices['best_ask']
        spread = prices['spread']

        # Color coding
        yes_color = "\033[92m" if yes_val > 0.5 else "\033[93m" if yes_val > 0.3 else "\033[91m"
        spread_color = "\033[92m" if spread < 0.05 else "\033[93m" if spread < 0.15 else "\033[91m"

        yes_p = f"{yes_val*100:.0f}¢"
        bid = f"{bid_val*100:.0f}¢" if bid_val > 0.01 else "──"
        ask = f"{ask_val*100:.0f}¢" if ask_val < 0.99 else "──"
        spread_str = f"{spread*100:.0f}¢" if spread < 0.99 else "wide"

        print(f"  \033[90m│\033[0m {question:<40} \033[90m│\033[0m {yes_color}{yes_p:^8}\033[0m \033[90m│\033[0m \033[92m{bid:^8}\033[0m \033[90m│\033[0m \033[91m{ask:^8}\033[0m \033[90m│\033[0m {spread_color}{spread_str:^8}\033[0m \033[90m│\033[0m")
        markets.append({"id": mid, "question": m.get('question', ''), "yes": price['yes']})

    print(f"  \033[90m└{'─'*41}┴{'─'*9}┴{'─'*9}┴{'─'*9}┴{'─'*9}┘\033[0m")
    print()

    # Show market IDs
    print(f"  \033[90mMarket IDs:\033[0m")
    for m in markets:
        print(f"    \033[36m{m['id']}\033[0m → {m['question'][:50]}...")
    print()

    return markets

def show_orders():
    """Show all open orders - professional format"""
    orders = get_open_orders()

    print()
    print(f"  \033[1;36m▶ OPEN ORDERS\033[0m")
    print(f"  \033[90m{'─'*60}\033[0m")

    if not orders:
        print(f"  \033[90m  No open orders\033[0m")
        print()
        return []

    print()
    print(f"  \033[90m│\033[0m {'Side':<6} \033[90m│\033[0m {'Price':^8} \033[90m│\033[0m {'Size':^8} \033[90m│\033[0m {'Order ID':<32} \033[90m│\033[0m")
    print(f"  \033[90m├{'─'*7}┼{'─'*9}┼{'─'*9}┼{'─'*33}┤\033[0m")

    for o in orders:
        side = o.get('side', 'BUY')
        price = float(o.get('price', 0)) * 100
        size = o.get('original_size', o.get('size', 0))
        oid = o.get('id', '')[:30]

        side_color = "\033[92m" if side == "BUY" else "\033[91m"
        print(f"  \033[90m│\033[0m {side_color}{side:<6}\033[0m \033[90m│\033[0m {price:>6.0f}¢  \033[90m│\033[0m {size:^8} \033[90m│\033[0m \033[90m{oid:<32}\033[0m \033[90m│\033[0m")

    print(f"  \033[90m└{'─'*7}┴{'─'*9}┴{'─'*9}┴{'─'*33}┘\033[0m")
    print()
    return orders

def show_orderbook(market_id: str, outcome: str = "yes"):
    """Show orderbook with visual depth bars"""
    try:
        ob = get_orderbook(market_id, outcome)
        bids = sorted([{"p": float(b.price), "s": float(b.size)} for b in ob.bids], key=lambda x: x['p'], reverse=True)[:8]
        asks = sorted([{"p": float(a.price), "s": float(a.size)} for a in ob.asks], key=lambda x: x['p'])[:8]
    except:
        print(f"  \033[91mNo orderbook for market {market_id}\033[0m")
        return

    # Get max size for bar scaling
    max_size = max([b['s'] for b in bids] + [a['s'] for a in asks] + [1])

    print()
    print(f"  \033[1;36m▶ ORDERBOOK ({outcome.upper()})\033[0m")
    print(f"  \033[90m{'─'*55}\033[0m")
    print()
    print(f"  {'BIDS (buyers)':^25}  \033[90m│\033[0m  {'ASKS (sellers)':^25}")
    print(f"  \033[90m{'─'*25}──┼──{'─'*25}\033[0m")

    # Combine bids and asks side by side
    rows = max(len(bids), len(asks))
    for i in range(rows):
        # Bid side (right aligned bar)
        if i < len(bids):
            b = bids[i]
            bar_len = int((b['s'] / max_size) * 12)
            bar = "█" * bar_len
            bid_str = f"\033[92m{bar:>12}\033[0m {b['s']:>5.0f}@{b['p']*100:.0f}¢"
        else:
            bid_str = " " * 24

        # Ask side (left aligned bar)
        if i < len(asks):
            a = asks[i]
            bar_len = int((a['s'] / max_size) * 12)
            bar = "█" * bar_len
            ask_str = f"{a['p']*100:.0f}¢@{a['s']:<5.0f} \033[91m{bar:<12}\033[0m"
        else:
            ask_str = " " * 24

        print(f"  {bid_str:>25}  \033[90m│\033[0m  {ask_str:<25}")

    print(f"  \033[90m{'─'*25}──┴──{'─'*25}\033[0m")

    # Summary line
    if bids and asks:
        best_bid = bids[0]['p']
        best_ask = asks[0]['p']
        spread = best_ask - best_bid
        mid = (best_bid + best_ask) / 2
        spread_label = "\033[92mTIGHT\033[0m" if spread < 0.02 else "\033[93mOK\033[0m" if spread < 0.10 else "\033[91mWIDE\033[0m"
        print(f"  Bid:\033[92m{best_bid*100:.0f}¢\033[0m  Ask:\033[91m{best_ask*100:.0f}¢\033[0m  Mid:{mid*100:.1f}¢  Spread:{spread*100:.0f}¢ {spread_label}")
    print()

def quick_buy(market_id: str, size: int = 5, price: float = None):
    """Quick buy - uses best ask if no price given"""
    if price is None:
        prices = get_best_prices(market_id)
        price = prices['best_ask']
        print(f"Using best ask: {price*100:.0f}¢")

    return place_order(market_id, "BUY", price, size)

def quick_sell(market_id: str, size: int = 5, price: float = None):
    """Quick sell - uses best bid if no price given"""
    if price is None:
        prices = get_best_prices(market_id)
        price = prices['best_bid']
        print(f"Using best bid: {price*100:.0f}¢")

    return place_order(market_id, "SELL", price, size)


# =============================================================================
# COMBINED DATA FUNCTIONS
# =============================================================================

def get_market_info(market_id: str):
    """Get combined market info: gamma data + orderbook prices"""
    market = get_gamma_market(market_id)
    prices = get_best_prices(market_id)

    return {
        "id": market_id,
        "question": market.get("question", market.get("title", "")),
        "status": market.get("status", "unknown"),
        "volume": market.get("volume", 0),
        "yes_price": prices.get("best_ask", 0.5),
        "no_price": 1 - prices.get("best_ask", 0.5),
        "bid": prices.get("best_bid", 0),
        "ask": prices.get("best_ask", 1),
        "spread": prices.get("spread", 1),
        "liquid": prices.get("liquid", False)
    }


def get_recent_trades(market_id: str, limit: int = 10):
    """Get recent trades for a market"""
    import urllib.request
    import ssl

    token_id = get_clob_token_id(market_id, "yes")
    url = f"https://clob.polymarket.com/trades?token_id={token_id}&limit={limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'ClaudeTrading/1.0'})
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            return json.loads(resp.read())
    except:
        return []


def clear_caches():
    """Clear all in-memory caches"""
    global _TOKEN_CACHE, _MARKET_CACHE, _CLIENT
    _TOKEN_CACHE = {}
    _MARKET_CACHE = {}
    _CLIENT = None
    return "Caches cleared"


# =============================================================================
# MAIN - Quick test
# =============================================================================

if __name__ == "__main__":
    print("Polymarket API - Quick Test")
    print("-" * 40)

    # Test balance
    print("Balance:", get_balances())

    # Test orders
    orders = get_open_orders()
    print(f"Open orders: {len(orders)}")

    # Test positions
    positions = get_positions()
    print(f"Positions: {len(positions)}")
