import sqlite3
import os
from datetime import datetime
from typing import Set, List, Tuple

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cleaner.db")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite tables for cleaner history and whitelist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS whitelist (
                username TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scan_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                my_username TEXT NOT NULL,
                target_username TEXT NOT NULL,
                scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                my_username TEXT NOT NULL,
                target_username TEXT NOT NULL,
                action TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

def get_whitelist() -> Set[str]:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute("SELECT username FROM whitelist")
        return {row["username"].lower() for row in cursor.fetchall()}

def add_whitelist(username: str) -> bool:
    init_db()
    uname = username.strip().lower().lstrip("@")
    if not uname:
        return False
    with get_connection() as conn:
        conn.execute("INSERT OR IGNORE INTO whitelist (username) VALUES (?)", (uname,))
    return True

def remove_whitelist(username: str) -> bool:
    init_db()
    uname = username.strip().lower().lstrip("@")
    with get_connection() as conn:
        cursor = conn.execute("DELETE FROM whitelist WHERE username = ?", (uname,))
        return cursor.rowcount > 0

def save_scan_results(my_username: str, non_followers: List[str]):
    init_db()
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute("DELETE FROM scan_history WHERE my_username = ?", (my_username.lower(),))
        conn.executemany(
            "INSERT INTO scan_history (my_username, target_username, scanned_at) VALUES (?, ?, ?)",
            [(my_username.lower(), u.lower(), now) for u in non_followers]
        )

def get_last_scan(my_username: str) -> List[str]:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT target_username FROM scan_history WHERE my_username = ? ORDER BY id ASC",
            (my_username.lower(),)
        )
        return [row["target_username"] for row in cursor.fetchall()]

def log_action(my_username: str, target: str, action: str, status: str, message: str = ""):
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO action_logs (my_username, target_username, action, status, message) VALUES (?, ?, ?, ?, ?)",
            (my_username.lower(), target.lower(), action, status, message)
        )

def get_recent_logs(limit: int = 15) -> List[sqlite3.Row]:
    init_db()
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT target_username, action, status, message, performed_at FROM action_logs ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        return cursor.fetchall()
