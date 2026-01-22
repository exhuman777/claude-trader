#!/usr/bin/env python3
"""
Poly Utils - Shared utilities for all Poly projects
====================================================
Common HTTP handlers, JSON helpers, and display formatting.
"""

import json
from http.server import BaseHTTPRequestHandler
from datetime import datetime
from typing import Any, Dict, Optional

# ============================================================================
# HTTP HELPERS
# ============================================================================

class BaseHandler(BaseHTTPRequestHandler):
    """Base HTTP handler with common methods"""

    def log_message(self, format, *args):
        pass  # Suppress logs

    def send_json(self, data: Any, status: int = 200):
        """Send JSON response with CORS"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_html(self, html: str, status: int = 200):
        """Send HTML response"""
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html.encode())

    def get_param(self, name: str, default: str = "") -> str:
        """Extract query parameter from URL"""
        from urllib.parse import parse_qs, urlparse
        query = parse_qs(urlparse(self.path).query)
        return query.get(name, [default])[0]


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def fmt_price(price: float) -> str:
    """Format price as cents: 0.35 -> 35¢"""
    return f"{price * 100:.0f}¢"


def fmt_volume(vol: float) -> str:
    """Format volume: 1500000 -> $1.5M"""
    if vol >= 1_000_000:
        return f"${vol / 1_000_000:.1f}M"
    elif vol >= 1_000:
        return f"${vol / 1_000:.0f}K"
    return f"${vol:.0f}"


def fmt_change(change: float) -> str:
    """Format percentage change with sign"""
    sign = "+" if change >= 0 else ""
    return f"{sign}{change:.1f}%"


def fmt_time(ts: Optional[str] = None) -> str:
    """Format timestamp as HH:MM:SS"""
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return dt.strftime("%H:%M:%S")
        except:
            pass
    return datetime.now().strftime("%H:%M:%S")


# ============================================================================
# DATA HELPERS
# ============================================================================

def safe_get(data: Dict, *keys, default=None):
    """Safely get nested dict value"""
    result = data
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key, default)
        else:
            return default
    return result


def parse_price_string(price_str: str) -> float:
    """Parse Polymarket price string: '[0.55,0.45]' -> 0.55"""
    try:
        return float(price_str.strip("[]").split(",")[0])
    except:
        return 0.5


# ============================================================================
# SPREAD ANALYSIS
# ============================================================================

def analyze_spread(bid: float, ask: float) -> Dict:
    """Analyze bid/ask spread"""
    spread = ask - bid
    spread_pct = (spread / ask * 100) if ask > 0 else 0

    if spread <= 0.02:
        label, quality = "TIGHT", "good"
    elif spread <= 0.10:
        label, quality = "OK", "medium"
    else:
        label, quality = "WIDE", "poor"

    return {
        "spread": spread,
        "spread_pct": spread_pct,
        "label": label,
        "quality": quality,
        "display": f"{fmt_price(spread)} ({spread_pct:.1f}%)",
    }
