#!/usr/bin/env python3
"""
Trading Memory Store
Persistent knowledge that improves across sessions
"""
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

# Memory storage location
MEMORY_DIR = Path(__file__).parent / "data"
MEMORY_DIR.mkdir(exist_ok=True)

KNOWLEDGE_FILE = MEMORY_DIR / "knowledge.json"
PATTERNS_FILE = MEMORY_DIR / "patterns.json"
HISTORY_FILE = MEMORY_DIR / "trade_history.json"


class TradingMemory:
    """
    Persistent memory for trading knowledge.
    Learns from sessions to avoid repeating work.
    """

    def __init__(self):
        self.knowledge = self._load(KNOWLEDGE_FILE, default={"facts": {}, "insights": []})
        self.patterns = self._load(PATTERNS_FILE, default={"successful": [], "failed": []})
        self.history = self._load(HISTORY_FILE, default={"trades": [], "queries": []})

    def _load(self, path: Path, default: dict) -> dict:
        """Load JSON file or return default"""
        if path.exists():
            try:
                return json.loads(path.read_text())
            except json.JSONDecodeError:
                return default
        return default

    def _save(self, path: Path, data: dict):
        """Save data to JSON file"""
        path.write_text(json.dumps(data, indent=2, default=str))

    def save_all(self):
        """Persist all memory to disk"""
        self._save(KNOWLEDGE_FILE, self.knowledge)
        self._save(PATTERNS_FILE, self.patterns)
        self._save(HISTORY_FILE, self.history)

    # ==================== Knowledge Management ====================

    def remember_fact(self, key: str, value: str, source: str = "observation"):
        """Store a fact about markets/trading"""
        fact_id = hashlib.md5(key.encode()).hexdigest()[:8]
        self.knowledge["facts"][fact_id] = {
            "key": key,
            "value": value,
            "source": source,
            "updated": datetime.now().isoformat(),
        }
        self.save_all()

    def remember_insight(self, insight: str, confidence: float = 0.5):
        """Store a trading insight or learned pattern"""
        self.knowledge["insights"].append({
            "text": insight,
            "confidence": confidence,
            "created": datetime.now().isoformat(),
            "validated": False,
        })
        # Keep last 100 insights
        self.knowledge["insights"] = self.knowledge["insights"][-100:]
        self.save_all()

    def get_relevant_knowledge(self, query: str, limit: int = 5) -> list[dict]:
        """Find knowledge relevant to a query (simple keyword match)"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        results = []

        # Search facts
        for fact_id, fact in self.knowledge["facts"].items():
            text = f"{fact['key']} {fact['value']}".lower()
            score = len(query_words & set(text.split()))
            if score > 0:
                results.append({"type": "fact", "data": fact, "score": score})

        # Search insights
        for insight in self.knowledge["insights"]:
            text = insight["text"].lower()
            score = len(query_words & set(text.split()))
            if score > 0:
                results.append({"type": "insight", "data": insight, "score": score})

        # Sort by score and return top N
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # ==================== Pattern Tracking ====================

    def record_successful_pattern(self, pattern: str, context: dict):
        """Record a trading pattern that worked"""
        self.patterns["successful"].append({
            "pattern": pattern,
            "context": context,
            "timestamp": datetime.now().isoformat(),
        })
        self.patterns["successful"] = self.patterns["successful"][-50:]
        self.save_all()

    def record_failed_pattern(self, pattern: str, reason: str):
        """Record a pattern that didn't work"""
        self.patterns["failed"].append({
            "pattern": pattern,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        })
        self.patterns["failed"] = self.patterns["failed"][-50:]
        self.save_all()

    def get_best_practices(self) -> list[str]:
        """Get patterns that have worked well"""
        successful = self.patterns["successful"]
        # Count pattern occurrences
        pattern_counts = {}
        for p in successful:
            key = p["pattern"]
            pattern_counts[key] = pattern_counts.get(key, 0) + 1

        # Return most common patterns
        sorted_patterns = sorted(pattern_counts.items(), key=lambda x: -x[1])
        return [p[0] for p in sorted_patterns[:10]]

    def get_patterns_to_avoid(self) -> list[str]:
        """Get patterns that have failed"""
        return [p["pattern"] for p in self.patterns["failed"][-10:]]

    # ==================== Trade History ====================

    def record_trade(self, trade: dict):
        """Record a trade for history"""
        trade["timestamp"] = datetime.now().isoformat()
        self.history["trades"].append(trade)
        self.history["trades"] = self.history["trades"][-500:]
        self.save_all()

    def record_query(self, query: str, result_summary: str):
        """Record a query to avoid repeating research"""
        query_hash = hashlib.md5(query.lower().encode()).hexdigest()[:8]
        self.history["queries"].append({
            "hash": query_hash,
            "query": query,
            "result": result_summary,
            "timestamp": datetime.now().isoformat(),
        })
        self.history["queries"] = self.history["queries"][-200:]
        self.save_all()

    def find_similar_query(self, query: str) -> Optional[dict]:
        """Check if we've answered a similar query before"""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for q in reversed(self.history["queries"]):
            past_words = set(q["query"].lower().split())
            overlap = len(query_words & past_words) / max(len(query_words), 1)
            if overlap > 0.7:  # 70% word overlap
                return q
        return None

    # ==================== Context Building ====================

    def get_session_context(self) -> str:
        """Build context string for new session"""
        lines = ["# Trading Memory Context\n"]

        # Best practices
        best = self.get_best_practices()
        if best:
            lines.append("## What Works")
            for p in best[:5]:
                lines.append(f"- {p}")
            lines.append("")

        # Patterns to avoid
        avoid = self.get_patterns_to_avoid()
        if avoid:
            lines.append("## Avoid")
            for p in avoid[:5]:
                lines.append(f"- {p}")
            lines.append("")

        # Recent insights
        recent_insights = [i for i in self.knowledge["insights"] if i.get("validated")]
        if recent_insights:
            lines.append("## Validated Insights")
            for i in recent_insights[-5:]:
                lines.append(f"- {i['text']}")
            lines.append("")

        # Key facts
        if self.knowledge["facts"]:
            lines.append("## Key Facts")
            for fid, fact in list(self.knowledge["facts"].items())[-5:]:
                lines.append(f"- {fact['key']}: {fact['value']}")

        return "\n".join(lines)


# Global memory instance
memory = TradingMemory()


def get_memory() -> TradingMemory:
    """Get the global memory instance"""
    return memory


if __name__ == "__main__":
    # Test memory
    m = TradingMemory()

    # Add some test data
    m.remember_fact("spread_rule", "Don't trade when spread > 3%", "experience")
    m.remember_insight("Whale follows work best on high-volume markets", 0.8)
    m.record_successful_pattern("ladder buy 5 orders from 35 to 30", {"market": "test"})

    print("Context:\n")
    print(m.get_session_context())
