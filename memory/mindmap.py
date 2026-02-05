#!/usr/bin/env python3
"""
Trading Mind Map
Hierarchical knowledge organization for trading strategies
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

MINDMAP_FILE = Path(__file__).parent / "data" / "mindmap.json"


class TradingMindMap:
    """
    Hierarchical organization of trading knowledge.
    Helps avoid repeating analysis by caching thought processes.
    """

    def __init__(self):
        self.root = self._load()

    def _load(self) -> dict:
        """Load mindmap from disk"""
        if MINDMAP_FILE.exists():
            try:
                return json.loads(MINDMAP_FILE.read_text())
            except json.JSONDecodeError:
                pass

        # Default structure
        return {
            "markets": {},      # Market-specific knowledge
            "strategies": {},   # Trading strategies
            "analysis": {},     # Cached analysis
            "events": {},       # Event-specific notes
        }

    def save(self):
        """Persist mindmap to disk"""
        MINDMAP_FILE.parent.mkdir(exist_ok=True)
        MINDMAP_FILE.write_text(json.dumps(self.root, indent=2, default=str))

    # ==================== Market Knowledge ====================

    def learn_market(self, market_id: str, info: dict):
        """Store knowledge about a specific market"""
        if market_id not in self.root["markets"]:
            self.root["markets"][market_id] = {
                "created": datetime.now().isoformat(),
                "observations": [],
                "price_history": [],
                "notes": [],
            }

        market = self.root["markets"][market_id]
        market.update(info)
        market["updated"] = datetime.now().isoformat()
        self.save()

    def add_market_observation(self, market_id: str, observation: str):
        """Add an observation about a market"""
        if market_id not in self.root["markets"]:
            self.learn_market(market_id, {})

        self.root["markets"][market_id]["observations"].append({
            "text": observation,
            "time": datetime.now().isoformat(),
        })
        # Keep last 20 observations per market
        self.root["markets"][market_id]["observations"] = \
            self.root["markets"][market_id]["observations"][-20:]
        self.save()

    def get_market_knowledge(self, market_id: str) -> Optional[dict]:
        """Get all knowledge about a market"""
        return self.root["markets"].get(market_id)

    # ==================== Strategy Caching ====================

    def cache_strategy(self, name: str, description: str, conditions: list[str], actions: list[str]):
        """Cache a trading strategy"""
        self.root["strategies"][name] = {
            "description": description,
            "conditions": conditions,
            "actions": actions,
            "uses": 0,
            "wins": 0,
            "losses": 0,
            "created": datetime.now().isoformat(),
        }
        self.save()

    def record_strategy_result(self, name: str, success: bool):
        """Record if a strategy worked"""
        if name in self.root["strategies"]:
            self.root["strategies"][name]["uses"] += 1
            if success:
                self.root["strategies"][name]["wins"] += 1
            else:
                self.root["strategies"][name]["losses"] += 1
            self.save()

    def get_best_strategies(self, limit: int = 5) -> list[dict]:
        """Get strategies with best win rate"""
        strategies = []
        for name, s in self.root["strategies"].items():
            if s["uses"] > 0:
                win_rate = s["wins"] / s["uses"]
                strategies.append({
                    "name": name,
                    "win_rate": win_rate,
                    "uses": s["uses"],
                    **s
                })

        strategies.sort(key=lambda x: (-x["win_rate"], -x["uses"]))
        return strategies[:limit]

    # ==================== Analysis Caching ====================

    def cache_analysis(self, query: str, result: str, expires_hours: int = 24):
        """Cache an analysis result to avoid repeating work"""
        key = query.lower().strip()
        self.root["analysis"][key] = {
            "result": result,
            "created": datetime.now().isoformat(),
            "expires_hours": expires_hours,
        }
        self.save()

    def get_cached_analysis(self, query: str) -> Optional[str]:
        """Get cached analysis if still valid"""
        key = query.lower().strip()
        if key in self.root["analysis"]:
            cached = self.root["analysis"][key]
            # Check expiry
            created = datetime.fromisoformat(cached["created"])
            age_hours = (datetime.now() - created).total_seconds() / 3600
            if age_hours < cached["expires_hours"]:
                return cached["result"]
        return None

    # ==================== Event Notes ====================

    def note_event(self, event_slug: str, note: str):
        """Add a note about an event"""
        if event_slug not in self.root["events"]:
            self.root["events"][event_slug] = {"notes": [], "markets": []}

        self.root["events"][event_slug]["notes"].append({
            "text": note,
            "time": datetime.now().isoformat(),
        })
        self.save()

    def get_event_context(self, event_slug: str) -> str:
        """Get all notes for an event as context"""
        if event_slug not in self.root["events"]:
            return ""

        event = self.root["events"][event_slug]
        lines = [f"# Event: {event_slug}\n"]

        for note in event["notes"][-10:]:
            lines.append(f"- {note['text']}")

        return "\n".join(lines)

    # ==================== Export for Context ====================

    def export_context(self, max_tokens: int = 1000) -> str:
        """Export mindmap as context string (token-limited)"""
        lines = ["# Trading Mind Map\n"]

        # Best strategies
        best = self.get_best_strategies(3)
        if best:
            lines.append("## Proven Strategies")
            for s in best:
                lines.append(f"- **{s['name']}** ({s['win_rate']*100:.0f}% win rate, {s['uses']} uses)")
                lines.append(f"  {s['description'][:100]}")
            lines.append("")

        # Recent market observations
        recent_markets = sorted(
            self.root["markets"].items(),
            key=lambda x: x[1].get("updated", ""),
            reverse=True
        )[:3]

        if recent_markets:
            lines.append("## Recent Market Notes")
            for mid, m in recent_markets:
                if m.get("observations"):
                    obs = m["observations"][-1]["text"]
                    lines.append(f"- {mid[:20]}: {obs[:80]}")
            lines.append("")

        result = "\n".join(lines)

        # Rough token estimate (4 chars per token)
        if len(result) > max_tokens * 4:
            result = result[:max_tokens * 4] + "\n...(truncated)"

        return result


# Global instance
mindmap = TradingMindMap()


def get_mindmap() -> TradingMindMap:
    """Get the global mindmap instance"""
    return mindmap


if __name__ == "__main__":
    mm = TradingMindMap()

    # Test
    mm.cache_strategy(
        "ladder_dip_buy",
        "Buy on dips with ladder orders",
        ["price dropped >5%", "high volume"],
        ["place 5 buy orders from current-5% to current-10%"]
    )
    mm.record_strategy_result("ladder_dip_buy", True)
    mm.add_market_observation("test-market", "Whale bought $50k at 35c")

    print(mm.export_context())
