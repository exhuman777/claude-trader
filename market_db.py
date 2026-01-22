#!/usr/bin/env python3
"""
Market Database Interface
=========================
Fast SQLite lookups for Polymarket markets.
Uses existing ../data/markets.db (1,330+ markets indexed).
"""
import sqlite3
from pathlib import Path

# Go up to dashboard4all folder (3 levels: claude-trader -> projects -> dashboard4all)
DB_PATH = Path(__file__).parent.parent.parent / "data" / "markets.db"

def get_conn():
    """Get database connection with row factory"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def search_db(query: str, limit: int = 20):
    """Search markets by title/question"""
    conn = get_conn()
    try:
        # Use LIKE for simple search (FTS would be faster but this works)
        sql = """
            SELECT id, title, question, category, yes_price, volume, status
            FROM markets
            WHERE (title LIKE ? OR question LIKE ?) AND status = 'open'
            ORDER BY volume DESC
            LIMIT ?
        """
        pattern = f"%{query}%"
        rows = conn.execute(sql, (pattern, pattern, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_market_from_db(market_id: str):
    """Get single market by ID"""
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM markets WHERE id = ?",
            (market_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def get_trending(limit: int = 10):
    """Get top markets by volume"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, title, yes_price, volume, category
            FROM markets
            WHERE status = 'open'
            ORDER BY volume DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_by_category(category: str, limit: int = 20):
    """Get markets by category"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT id, title, yes_price, volume
            FROM markets
            WHERE category = ? AND status = 'open'
            ORDER BY volume DESC
            LIMIT ?
        """, (category, limit)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def get_categories():
    """List all categories with counts"""
    conn = get_conn()
    try:
        rows = conn.execute("""
            SELECT category, COUNT(*) as count
            FROM markets
            WHERE status = 'open'
            GROUP BY category
            ORDER BY count DESC
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

def sync_market(market_id: str, data: dict):
    """Update market in database from API response"""
    conn = get_conn()
    try:
        conn.execute("""
            INSERT OR REPLACE INTO markets
            (id, title, question, yes_price, no_price, volume, status, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
        """, (
            market_id,
            data.get('title', data.get('question', '')),
            data.get('question', ''),
            data.get('yes_price', 0.5),
            data.get('no_price', 0.5),
            data.get('volume', 0),
            data.get('status', 'open')
        ))
        conn.commit()
    finally:
        conn.close()

def db_stats():
    """Get database statistics"""
    conn = get_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM markets").fetchone()[0]
        active = conn.execute("SELECT COUNT(*) FROM markets WHERE status='open'").fetchone()[0]
        return {"total": total, "active": active}
    finally:
        conn.close()


if __name__ == "__main__":
    print(f"Database: {DB_PATH}")
    stats = db_stats()
    print(f"Markets: {stats['total']} total, {stats['active']} active")

    print("\nCategories:")
    for cat in get_categories()[:5]:
        print(f"  {cat['category']}: {cat['count']}")

    print("\nTrending:")
    for m in get_trending(5):
        print(f"  {m['id']}: {m['title'][:40]}... ${m['volume']:,.0f}")
