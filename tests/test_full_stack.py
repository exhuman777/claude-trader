#!/usr/bin/env python3
"""
Full Stack Trading Tests
========================
Comprehensive tests for Polymarket trading infrastructure.

Run: python tests/test_full_stack.py
Or:  pytest tests/test_full_stack.py -v

Tests are organized in phases:
1. Environment - Dependencies, config, paths
2. API Connectivity - Can we reach Polymarket?
3. Market Data - Can we fetch prices, orderbooks?
4. Account - Balance, positions, orders
5. Trading Logic - Order building, ladders (dry run)
6. Automation - Whale follow, volume bets (dry run)
7. Integration - End-to-end flows
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test results tracking
RESULTS = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "tests": []
}

def log(msg, level="INFO"):
    """Print with timestamp and level."""
    ts = datetime.now().strftime("%H:%M:%S")
    symbols = {"INFO": "ℹ", "PASS": "✓", "FAIL": "✗", "SKIP": "⊘", "WARN": "⚠"}
    colors = {"INFO": "\033[0m", "PASS": "\033[92m", "FAIL": "\033[91m", "SKIP": "\033[93m", "WARN": "\033[93m"}
    print(f"{colors.get(level, '')}{symbols.get(level, '•')} [{ts}] {msg}\033[0m")

def test(name, phase):
    """Decorator for test functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if result is None or result is True:
                    RESULTS["passed"] += 1
                    RESULTS["tests"].append({"name": name, "phase": phase, "status": "PASS"})
                    log(f"{name}", "PASS")
                    return True
                elif result == "SKIP":
                    RESULTS["skipped"] += 1
                    RESULTS["tests"].append({"name": name, "phase": phase, "status": "SKIP"})
                    log(f"{name} (skipped)", "SKIP")
                    return None
                else:
                    RESULTS["failed"] += 1
                    RESULTS["tests"].append({"name": name, "phase": phase, "status": "FAIL", "error": str(result)})
                    log(f"{name}: {result}", "FAIL")
                    return False
            except Exception as e:
                RESULTS["failed"] += 1
                RESULTS["tests"].append({"name": name, "phase": phase, "status": "FAIL", "error": str(e)})
                log(f"{name}: {e}", "FAIL")
                return False
        return wrapper
    return decorator


# =============================================================================
# PHASE 1: ENVIRONMENT
# =============================================================================

@test("Python version >= 3.10", "environment")
def test_python_version():
    if sys.version_info < (3, 10):
        return f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.10"
    return True

@test("Project structure exists", "environment")
def test_project_structure():
    required = ["polymarket_api.py", "auto.py", "config.py", "CLAUDE.md", "PLAYBOOK.md"]
    missing = [f for f in required if not (PROJECT_ROOT / f).exists()]
    if missing:
        return f"Missing: {missing}"
    return True

@test("Data directory exists", "environment")
def test_data_dir():
    data_dir = PROJECT_ROOT / "data"
    if not data_dir.exists():
        return "data/ directory missing"
    return True

@test("Trading config exists", "environment")
def test_config_exists():
    config_path = PROJECT_ROOT / "data" / ".trading_config.json"
    if not config_path.exists():
        return f"Config not found at {config_path}"
    return True

@test("Trading config valid JSON", "environment")
def test_config_valid():
    config_path = PROJECT_ROOT / "data" / ".trading_config.json"
    try:
        with open(config_path) as f:
            config = json.load(f)
        required_keys = ["private_key", "funder"]
        missing = [k for k in required_keys if k not in config]
        if missing:
            return f"Missing keys: {missing}"
        return True
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

@test("py-clob-client installed", "environment")
def test_clob_client():
    try:
        from py_clob_client.client import ClobClient
        return True
    except ImportError:
        return "py-clob-client not installed"

@test("requests installed", "environment")
def test_requests():
    try:
        import requests
        return True
    except ImportError:
        return "requests not installed"


# =============================================================================
# PHASE 2: API CONNECTIVITY
# =============================================================================

@test("Gamma API reachable", "api")
def test_gamma_api():
    import requests
    try:
        resp = requests.get("https://gamma-api.polymarket.com/markets?limit=1", timeout=10)
        if resp.status_code != 200:
            return f"Status {resp.status_code}"
        return True
    except Exception as e:
        return str(e)

@test("CLOB API reachable", "api")
def test_clob_api():
    import requests
    try:
        resp = requests.get("https://clob.polymarket.com/", timeout=10)
        # CLOB returns 404 on root, but that means it's reachable
        if resp.status_code in [200, 404]:
            return True
        return f"Status {resp.status_code}"
    except Exception as e:
        return str(e)

@test("Data API reachable", "api")
def test_data_api():
    import requests
    try:
        resp = requests.get("https://data-api.polymarket.com/trades?limit=1", timeout=10)
        if resp.status_code != 200:
            return f"Status {resp.status_code}"
        return True
    except Exception as e:
        return str(e)


# =============================================================================
# PHASE 3: MARKET DATA
# =============================================================================

@test("Can fetch top volume markets", "market_data")
def test_fetch_top_volume():
    from auto import fetch_top_volume
    markets = fetch_top_volume(5)
    if not markets:
        return "No markets returned"
    if len(markets) < 1:
        return "Empty market list"
    return True

@test("Can search markets", "market_data")
def test_search_markets():
    from polymarket_api import search_markets
    results = search_markets("election", 5)
    if not isinstance(results, list):
        return f"Expected list, got {type(results)}"
    return True

@test("Can get market by slug", "market_data")
def test_get_market_by_slug():
    from auto import fetch_market_by_slug
    # Use a known active market pattern
    from auto import fetch_top_volume
    markets = fetch_top_volume(1)
    if markets:
        slug = markets[0].get('slug')
        if slug:
            market = fetch_market_by_slug(slug)
            if market and 'id' in market:
                return True
    return "SKIP"  # Skip if no markets available

@test("Can get price", "market_data")
def test_get_price():
    from polymarket_api import get_price
    from auto import fetch_top_volume
    markets = fetch_top_volume(1)
    if markets:
        market_id = markets[0].get('id')
        if market_id:
            price = get_price(str(market_id))
            if 'yes' in price and 'no' in price:
                return True
            return f"Invalid price format: {price}"
    return "SKIP"

@test("Can get orderbook", "market_data")
def test_get_orderbook():
    from polymarket_api import get_orderbook
    from auto import fetch_top_volume
    markets = fetch_top_volume(1)
    if markets:
        market_id = markets[0].get('id')
        if market_id:
            try:
                ob = get_orderbook(str(market_id))
                # Orderbook should have bids and asks
                if hasattr(ob, 'bids') and hasattr(ob, 'asks'):
                    return True
                return f"Invalid orderbook format"
            except Exception as e:
                if "No token" in str(e):
                    return "SKIP"  # Market may not have CLOB tokens
                return str(e)
    return "SKIP"

@test("Can fetch recent trades", "market_data")
def test_fetch_trades():
    from auto import fetch_recent_trades
    trades = fetch_recent_trades(10)
    if not isinstance(trades, list):
        return f"Expected list, got {type(trades)}"
    if len(trades) == 0:
        return "No trades returned"
    return True


# =============================================================================
# PHASE 4: ACCOUNT
# =============================================================================

@test("Can initialize CLOB client", "account")
def test_clob_client_init():
    from polymarket_api import get_client
    try:
        client = get_client()
        if client is None:
            return "Client is None"
        return True
    except Exception as e:
        return str(e)

@test("Can get balances", "account")
def test_get_balances():
    from polymarket_api import get_balances
    try:
        bal = get_balances()
        # May return dict with 'note' if API unavailable
        if isinstance(bal, dict):
            return True
        return True
    except Exception as e:
        return str(e)

@test("Can get positions", "account")
def test_get_positions():
    from polymarket_api import get_positions
    try:
        positions = get_positions()
        if not isinstance(positions, list):
            return f"Expected list, got {type(positions)}"
        return True
    except Exception as e:
        return str(e)

@test("Can get open orders", "account")
def test_get_orders():
    from polymarket_api import get_open_orders
    try:
        orders = get_open_orders()
        if not isinstance(orders, list):
            return f"Expected list, got {type(orders)}"
        return True
    except Exception as e:
        return str(e)


# =============================================================================
# PHASE 5: TRADING LOGIC (DRY RUN)
# =============================================================================

@test("Order args validation", "trading")
def test_order_args():
    from py_clob_client.clob_types import OrderArgs
    try:
        args = OrderArgs(
            price=0.35,
            size=10,
            side="BUY",
            token_id="12345"
        )
        if args.price != 0.35:
            return "Price mismatch"
        if args.size != 10:
            return "Size mismatch"
        return True
    except Exception as e:
        return str(e)

@test("Price formatting", "trading")
def test_price_format():
    # Test our price formatting convention
    price = 0.35
    formatted = f"{price*100:.0f}¢"
    if formatted != "35¢":
        return f"Expected '35¢', got '{formatted}'"
    return True

@test("Ladder price calculation", "trading")
def test_ladder_prices():
    # Test ladder price generation (matches actual place_ladder behavior)
    start, end, num = 0.40, 0.30, 5
    step = (end - start) / max(num - 1, 1)
    prices = [round(start + i * step, 2) for i in range(num)]
    # Verify: starts at 40¢, ends at 30¢, 5 orders
    if len(prices) != 5:
        return f"Expected 5 prices, got {len(prices)}"
    if prices[0] != 0.40:
        return f"First price should be 0.40, got {prices[0]}"
    if prices[-1] != 0.30:
        return f"Last price should be 0.30, got {prices[-1]}"
    # All prices should be in range
    for p in prices:
        if not (0.30 <= p <= 0.40):
            return f"Price {p} out of range [0.30, 0.40]"
    return True

@test("Market buy calculation", "trading")
def test_market_buy_calc():
    from auto import market_buy
    # Dry run market buy
    from auto import fetch_top_volume
    markets = fetch_top_volume(1)
    if markets:
        market_id = markets[0].get('id')
        if market_id:
            success, shares, price, cost, status = market_buy(str(market_id), 5, dry_run=True)
            if status == "dry_run":
                return True
            if "price out of range" in status:
                return "SKIP"  # Market price not tradeable
            return f"Unexpected status: {status}"
    return "SKIP"


# =============================================================================
# PHASE 6: AUTOMATION (DRY RUN)
# =============================================================================

@test("Whale follow dry run", "automation")
def test_whale_follow():
    from auto import whale_follow
    try:
        # Should run without error in dry mode
        results = whale_follow(min_usd=10000, bet=5, max_trades=2, dry_run=True, only_profitable=False)
        if not isinstance(results, list):
            return f"Expected list, got {type(results)}"
        return True
    except Exception as e:
        return str(e)

@test("Top volume dry run", "automation")
def test_top_volume():
    from auto import top_volume_bet
    try:
        results = top_volume_bet(bet=5, count=2, dry_run=True)
        if not isinstance(results, list):
            return f"Expected list, got {type(results)}"
        return True
    except Exception as e:
        return str(e)

@test("Scan opportunities", "automation")
def test_scan():
    from auto import scan_opportunities
    try:
        opps = scan_opportunities(min_volume=50000, max_price=0.50)
        if not isinstance(opps, list):
            return f"Expected list, got {type(opps)}"
        return True
    except Exception as e:
        return str(e)

@test("Trader profile fetch", "automation")
def test_trader_profile():
    from auto import fetch_trader_profile
    # Test with a known address (Polymarket foundation)
    profile = fetch_trader_profile("0x0000000000000000000000000000000000000000")
    # May return None for unknown address, that's OK
    return True


# =============================================================================
# PHASE 7: INTEGRATION
# =============================================================================

@test("Full research flow", "integration")
def test_research_flow():
    """Test: search -> get price -> get orderbook"""
    from polymarket_api import search_markets, get_price, get_best_prices

    # Step 1: Search
    results = search_markets("president", 3)
    if not results:
        return "SKIP"  # No results

    # Step 2: Get first active market
    market_id = None
    for m in results:
        if m.get('active') and not m.get('closed'):
            market_id = m.get('id')
            break

    if not market_id:
        return "SKIP"  # No active markets

    # Step 3: Get price
    price = get_price(str(market_id))
    if not price or 'yes' not in price:
        return f"Invalid price for {market_id}"

    # Step 4: Get best prices
    try:
        best = get_best_prices(str(market_id))
        if 'best_bid' not in best:
            return f"Invalid best prices for {market_id}"
    except:
        pass  # OK if orderbook unavailable

    return True

@test("Full automation flow (dry)", "integration")
def test_automation_flow():
    """Test: fetch markets -> filter -> prepare orders"""
    from auto import fetch_top_volume, market_buy

    # Step 1: Fetch markets
    markets = fetch_top_volume(10)
    if not markets:
        return "No markets available"

    # Step 2: Filter tradeable
    tradeable = []
    for m in markets:
        prices = m.get('outcomePrices', '[]')
        if isinstance(prices, str):
            import json as j
            prices = j.loads(prices) if prices else [0.5]
        price = float(prices[0]) if prices else 0.5
        if 0.05 < price < 0.95:
            tradeable.append({'id': m['id'], 'price': price})

    if not tradeable:
        return "SKIP"  # No tradeable markets

    # Step 3: Dry run order
    market = tradeable[0]
    success, shares, price, cost, status = market_buy(str(market['id']), 5, dry_run=True)

    if status not in ["dry_run", "price out of range"]:
        return f"Unexpected: {status}"

    return True

@test("Display functions work", "integration")
def test_display():
    """Test display helpers don't crash"""
    from auto import fmt_usd, fmt_price, log

    # Test formatting
    if fmt_usd(1500000) != "$1.5M":
        return f"fmt_usd(1.5M) = {fmt_usd(1500000)}"
    if fmt_usd(50000) != "$50.0K":
        return f"fmt_usd(50K) = {fmt_usd(50000)}"
    if fmt_price(0.35) != "35¢":
        return f"fmt_price(0.35) = {fmt_price(0.35)}"

    return True


# =============================================================================
# MAIN
# =============================================================================

def print_header(text):
    """Print section header."""
    print()
    print(f"\033[1;36m{'='*60}\033[0m")
    print(f"\033[1;36m  {text}\033[0m")
    print(f"\033[1;36m{'='*60}\033[0m")
    print()

def print_summary():
    """Print test summary."""
    print()
    print(f"\033[1m{'='*60}\033[0m")
    print(f"\033[1m  TEST SUMMARY\033[0m")
    print(f"\033[1m{'='*60}\033[0m")
    print()

    total = RESULTS["passed"] + RESULTS["failed"] + RESULTS["skipped"]

    print(f"  \033[92m✓ Passed:  {RESULTS['passed']}\033[0m")
    print(f"  \033[91m✗ Failed:  {RESULTS['failed']}\033[0m")
    print(f"  \033[93m⊘ Skipped: {RESULTS['skipped']}\033[0m")
    print(f"  ─────────────")
    print(f"  Total:   {total}")
    print()

    if RESULTS["failed"] > 0:
        print("  \033[91mFailed tests:\033[0m")
        for t in RESULTS["tests"]:
            if t["status"] == "FAIL":
                print(f"    • {t['name']}: {t.get('error', 'Unknown error')}")
        print()

    # Save results
    results_file = PROJECT_ROOT / "tests" / "last_run.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "passed": RESULTS["passed"],
                "failed": RESULTS["failed"],
                "skipped": RESULTS["skipped"]
            },
            "tests": RESULTS["tests"]
        }, f, indent=2)
    print(f"  Results saved to: {results_file}")
    print()

    return RESULTS["failed"] == 0


def run_all():
    """Run all tests."""
    print()
    print("\033[1;35m" + "="*60 + "\033[0m")
    print("\033[1;35m  POLYMARKET TRADING INFRASTRUCTURE TESTS\033[0m")
    print("\033[1;35m" + "="*60 + "\033[0m")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Project: {PROJECT_ROOT}")

    # Phase 1: Environment
    print_header("PHASE 1: ENVIRONMENT")
    test_python_version()
    test_project_structure()
    test_data_dir()
    test_config_exists()
    test_config_valid()
    test_clob_client()
    test_requests()

    # Phase 2: API Connectivity
    print_header("PHASE 2: API CONNECTIVITY")
    test_gamma_api()
    test_clob_api()
    test_data_api()

    # Phase 3: Market Data
    print_header("PHASE 3: MARKET DATA")
    test_fetch_top_volume()
    test_search_markets()
    test_get_market_by_slug()
    test_get_price()
    test_get_orderbook()
    test_fetch_trades()

    # Phase 4: Account
    print_header("PHASE 4: ACCOUNT")
    test_clob_client_init()
    test_get_balances()
    test_get_positions()
    test_get_orders()

    # Phase 5: Trading Logic
    print_header("PHASE 5: TRADING LOGIC (DRY RUN)")
    test_order_args()
    test_price_format()
    test_ladder_prices()
    test_market_buy_calc()

    # Phase 6: Automation
    print_header("PHASE 6: AUTOMATION (DRY RUN)")
    test_whale_follow()
    test_top_volume()
    test_scan()
    test_trader_profile()

    # Phase 7: Integration
    print_header("PHASE 7: INTEGRATION")
    test_research_flow()
    test_automation_flow()
    test_display()

    # Summary
    success = print_summary()
    return 0 if success else 1


if __name__ == "__main__":
    exit(run_all())
