import sqlite3
import time
import os
from typing import List, Tuple

DB_PATH = "jarvis.db"

def init_db():
    """Initialize SQLite database and create tables if not exists"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            role TEXT,
            content TEXT
        )
    """)
    
    # Memories table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            category TEXT,
            content TEXT
        )
    """)
    
    # Create FTS5 virtual table for memories if FTS5 is supported, otherwise fallback
    try:
        cursor.execute("CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(content, category)")
    except sqlite3.OperationalError:
        # Fallback if FTS5 is missing (rare in modern python)
        pass
        
    # Skills table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            name TEXT UNIQUE,
            description TEXT,
            filepath TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def log_conversation(role: str, content: str):
    """Log a conversation message"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (timestamp, role, content) VALUES (?, ?, ?)",
        (time.time(), role, content)
    )
    conn.commit()
    conn.close()

def add_memory(category: str, content: str):
    """Add a new memory"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = time.time()
    cursor.execute(
        "INSERT INTO memories (timestamp, category, content) VALUES (?, ?, ?)",
        (timestamp, category, content)
    )
    try:
        cursor.execute(
            "INSERT INTO memories_fts (content, category) VALUES (?, ?)",
            (content, category)
        )
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def search_memories(query: str, limit: int = 5) -> List[Tuple[str, str]]:
    """Search stored memories using FTS5 (with OR keyword expansion) or LIKE query"""
    import re
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Extract clean words, ignoring short words (stop words)
    words = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in query.split()]
    words = [w for w in words if len(w) > 2]
    
    if not words:
        # Default: return recent memories if query is too short
        cursor.execute("SELECT category, content FROM memories ORDER BY id DESC LIMIT ?", (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    # Build OR match for FTS5 (e.g., "word1* OR word2*")
    fts_query = " OR ".join([f"{w}*" for w in words])
    results = []
    try:
        # Try FTS5 match
        cursor.execute(
            "SELECT category, content FROM memories_fts WHERE memories_fts MATCH ? LIMIT ?",
            (fts_query, limit)
        )
        results = cursor.fetchall()
    except sqlite3.OperationalError:
        # Fallback to LIKE query
        like_clauses = " OR ".join(["content LIKE ? OR category LIKE ?" for _ in words])
        params = []
        for w in words:
            params.extend([f"%{w}%", f"%{w}%"])
        params.append(limit)
        cursor.execute(
            f"SELECT category, content FROM memories WHERE {like_clauses} LIMIT ?",
            params
        )
        results = cursor.fetchall()
    conn.close()
    return results

def get_recent_conversations(limit: int = 6) -> List[Tuple[str, str]]:
    """Retrieve recent conversation logs"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    conn.close()
    # Reverse to keep chronological order
    return rows[::-1]

def get_db_stats() -> Tuple[int, int, int]:
    """Return count of memories, conversations, and skills in database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT count(*) FROM memories")
        mem_count = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM skills")
        skills_count = cursor.fetchone()[0]
    except Exception:
        mem_count, conv_count, skills_count = 0, 0, 0
    conn.close()
    return mem_count, conv_count, skills_count

# Initialize db when this module is imported
init_db()
