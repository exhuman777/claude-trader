#!/usr/bin/env python3
"""
Alert System for Polymarket Trading
====================================
Price and volume alerts with notifications.

Usage:
    python alerts.py                           # Start alert monitor
    python alerts.py add price 1234567 0.50    # Alert when price > 50¢
    python alerts.py add volume 5000           # Alert on trades > $5K
    python alerts.py list                      # Show active alerts
    python alerts.py clear                     # Clear all alerts
"""

import json
import time
import threading
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from rtds_client import RealTimeDataClient, Subscription, Message
    HAS_RTDS = True
except ImportError:
    HAS_RTDS = False


class AlertType(Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    VOLUME_ABOVE = "volume_above"
    TRADE_SIZE = "trade_size"
    PRICE_CHANGE = "price_change"


@dataclass
class Alert:
    """Alert configuration"""
    id: str
    alert_type: str
    market_id: Optional[str]
    threshold: float
    enabled: bool = True
    triggered_count: int = 0
    last_triggered: Optional[str] = None
    description: str = ""
    created_at: str = ""

    def to_dict(self):
        return asdict(self)


class AlertManager:
    """Manages price and volume alerts"""

    def __init__(self, alerts_file: str = "data/alerts.json"):
        self.alerts_file = Path(alerts_file)
        self.alerts: Dict[str, Alert] = {}
        self.callbacks: List[Callable] = []
        self.price_cache: Dict[str, float] = {}
        self._load_alerts()

    def _load_alerts(self):
        """Load alerts from file"""
        if self.alerts_file.exists():
            try:
                with open(self.alerts_file) as f:
                    data = json.load(f)
                    for alert_data in data.get("alerts", []):
                        alert = Alert(**alert_data)
                        self.alerts[alert.id] = alert
            except Exception as e:
                print(f"Error loading alerts: {e}")

    def _save_alerts(self):
        """Save alerts to file"""
        self.alerts_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.alerts_file, "w") as f:
            json.dump({
                "alerts": [a.to_dict() for a in self.alerts.values()],
                "updated_at": datetime.now().isoformat(),
            }, f, indent=2)

    def add_alert(self, alert_type: AlertType, threshold: float,
                  market_id: Optional[str] = None, description: str = "") -> Alert:
        """Add a new alert"""
        alert_id = f"{alert_type.value}_{market_id or 'all'}_{int(time.time())}"

        alert = Alert(
            id=alert_id,
            alert_type=alert_type.value,
            market_id=market_id,
            threshold=threshold,
            description=description or f"{alert_type.value} @ {threshold}",
            created_at=datetime.now().isoformat(),
        )

        self.alerts[alert_id] = alert
        self._save_alerts()
        return alert

    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self._save_alerts()
            return True
        return False

    def clear_alerts(self):
        """Clear all alerts"""
        self.alerts.clear()
        self._save_alerts()

    def list_alerts(self) -> List[Alert]:
        """List all alerts"""
        return list(self.alerts.values())

    def check_price(self, market_id: str, price: float) -> List[Alert]:
        """Check price alerts for a market"""
        triggered = []

        for alert in self.alerts.values():
            if not alert.enabled:
                continue

            if alert.market_id and alert.market_id != market_id:
                continue

            # Check price above
            if alert.alert_type == AlertType.PRICE_ABOVE.value:
                if price >= alert.threshold:
                    triggered.append(alert)

            # Check price below
            elif alert.alert_type == AlertType.PRICE_BELOW.value:
                if price <= alert.threshold:
                    triggered.append(alert)

            # Check price change
            elif alert.alert_type == AlertType.PRICE_CHANGE.value:
                old_price = self.price_cache.get(market_id, price)
                change = abs(price - old_price) / old_price if old_price > 0 else 0
                if change >= alert.threshold:
                    triggered.append(alert)

        # Update cache
        self.price_cache[market_id] = price

        # Mark as triggered
        for alert in triggered:
            alert.triggered_count += 1
            alert.last_triggered = datetime.now().isoformat()
            self._notify(alert, market_id, price)

        if triggered:
            self._save_alerts()

        return triggered

    def check_trade(self, trade: dict) -> List[Alert]:
        """Check trade/volume alerts"""
        triggered = []
        usd_value = trade.get("size", 0) * trade.get("price", 0)

        for alert in self.alerts.values():
            if not alert.enabled:
                continue

            # Check volume above
            if alert.alert_type == AlertType.VOLUME_ABOVE.value:
                if usd_value >= alert.threshold:
                    triggered.append(alert)

            # Check trade size
            elif alert.alert_type == AlertType.TRADE_SIZE.value:
                if trade.get("size", 0) >= alert.threshold:
                    triggered.append(alert)

        # Mark as triggered
        for alert in triggered:
            alert.triggered_count += 1
            alert.last_triggered = datetime.now().isoformat()
            self._notify_trade(alert, trade)

        if triggered:
            self._save_alerts()

        return triggered

    def _notify(self, alert: Alert, market_id: str, price: float):
        """Send notification for price alert"""
        msg = f"🚨 ALERT: {alert.description}\n"
        msg += f"   Market: {market_id}\n"
        msg += f"   Price: {price*100:.1f}¢\n"
        msg += f"   Threshold: {alert.threshold*100:.1f}¢"

        print("\n" + "=" * 50)
        print(msg)
        print("=" * 50 + "\n")

        # Call registered callbacks
        for callback in self.callbacks:
            try:
                callback(alert, {"market_id": market_id, "price": price})
            except Exception as e:
                print(f"Callback error: {e}")

        # Try system notification (macOS)
        self._system_notify(f"Price Alert: {market_id}", f"{price*100:.0f}¢ - {alert.description}")

    def _notify_trade(self, alert: Alert, trade: dict):
        """Send notification for trade alert"""
        usd = trade.get("size", 0) * trade.get("price", 0)
        msg = f"🚨 WHALE ALERT: ${usd:,.0f} trade\n"
        msg += f"   {trade.get('side')} {trade.get('size')} @ {trade.get('price')*100:.0f}¢\n"
        msg += f"   {trade.get('title', '')[:50]}"

        print("\n" + "=" * 50)
        print(msg)
        print("=" * 50 + "\n")

        # Call registered callbacks
        for callback in self.callbacks:
            try:
                callback(alert, trade)
            except Exception as e:
                print(f"Callback error: {e}")

        # System notification
        self._system_notify(f"Whale Trade: ${usd:,.0f}", trade.get("title", "")[:50])

    def _system_notify(self, title: str, message: str):
        """Send system notification (macOS)"""
        try:
            os.system(f'''osascript -e 'display notification "{message}" with title "{title}"' 2>/dev/null''')
        except:
            pass

    def register_callback(self, callback: Callable):
        """Register notification callback"""
        self.callbacks.append(callback)


def run_alert_monitor(manager: AlertManager):
    """Run WebSocket-based alert monitor"""
    if not HAS_RTDS:
        print("Error: rtds_client.py required for live monitoring")
        print("Using polling mode instead...")
        run_polling_monitor(manager)
        return

    def on_message(msg: Message):
        if msg.topic == "activity" and msg.type == "trades":
            trade = {
                "side": msg.payload.get("side", ""),
                "size": msg.payload.get("size", 0),
                "price": msg.payload.get("price", 0),
                "title": msg.payload.get("title", ""),
                "market_id": msg.payload.get("conditionId", ""),
            }
            manager.check_trade(trade)

            # Also check price
            if trade["market_id"] and trade["price"]:
                manager.check_price(trade["market_id"], trade["price"])

    def on_connect(client: RealTimeDataClient):
        print("[ALERTS] Connected to WebSocket")
        client.subscribe_trades()
        print("[ALERTS] Monitoring trades for alerts...")

    print("[ALERTS] Starting WebSocket monitor...")

    client = RealTimeDataClient(
        on_message=on_message,
        on_connect=on_connect,
        auto_reconnect=True,
    )

    try:
        client.connect(blocking=True)
    except KeyboardInterrupt:
        print("\n[ALERTS] Stopping...")
        client.disconnect()


def run_polling_monitor(manager: AlertManager, interval: int = 30):
    """Run polling-based alert monitor (fallback)"""
    print(f"[ALERTS] Polling mode (every {interval}s)")

    while True:
        try:
            # Check watched markets
            for alert in manager.alerts.values():
                if alert.market_id and alert.enabled:
                    try:
                        url = f"https://gamma-api.polymarket.com/markets/{alert.market_id}"
                        resp = requests.get(url, timeout=10)
                        if resp.status_code == 200:
                            market = resp.json()
                            price_str = market.get("outcomePrices", "[0.5]")
                            price = float(price_str.strip("[]").split(",")[0])
                            manager.check_price(alert.market_id, price)
                    except Exception as e:
                        pass

            time.sleep(interval)

        except KeyboardInterrupt:
            print("\n[ALERTS] Stopping...")
            break


def main():
    parser = argparse.ArgumentParser(description="Alert system")
    parser.add_argument("command", nargs="?", default="monitor",
                       choices=["monitor", "add", "remove", "list", "clear"],
                       help="Command to run")
    parser.add_argument("args", nargs="*", help="Command arguments")
    parser.add_argument("--file", default="data/alerts.json", help="Alerts file")
    args = parser.parse_args()

    manager = AlertManager(args.file)

    if args.command == "monitor":
        print("=" * 60)
        print("Poly Alerts - Price & Volume Monitoring")
        print("=" * 60)
        print(f"Active alerts: {len(manager.alerts)}")
        for alert in manager.list_alerts():
            status = "✓" if alert.enabled else "✗"
            print(f"  {status} {alert.description}")
        print("")

        run_alert_monitor(manager)

    elif args.command == "add":
        if len(args.args) < 2:
            print("Usage: alerts.py add <type> <threshold> [market_id]")
            print("Types: price_above, price_below, volume_above, trade_size")
            return

        alert_type = args.args[0]
        threshold = float(args.args[1])
        market_id = args.args[2] if len(args.args) > 2 else None

        try:
            at = AlertType(alert_type)
        except ValueError:
            print(f"Invalid alert type: {alert_type}")
            print("Valid types: price_above, price_below, volume_above, trade_size")
            return

        alert = manager.add_alert(at, threshold, market_id)
        print(f"Added alert: {alert.description}")

    elif args.command == "remove":
        if not args.args:
            print("Usage: alerts.py remove <alert_id>")
            return
        if manager.remove_alert(args.args[0]):
            print("Alert removed")
        else:
            print("Alert not found")

    elif args.command == "list":
        alerts = manager.list_alerts()
        if not alerts:
            print("No alerts configured")
            return

        print(f"\n{'ID':<40} {'Type':<15} {'Threshold':<10} {'Triggered'}")
        print("-" * 80)
        for alert in alerts:
            status = "✓" if alert.enabled else "✗"
            print(f"{status} {alert.id:<38} {alert.alert_type:<15} {alert.threshold:<10.4f} {alert.triggered_count}")

    elif args.command == "clear":
        manager.clear_alerts()
        print("All alerts cleared")


if __name__ == "__main__":
    main()
