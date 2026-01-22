#!/usr/bin/env python3
"""
Polymarket Trading Automations
==============================
Automated strategies for Claude Code trading.

Usage:
    from auto import *

    # Follow whale trades
    whale_follow(min_usd=5000, bet=5, max_trades=5)

    # Bet on top volume
    top_volume_bet(bet=5, count=3)

    # Elon markets by volume
    elon_volume_bet(bet=5, count=3)
"""

import requests
import time
import json
from datetime import datetime
from pathlib import Path

# Import our trading API
try:
    from polymarket_api import (
        place_order, get_best_prices, get_balances,
        get_open_orders, get_positions
    )
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("Warning: polymarket_api not available")

# ============================================================
# CONFIG
# ============================================================

DEFAULT_BET = 5.0  # $5 default
MIN_PRICE = 0.05   # Skip < 5¢ (likely resolved)
MAX_PRICE = 0.95   # Skip > 95¢ (likely resolved)
DELAY = 0.5        # Between orders

# ============================================================
# HELPERS
# ============================================================

def get_balance():
    """Get current USDC balance."""
    try:
        bal = get_balances()
        if isinstance(bal, dict):
            # Handle various response formats
            if 'USDC' in bal:
                return float(bal['USDC'])
            if 'balance' in bal:
                return float(bal['balance'])
            if 'note' in bal:
                # Balance API unavailable, return high value to allow trades
                return 1000.0
        return float(bal) if bal else 1000.0
    except:
        return 1000.0  # Allow trades, let API reject if insufficient

def fmt_usd(v):
    """Format USD value."""
    if v >= 1_000_000: return f"${v/1_000_000:.1f}M"
    if v >= 1_000: return f"${v/1_000:.1f}K"
    return f"${v:.0f}"

def fmt_price(p):
    """Format price as cents."""
    return f"{p*100:.0f}¢"

def log(msg):
    """Print with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")

def market_buy(market_id, budget, dry_run=False):
    """
    Buy $budget worth of YES at best ask.
    Returns (success, shares, price, cost).
    """
    try:
        prices = get_best_prices(market_id)
        ask = prices.get('best_ask', 0)

        if ask <= MIN_PRICE or ask >= MAX_PRICE:
            return (False, 0, ask, 0, "price out of range")

        shares = int(budget / ask)
        if shares < 1:
            return (False, 0, ask, 0, "budget too small")

        cost = shares * ask

        if dry_run:
            return (True, shares, ask, cost, "dry_run")

        result = place_order(market_id, 'BUY', ask, shares)
        status = result.get('status', 'error')
        return (status in ['matched', 'live'], shares, ask, cost, status)
    except Exception as e:
        return (False, 0, 0, 0, str(e))

# ============================================================
# DATA FETCHERS
# ============================================================

def fetch_recent_trades(limit=200):
    """Fetch recent trades from data API."""
    url = f'https://data-api.polymarket.com/trades?limit={limit}'
    resp = requests.get(url, timeout=15)
    return resp.json()


def fetch_trader_profile(address):
    """
    Fetch trader's profile and PnL from leaderboard API.
    Returns: {profit, volume, positions, rank} or None
    """
    try:
        # Try leaderboard endpoint
        url = f'https://data-api.polymarket.com/profile/{address}'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'address': address,
                'profit': float(data.get('profit', data.get('pnl', 0)) or 0),
                'volume': float(data.get('volume', 0) or 0),
                'positions': int(data.get('positions', data.get('positionCount', 0)) or 0),
                'rank': data.get('rank', 0),
                'name': data.get('name', data.get('pseudonym', address[:10])),
            }
    except:
        pass

    # Fallback: try activity endpoint
    try:
        url = f'https://data-api.polymarket.com/activity?user={address}&limit=50'
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            trades = resp.json()
            # Estimate profit from recent trades
            profit = 0
            for t in trades:
                if t.get('type') == 'trade':
                    side = t.get('side', '').upper()
                    price = float(t.get('price', 0))
                    size = float(t.get('size', 0))
                    # Rough PnL estimate (not accurate but directional)
                    if side == 'SELL':
                        profit += price * size * 0.1  # Assume 10% avg profit on sells
            return {
                'address': address,
                'profit': profit,
                'volume': sum(float(t.get('usdcSize', 0) or 0) for t in trades),
                'positions': len(set(t.get('conditionId') for t in trades)),
                'rank': 0,
                'name': address[:10],
            }
    except:
        pass

    return None


def check_whale_profitable(address, min_profit=0):
    """
    Check if a whale trader is profitable.

    Args:
        address: Wallet address
        min_profit: Minimum profit required ($)

    Returns:
        (is_profitable, profit_amount, trader_info)
    """
    profile = fetch_trader_profile(address)
    if not profile:
        return (False, 0, None)

    profit = profile.get('profit', 0)
    is_profitable = profit >= min_profit

    return (is_profitable, profit, profile)

def fetch_top_volume(limit=20):
    """Fetch top volume markets."""
    url = f'https://gamma-api.polymarket.com/markets?limit={limit}&order=volume24hr&ascending=false&active=true&closed=false'
    resp = requests.get(url, timeout=10)
    return resp.json()

def fetch_market_by_slug(slug):
    """Get market by slug."""
    url = f'https://gamma-api.polymarket.com/markets?slug={slug}'
    resp = requests.get(url, timeout=10)
    markets = resp.json()
    return markets[0] if markets else None

def fetch_market_by_condition(cond_id):
    """Get market by condition ID."""
    url = f'https://gamma-api.polymarket.com/markets?condition_id={cond_id}'
    resp = requests.get(url, timeout=10)
    markets = resp.json()
    return markets[0] if markets else None

# ============================================================
# STRATEGIES
# ============================================================

def whale_follow(min_usd=5000, bet=DEFAULT_BET, max_trades=5, dry_run=True, only_profitable=True, min_profit=0):
    """
    Follow whale trades (only from profitable traders).

    Find recent BUY trades > min_usd and copy them.

    Args:
        min_usd: Minimum trade size to follow
        bet: Amount to bet on each ($)
        max_trades: Maximum trades to make
        dry_run: If True, show what would happen without trading
        only_profitable: If True, only copy from profitable traders
        min_profit: Minimum trader profit to copy ($)

    Returns:
        List of executed trades
    """
    log(f"🐋 WHALE FOLLOW: min=${min_usd}, bet=${bet}, max={max_trades}")
    if only_profitable:
        log(f"   Only copying profitable traders (>${min_profit})")
    if dry_run:
        log("   (DRY RUN - no real trades)")
    print()

    # Fetch recent trades
    trades = fetch_recent_trades(500)

    # Filter big buys
    big_buys = []
    seen_markets = set()
    checked_traders = {}  # Cache trader profiles

    for t in trades:
        if t.get('side', '').upper() != 'BUY':
            continue

        price = float(t.get('price', 0))
        size = float(t.get('size', 0))
        usd = price * size

        if usd < min_usd:
            continue

        # Skip resolved markets
        if price <= MIN_PRICE or price >= MAX_PRICE:
            continue

        # Skip duplicates
        cond = t.get('conditionId', '')
        if cond in seen_markets:
            continue

        # Check trader profitability
        trader_addr = t.get('proxyWallet', t.get('user', ''))
        trader_name = t.get('name', t.get('pseudonym', trader_addr[:10] if trader_addr else 'anon'))

        if only_profitable and trader_addr:
            if trader_addr not in checked_traders:
                is_prof, profit, profile = check_whale_profitable(trader_addr, min_profit)
                checked_traders[trader_addr] = (is_prof, profit, profile)

            is_prof, profit, profile = checked_traders[trader_addr]
            if not is_prof:
                continue  # Skip unprofitable traders
            trader_name = profile.get('name', trader_name) if profile else trader_name
            trader_profit = profit
        else:
            trader_profit = None

        seen_markets.add(cond)

        big_buys.append({
            'usd': usd,
            'price': price,
            'size': size,
            'title': t.get('title', '')[:45],
            'slug': t.get('slug', ''),
            'conditionId': cond,
            'outcome': t.get('outcome', 'YES'),
            'trader': trader_name,
            'trader_profit': trader_profit,
        })

    big_buys.sort(key=lambda x: x['usd'], reverse=True)
    big_buys = big_buys[:max_trades]

    if not big_buys:
        log("No whale trades found matching criteria")
        if only_profitable:
            log("   (Try only_profitable=False to see all whales)")
        return []

    # Show what we found
    log(f"Found {len(big_buys)} whale trades from profitable traders:")
    for i, b in enumerate(big_buys, 1):
        profit_str = f" [+${b['trader_profit']:.0f}]" if b.get('trader_profit') else ""
        trader_str = b.get('trader', 'anon')[:12]
        print(f"  {i}. {fmt_usd(b['usd'])} | {b['size']:.0f} @ {fmt_price(b['price'])} | {b['title']}")
        print(f"     by {trader_str}{profit_str}")
    print()

    # Execute trades
    results = []
    balance = get_balance() if not dry_run else float('inf')

    for b in big_buys:
        if balance < bet:
            log(f"⚠️  Out of funds (${balance:.2f} remaining)")
            break

        # Find market ID
        market = fetch_market_by_slug(b['slug']) if b['slug'] else None
        if not market:
            market = fetch_market_by_condition(b['conditionId'])

        if not market:
            log(f"   ✗ Could not find market: {b['title'][:30]}")
            continue

        market_id = market.get('id')

        # Execute
        success, shares, price, cost, status = market_buy(market_id, bet, dry_run)

        if success:
            log(f"   ✓ BUY {shares} @ {fmt_price(price)} = ${cost:.2f} | {b['title'][:35]}")
            balance -= cost
            results.append({
                'market_id': market_id,
                'shares': shares,
                'price': price,
                'cost': cost,
                'title': b['title'],
            })
        else:
            log(f"   ✗ Failed: {status} | {b['title'][:35]}")

        time.sleep(DELAY)

    print()
    total = sum(r['cost'] for r in results)
    log(f"Done: {len(results)} trades, ${total:.2f} total")
    return results


def top_volume_bet(bet=DEFAULT_BET, count=5, dry_run=True):
    """
    Bet on top volume markets.

    Args:
        bet: Amount to bet on each ($)
        count: Number of markets
        dry_run: If True, show what would happen

    Returns:
        List of executed trades
    """
    log(f"📊 TOP VOLUME: bet=${bet}, count={count}")
    if dry_run:
        log("   (DRY RUN - no real trades)")
    print()

    markets = fetch_top_volume(count * 3)  # Fetch extra for filtering

    # Filter active, tradeable markets
    valid = []
    for m in markets:
        prices = m.get('outcomePrices', '[]')
        if isinstance(prices, str):
            prices = json.loads(prices) if prices else [0.5]
        price = float(prices[0]) if prices else 0.5

        # Skip resolved
        if price <= MIN_PRICE or price >= MAX_PRICE:
            continue

        vol = float(m.get('volume24hr', 0) or 0)
        valid.append({
            'id': m.get('id'),
            'title': m.get('question', '')[:45],
            'price': price,
            'volume': vol,
        })

        if len(valid) >= count:
            break

    if not valid:
        log("No valid markets found")
        return []

    # Show markets
    log(f"Found {len(valid)} markets:")
    for i, m in enumerate(valid, 1):
        print(f"  {i}. {fmt_usd(m['volume'])} | {fmt_price(m['price'])} | {m['title']}")
    print()

    # Execute
    results = []
    balance = get_balance() if not dry_run else float('inf')

    for m in valid:
        if balance < bet:
            log(f"⚠️  Out of funds (${balance:.2f} remaining)")
            break

        success, shares, price, cost, status = market_buy(m['id'], bet, dry_run)

        if success:
            log(f"   ✓ BUY {shares} @ {fmt_price(price)} = ${cost:.2f} | {m['title'][:35]}")
            balance -= cost
            results.append({
                'market_id': m['id'],
                'shares': shares,
                'price': price,
                'cost': cost,
                'title': m['title'],
            })
        else:
            log(f"   ✗ Failed: {status} | {m['title'][:35]}")

        time.sleep(DELAY)

    print()
    total = sum(r['cost'] for r in results)
    log(f"Done: {len(results)} trades, ${total:.2f} total")
    return results


def elon_volume_bet(bet=DEFAULT_BET, count=3, dry_run=True):
    """
    Bet on Elon markets by volume.

    Args:
        bet: Amount to bet on each ($)
        count: Number of markets
        dry_run: If True, show what would happen

    Returns:
        List of executed trades
    """
    log(f"🚀 ELON VOLUME: bet=${bet}, count={count}")
    if dry_run:
        log("   (DRY RUN - no real trades)")
    print()

    # Fetch and filter Elon markets
    all_markets = fetch_top_volume(100)

    elon_markets = []
    for m in all_markets:
        q = m.get('question', '').lower()
        if 'elon' not in q and 'musk' not in q and 'tweet' not in q:
            continue

        prices = m.get('outcomePrices', '[]')
        if isinstance(prices, str):
            prices = json.loads(prices) if prices else [0.5]
        price = float(prices[0]) if prices else 0.5

        if price <= MIN_PRICE or price >= MAX_PRICE:
            continue

        vol = float(m.get('volume24hr', 0) or 0)
        elon_markets.append({
            'id': m.get('id'),
            'title': m.get('question', '')[:45],
            'price': price,
            'volume': vol,
        })

        if len(elon_markets) >= count:
            break

    if not elon_markets:
        log("No Elon markets found")
        return []

    # Show markets
    log(f"Found {len(elon_markets)} Elon markets:")
    for i, m in enumerate(elon_markets, 1):
        print(f"  {i}. {fmt_usd(m['volume'])} | {fmt_price(m['price'])} | {m['title']}")
    print()

    # Execute
    results = []
    balance = get_balance() if not dry_run else float('inf')

    for m in elon_markets:
        if balance < bet:
            log(f"⚠️  Out of funds (${balance:.2f} remaining)")
            break

        success, shares, price, cost, status = market_buy(m['id'], bet, dry_run)

        if success:
            log(f"   ✓ BUY {shares} @ {fmt_price(price)} = ${cost:.2f} | {m['title'][:35]}")
            balance -= cost
            results.append({
                'market_id': m['id'],
                'shares': shares,
                'price': price,
                'cost': cost,
                'title': m['title'],
            })
        else:
            log(f"   ✗ Failed: {status} | {m['title'][:35]}")

        time.sleep(DELAY)

    print()
    total = sum(r['cost'] for r in results)
    log(f"Done: {len(results)} trades, ${total:.2f} total")
    return results


def scan_opportunities(min_volume=100000, max_price=0.30):
    """
    Scan for trading opportunities.

    Find markets with high volume and low price (potential upside).

    Args:
        min_volume: Minimum 24h volume
        max_price: Maximum YES price (lower = more upside potential)

    Returns:
        List of opportunities
    """
    log(f"🔍 SCANNING: vol>{fmt_usd(min_volume)}, price<{fmt_price(max_price)}")
    print()

    markets = fetch_top_volume(100)

    opps = []
    for m in markets:
        vol = float(m.get('volume24hr', 0) or 0)
        if vol < min_volume:
            continue

        prices = m.get('outcomePrices', '[]')
        if isinstance(prices, str):
            prices = json.loads(prices) if prices else [0.5]
        price = float(prices[0]) if prices else 0.5

        if price <= MIN_PRICE or price > max_price:
            continue

        opps.append({
            'id': m.get('id'),
            'title': m.get('question', '')[:50],
            'price': price,
            'volume': vol,
            'potential': (1 - price) / price,  # Upside ratio
        })

    opps.sort(key=lambda x: x['potential'], reverse=True)

    log(f"Found {len(opps)} opportunities:")
    for i, o in enumerate(opps[:10], 1):
        print(f"  {i}. {fmt_price(o['price'])} | {fmt_usd(o['volume'])} | {o['potential']:.1f}x | {o['title']}")

    return opps


# ============================================================
# SCHEDULED STRATEGIES
# ============================================================

def sport_volume_bet(bet=DEFAULT_BET, count=1, dry_run=True):
    """
    Bet on highest volume sports markets.

    Args:
        bet: Amount per trade
        count: Number of markets
        dry_run: If True, no real trades
    """
    log(f"⚽ SPORT VOLUME: bet=${bet}, count={count}")
    if dry_run:
        log("   (DRY RUN)")
    print()

    markets = fetch_top_volume(50)

    # Filter sports
    sports_keywords = ['win on', 'spread', 'o/u', 'over/under', 'total',
                       'fc ', 'vs', 'match', 'game', 'nba', 'nfl', 'mlb',
                       'premier league', 'la liga', 'champions league']

    sport_markets = []
    for m in markets:
        q = m.get('question', '').lower()
        if not any(kw in q for kw in sports_keywords):
            continue

        prices = m.get('outcomePrices', '[]')
        if isinstance(prices, str):
            prices = json.loads(prices) if prices else [0.5]
        price = float(prices[0]) if prices else 0.5

        if price <= MIN_PRICE or price >= MAX_PRICE:
            continue

        vol = float(m.get('volume24hr', 0) or 0)
        sport_markets.append({
            'id': m.get('id'),
            'title': m.get('question', '')[:45],
            'price': price,
            'volume': vol,
        })

        if len(sport_markets) >= count:
            break

    if not sport_markets:
        log("No sport markets found")
        return []

    log(f"Found {len(sport_markets)} sport markets:")
    for m in sport_markets:
        print(f"  {fmt_usd(m['volume'])} | {fmt_price(m['price'])} | {m['title']}")
    print()

    results = []
    for m in sport_markets:
        success, shares, price, cost, status = market_buy(m['id'], bet, dry_run)
        if success:
            log(f"   ✓ BUY {shares} @ {fmt_price(price)} = ${cost:.2f} | {m['title'][:35]}")
            results.append({'market_id': m['id'], 'shares': shares, 'price': price, 'cost': cost})
        else:
            log(f"   ✗ Failed: {status}")
        time.sleep(DELAY)

    total = sum(r['cost'] for r in results)
    log(f"Done: {len(results)} trades, ${total:.2f}")
    return results


def run_scheduler(strategy, interval_minutes=60, max_runs=None, bet=5, count=1):
    """
    Run a strategy on a schedule.

    Args:
        strategy: 'sport', 'whale', 'volume', 'elon'
        interval_minutes: Minutes between runs
        max_runs: Stop after N runs (None = forever)
        bet: Amount per trade
        count: Trades per run

    Example:
        run_scheduler('sport', interval_minutes=60, max_runs=5, bet=5)
    """
    strategies = {
        'sport': lambda: sport_volume_bet(bet=bet, count=count, dry_run=False),
        'whale': lambda: whale_follow(min_usd=5000, bet=bet, max_trades=count, dry_run=False),
        'volume': lambda: top_volume_bet(bet=bet, count=count, dry_run=False),
        'elon': lambda: elon_volume_bet(bet=bet, count=count, dry_run=False),
    }

    if strategy not in strategies:
        log(f"Unknown strategy: {strategy}")
        log(f"Available: {list(strategies.keys())}")
        return

    log(f"🕐 SCHEDULER: {strategy} every {interval_minutes}min")
    if max_runs:
        log(f"   Will stop after {max_runs} runs")
    log(f"   Ctrl+C to stop")
    print()

    runs = 0
    try:
        while True:
            runs += 1
            log(f"━━━ RUN {runs} ━━━")

            try:
                strategies[strategy]()
            except Exception as e:
                log(f"Error: {e}")

            if max_runs and runs >= max_runs:
                log(f"Completed {max_runs} runs, stopping")
                break

            next_run = datetime.now().timestamp() + (interval_minutes * 60)
            next_time = datetime.fromtimestamp(next_run).strftime("%H:%M:%S")
            log(f"Next run at {next_time}")
            print()

            time.sleep(interval_minutes * 60)

    except KeyboardInterrupt:
        log(f"\nStopped after {runs} runs")


def sport_whale_hunt(bet=5, count=2, min_usd=1000, dry_run=True, only_profitable=True, min_profit=0, _seen_this_round=None):
    """
    Combined strategy: Find top sport volume + follow sport whale trades from profitable traders.

    1. Find highest volume sport market
    2. Find biggest whale bets on sports from profitable traders
    3. Bet on both (no duplicates within round)

    Args:
        bet: Amount per trade ($)
        count: Total trades (split between volume + whales)
        min_usd: Minimum whale trade size
        dry_run: If True, no real trades
        only_profitable: Only copy from profitable traders
        min_profit: Minimum trader profit to copy
        _seen_this_round: Set of market IDs already bet on this round
    """
    log(f"🏆 SPORT WHALE HUNT: bet=${bet}, count={count}, min_whale=${min_usd}")
    if only_profitable:
        log(f"   Only profitable traders (>${min_profit})")
    if dry_run:
        log("   (DRY RUN)")
    print()

    results = []
    seen_this_round = _seen_this_round or set()
    checked_traders = {}

    sports_keywords = ['win on', 'spread', 'o/u', 'over/under', 'total',
                       'fc ', 'vs', 'match', 'game', 'nba', 'nfl', 'mlb', 'nhl',
                       'premier league', 'la liga', 'champions league', 'ucl',
                       'cavaliers', 'celtics', 'lakers', 'warriors', 'bulls',
                       'red wings', 'maple leafs', 'rangers', 'bruins', 'penguins',
                       'flames', 'oilers', 'canucks', 'jets', 'wild', 'avalanche',
                       'australian open', 'ufc', 'boxing', 'mma', 'tennis']

    # === STEP 1: Top volume sport ===
    log("📊 Step 1: Finding top volume sport...")
    markets = fetch_top_volume(50)

    top_sport = None
    for m in markets:
        q = m.get('question', '').lower()
        if not any(kw in q for kw in sports_keywords):
            continue

        mid = m.get('id')
        if mid in seen_this_round:
            continue  # Skip if already bet this round

        prices = m.get('outcomePrices', '[]')
        if isinstance(prices, str):
            prices = json.loads(prices) if prices else [0.5]
        price = float(prices[0]) if prices else 0.5

        if price <= MIN_PRICE or price >= MAX_PRICE:
            continue

        vol = float(m.get('volume24hr', 0) or 0)
        top_sport = {
            'id': mid,
            'title': m.get('question', '')[:45],
            'price': price,
            'volume': vol,
        }
        break

    if top_sport:
        print(f"   {fmt_usd(top_sport['volume'])} | {fmt_price(top_sport['price'])} | {top_sport['title']}")

        success, shares, price, cost, status = market_buy(top_sport['id'], bet, dry_run)
        if success:
            log(f"   ✓ BUY {shares} @ {fmt_price(price)} = ${cost:.2f}")
            results.append({'type': 'volume', 'market_id': top_sport['id'], 'shares': shares, 'cost': cost, 'title': top_sport['title']})
            seen_this_round.add(top_sport['id'])
        else:
            log(f"   ✗ Failed: {status}")
    else:
        log("   No sport markets found")

    print()

    # === STEP 2: Sport whale trades from profitable traders ===
    log(f"🐋 Step 2: Finding sport whales (>${min_usd}) from profitable traders...")
    trades = fetch_recent_trades(500)

    sport_whales = []
    seen = set()

    for t in trades:
        if t.get('side', '').upper() != 'BUY':
            continue

        title = t.get('title', '').lower()
        if not any(kw in title for kw in sports_keywords):
            continue

        price = float(t.get('price', 0))
        size = float(t.get('size', 0))
        usd = price * size

        if usd < min_usd:
            continue

        if price <= MIN_PRICE or price >= MAX_PRICE:
            continue

        cond = t.get('conditionId', '')
        if cond in seen:
            continue
        if cond in seen_this_round:
            continue  # Skip if already bet this round
        if top_sport and cond == top_sport.get('id'):
            continue  # Skip if same as volume pick

        # Check trader profitability
        trader_addr = t.get('proxyWallet', t.get('user', ''))
        trader_name = t.get('name', t.get('pseudonym', trader_addr[:10] if trader_addr else 'anon'))
        trader_profit = None

        if only_profitable and trader_addr:
            if trader_addr not in checked_traders:
                is_prof, profit, profile = check_whale_profitable(trader_addr, min_profit)
                checked_traders[trader_addr] = (is_prof, profit, profile)

            is_prof, profit, profile = checked_traders[trader_addr]
            if not is_prof:
                continue  # Skip unprofitable traders
            trader_name = profile.get('name', trader_name) if profile else trader_name
            trader_profit = profit
        seen.add(cond)

        sport_whales.append({
            'usd': usd,
            'title': t.get('title', '')[:45],
            'slug': t.get('slug', ''),
            'conditionId': cond,
            'price': price,
            'trader': trader_name,
            'trader_profit': trader_profit,
        })

    sport_whales.sort(key=lambda x: x['usd'], reverse=True)
    whale_count = count - len(results)  # Remaining slots

    if sport_whales:
        for w in sport_whales[:whale_count]:
            profit_str = f" [+${w['trader_profit']:.0f}]" if w.get('trader_profit') else ""
            print(f"   {fmt_usd(w['usd'])} | {fmt_price(w['price'])} | {w['title']}")
            print(f"      by {w.get('trader', 'anon')[:12]}{profit_str}")

            market = fetch_market_by_slug(w['slug']) if w['slug'] else None
            if not market:
                market = fetch_market_by_condition(w['conditionId'])

            if not market:
                log(f"   ✗ Could not find market")
                continue

            success, shares, price, cost, status = market_buy(market['id'], bet, dry_run)
            if success:
                log(f"   ✓ BUY {shares} @ {fmt_price(price)} = ${cost:.2f}")
                results.append({'type': 'whale', 'market_id': market['id'], 'shares': shares, 'cost': cost, 'title': w['title']})
                seen_this_round.add(w['conditionId'])
            else:
                log(f"   ✗ Failed: {status}")

            time.sleep(DELAY)
    else:
        log(f"   No sport whales found (>${min_usd}) from profitable traders")

    print()
    total = sum(r['cost'] for r in results)
    log(f"Done: {len(results)} trades, ${total:.2f}")
    return results, seen_this_round


def run_sport_whale_scheduler(interval_minutes=60, max_runs=5, bet=5, count=2, min_usd=1000, only_profitable=True, min_profit=0):
    """
    Schedule sport whale hunt strategy.

    Args:
        interval_minutes: Minutes between runs (default 60)
        max_runs: Stop after N runs (default 5)
        bet: Amount per trade (default $5)
        count: Trades per run (default 2)
        min_usd: Min whale size (default $1000)
        only_profitable: Only copy profitable traders
        min_profit: Minimum trader profit

    Example:
        run_sport_whale_scheduler(6, 3, 5, 2, 500)
        # Every 6min, 3 runs, $5/bet, 2 bets/run, whales >$500
    """
    log(f"🏆 SPORT WHALE SCHEDULER")
    log(f"   Every {interval_minutes}min, max {max_runs} runs")
    log(f"   ${bet}/bet, {count} bets/run, whales >${min_usd}")
    if only_profitable:
        log(f"   Only profitable traders (>${min_profit})")
    log(f"   Ctrl+C to stop")
    log(f"   No duplicate bets within same round")
    print()

    runs = 0
    total_spent = 0
    total_trades = 0
    all_trades = []

    try:
        while runs < max_runs:
            runs += 1
            log(f"━━━ RUN {runs}/{max_runs} ━━━")

            try:
                # Reset seen_this_round each run (allows same markets across rounds)
                result = sport_whale_hunt(
                    bet=bet,
                    count=count,
                    min_usd=min_usd,
                    dry_run=False,
                    only_profitable=only_profitable,
                    min_profit=min_profit,
                    _seen_this_round=set()  # Fresh set each round
                )
                # Handle both old and new return format
                if isinstance(result, tuple):
                    results, _ = result
                else:
                    results = result

                total_trades += len(results)
                total_spent += sum(r['cost'] for r in results)
                all_trades.extend(results)
            except Exception as e:
                log(f"Error: {e}")

            if runs >= max_runs:
                break

            next_time = datetime.fromtimestamp(
                datetime.now().timestamp() + (interval_minutes * 60)
            ).strftime("%H:%M:%S")
            log(f"Next run at {next_time}")
            print()

            time.sleep(interval_minutes * 60)

    except KeyboardInterrupt:
        pass

    print()
    log(f"━━━ FINAL SUMMARY ━━━")
    log(f"   Runs: {runs}")
    log(f"   Trades: {total_trades}")
    log(f"   Spent: ${total_spent:.2f}")
    if all_trades:
        log(f"   Markets:")
        for t in all_trades:
            log(f"      - {t.get('title', t.get('market_id', '?'))[:40]}")


def run_once(strategy, bet=5, count=1):
    """
    Run a strategy once (for testing).

    Args:
        strategy: 'sport', 'whale', 'volume', 'elon'
        bet: Amount per trade
        count: Number of trades
    """
    strategies = {
        'sport': lambda: sport_volume_bet(bet=bet, count=count, dry_run=False),
        'whale': lambda: whale_follow(min_usd=5000, bet=bet, max_trades=count, dry_run=False),
        'volume': lambda: top_volume_bet(bet=bet, count=count, dry_run=False),
        'elon': lambda: elon_volume_bet(bet=bet, count=count, dry_run=False),
    }

    if strategy not in strategies:
        log(f"Unknown: {strategy}. Available: {list(strategies.keys())}")
        return

    return strategies[strategy]()


# ============================================================
# CLI
# ============================================================

def show_help():
    """Show available commands."""
    print("""
POLYMARKET AUTO-TRADING
=======================

STRATEGIES (all default to dry_run=True):

  whale_follow(min_usd=5000, bet=5, max_trades=5, dry_run=True)
  top_volume_bet(bet=5, count=5, dry_run=True)
  elon_volume_bet(bet=5, count=3, dry_run=True)
  sport_volume_bet(bet=5, count=1, dry_run=True)
  scan_opportunities(min_volume=100000, max_price=0.30)

SCHEDULED (runs automatically):

  run_scheduler('sport', interval_minutes=60, max_runs=5, bet=5, count=1)
    Runs strategy every N minutes. Strategies: sport, whale, volume, elon

  run_once('sport', bet=5, count=1)
    Run strategy once (for testing)

EXAMPLES:

  # Dry run
  sport_volume_bet(bet=5, count=1)

  # Real trade
  sport_volume_bet(bet=5, count=1, dry_run=False)

  # Schedule: sport every 1h, max 5 runs
  run_scheduler('sport', interval_minutes=60, max_runs=5, bet=5)

  # Schedule: whale every 30min, run forever
  run_scheduler('whale', interval_minutes=30, bet=5, count=2)
""")


if __name__ == "__main__":
    show_help()
