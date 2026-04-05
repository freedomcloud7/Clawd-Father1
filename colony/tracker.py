"""
Revenue tracker — SQLite database for tracking colony earnings.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple
import config


def get_db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS revenue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT NOT NULL,
                stream TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                strategy TEXT,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                monthly_target REAL DEFAULT 5000
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id TEXT,
                action_type TEXT,
                description TEXT,
                result TEXT,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def record_revenue(team_id: str, stream: str, amount: float, description: str = ""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO revenue (team_id, stream, amount, description) VALUES (?, ?, ?, ?)",
            (team_id, stream, amount, description)
        )
        conn.commit()


def get_weekly_revenue(team_id: str = None) -> float:
    week_ago = datetime.now() - timedelta(days=7)
    with get_db() as conn:
        if team_id:
            row = conn.execute(
                "SELECT SUM(amount) FROM revenue WHERE team_id=? AND recorded_at>=?",
                (team_id, week_ago)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT SUM(amount) FROM revenue WHERE recorded_at>=?",
                (week_ago,)
            ).fetchone()
        return row[0] or 0.0


def get_monthly_revenue(team_id: str = None) -> float:
    month_ago = datetime.now() - timedelta(days=30)
    with get_db() as conn:
        if team_id:
            row = conn.execute(
                "SELECT SUM(amount) FROM revenue WHERE team_id=? AND recorded_at>=?",
                (team_id, month_ago)
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT SUM(amount) FROM revenue WHERE recorded_at>=?",
                (month_ago,)
            ).fetchone()
        return row[0] or 0.0


def get_stream_performance() -> List[Tuple]:
    week_ago = datetime.now() - timedelta(days=7)
    with get_db() as conn:
        rows = conn.execute("""
            SELECT team_id, stream, SUM(amount) as total
            FROM revenue
            WHERE recorded_at >= ?
            GROUP BY team_id, stream
            ORDER BY total DESC
        """, (week_ago,)).fetchall()
        return [(r["team_id"], r["stream"], r["total"]) for r in rows]


def log_action(team_id: str, action_type: str, description: str, result: str = ""):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO actions (team_id, action_type, description, result) VALUES (?, ?, ?, ?)",
            (team_id, action_type, description, result)
        )
        conn.commit()


def get_status_report() -> str:
    monthly = get_monthly_revenue()
    weekly = get_weekly_revenue()
    streams = get_stream_performance()
    goal = config.MONTHLY_GOAL

    report = f"""COLONY STATUS REPORT
{'='*40}
Monthly Revenue:  ${monthly:,.2f} / ${goal:,.2f} goal
Weekly Revenue:   ${weekly:,.2f}
Progress:         {(monthly/goal*100):.1f}%

TOP REVENUE STREAMS (last 7 days):
"""
    if streams:
        for team_id, stream, total in streams[:5]:
            report += f"  [{team_id}] {stream}: ${total:,.2f}\n"
    else:
        report += "  No revenue recorded yet.\n"

    return report


# Initialize on import
init_db()
