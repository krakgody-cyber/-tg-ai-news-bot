import sqlite3
import os
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "news_bot.db")


def get_connection():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_url TEXT,
            title TEXT,
            content TEXT,
            image_url TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT DEFAULT (datetime('now')),
            approved_at TEXT,
            posted_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sent_sources (
            source_url TEXT PRIMARY KEY,
            sent_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


def is_already_sent(source_url):
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM sent_sources WHERE source_url = ?", (source_url,)).fetchone()
    conn.close()
    return row is not None


def mark_sent(source_url):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO sent_sources (source_url) VALUES (?)",
        (source_url,),
    )
    conn.commit()
    conn.close()


def save_post(source_url, title, content, image_url):
    conn = get_connection()
    conn.execute(
        "INSERT INTO posts (source_url, title, content, image_url) VALUES (?, ?, ?, ?)",
        (source_url, title, content, image_url),
    )
    conn.commit()
    conn.close()


def get_pending_posts():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM posts WHERE status = 'pending' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def approve_post(post_id):
    conn = get_connection()
    conn.execute(
        "UPDATE posts SET status = 'approved', approved_at = datetime('now') WHERE id = ?",
        (post_id,),
    )
    conn.commit()
    conn.close()


def mark_posted(post_id):
    conn = get_connection()
    conn.execute(
        "UPDATE posts SET status = 'posted', posted_at = datetime('now') WHERE id = ?",
        (post_id,),
    )
    conn.commit()
    conn.close()


def reject_post(post_id):
    conn = get_connection()
    conn.execute(
        "UPDATE posts SET status = 'rejected' WHERE id = ?",
        (post_id,),
    )
    conn.commit()
    conn.close()


def get_post(post_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_post_content(post_id, title, content):
    conn = get_connection()
    conn.execute(
        "UPDATE posts SET title = ?, content = ? WHERE id = ?",
        (title, content, post_id),
    )
    conn.commit()
    conn.close()


def get_last_post_id():
    conn = get_connection()
    row = conn.execute("SELECT id FROM posts ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return row["id"] if row else None


def set_edit_state(post_id, chat_id, message_id):
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS edit_states (
            chat_id INTEGER PRIMARY KEY,
            post_id INTEGER,
            message_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.execute(
        "INSERT OR REPLACE INTO edit_states (chat_id, post_id, message_id) VALUES (?, ?, ?)",
        (chat_id, post_id, message_id),
    )
    conn.commit()
    conn.close()


def get_edit_state(chat_id):
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS edit_states (
            chat_id INTEGER PRIMARY KEY,
            post_id INTEGER,
            message_id INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    row = conn.execute(
        "SELECT * FROM edit_states WHERE chat_id = ?", (chat_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def clear_edit_state(chat_id):
    conn = get_connection()
    conn.execute("DELETE FROM edit_states WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()
