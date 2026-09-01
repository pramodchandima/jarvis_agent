import sqlite3
import threading
import time
from typing import List, Tuple

DB_PATH = "jarvis.db"

# Persistent per-thread connection pool.
# All asyncio coroutines run on the main thread, so they share one connection.
# Background threads (via asyncio.to_thread) get their own connection.
_local = threading.local()

def _get_conn() -> sqlite3.Connection:
    """Return a reusable per-thread SQLite connection with WAL mode enabled."""
    if not hasattr(_local, 'conn') or _local.conn is None:
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")   # allow concurrent reads
        conn.execute("PRAGMA synchronous=NORMAL")  # safe but faster than FULL
        _local.conn = conn
    return _local.conn

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
    
    # Register pre-built default skills with relevant keywords to help the LLM route requests accurately
    default_skills = [
        ("get_weather", "Fetch current meteorological weather and air quality report for any city or location. Keywords: weather, temperature, rain, wind, climate, forecast, hot, cold, humidity, aqi, air quality, outside.", "skills/get_weather.py"),
        ("get_space_weather", "Fetch NOAA Space Weather data including solar wind speed and current warning scales. Keywords: solar wind, solar flare, space weather, geomagnetic storm, aurora, sun activity.", "skills/get_space_weather.py"),
        ("get_space_telemetry", "Retrieve international space station ISS coordinates, velocity, crew info, telemetry, and track space satellites. Keywords: space station, iss, satellite, satellites, astronauts, orbit, altitude, space telemetry.", "skills/get_space_telemetry.py"),
        ("get_crypto_prices", "Get current USD market rates for major cryptocurrencies. Keywords: crypto, cryptocurrency, bitcoin, btc, ethereum, eth, solana, sol, bnb, doge, coin price, crypto market.", "skills/get_crypto_prices.py"),
        ("track_airplanes", "Track active airplanes, flight counts, speed, and altitude in the user's area using flight APIs. Keywords: airplane, aeroplane, flight, plane, planes, flight radar, overhead, aviation, air traffic, aircraft.", "skills/track_airplanes.py"),
        ("internet_speed_test", "Check current network connection status and latency (ping speed) to a public server. Keywords: speed test, internet speed, ping, network latency, slow internet, connection speed, wifi speed, bandwidth.", "skills/internet_speed_test.py"),
        ("web_search", "Search the internet/web for real-time information, answers, news, or topics you do not know about. Keywords: search, google, find out, latest news, current events, who is, what is, look up, online.", "skills/web_search.py"),
    ]
    for name, desc, path in default_skills:
        cursor.execute(
            """INSERT INTO skills (timestamp, name, description, filepath) 
               VALUES (?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET 
               description=excluded.description, filepath=excluded.filepath""",
            (time.time(), name, desc, path)
        )
    
    conn.commit()
    conn.close()

def log_conversation(role: str, content: str):
    """Log a conversation message"""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (timestamp, role, content) VALUES (?, ?, ?)",
        (time.time(), role, content)
    )
    conn.commit()

def add_memory(category: str, content: str):
    """Add a new memory"""
    conn = _get_conn()
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

def search_memories(query: str, limit: int = 5) -> List[Tuple[str, str]]:
    """Search stored memories using FTS5 (with OR keyword expansion) or LIKE query"""
    import re
    conn = _get_conn()
    cursor = conn.cursor()

    # Extract clean words, ignoring short words (stop words)
    words = [re.sub(r'[^a-zA-Z0-9]', '', w) for w in query.split()]
    words = [w for w in words if len(w) > 2]

    if not words:
        cursor.execute("SELECT category, content FROM memories ORDER BY id DESC LIMIT ?", (limit,))
        return cursor.fetchall()

    # Build OR match for FTS5 (e.g., "word1* OR word2*")
    fts_query = " OR ".join([f"{w}*" for w in words])
    try:
        cursor.execute(
            "SELECT category, content FROM memories_fts WHERE memories_fts MATCH ? LIMIT ?",
            (fts_query, limit)
        )
        return cursor.fetchall()
    except sqlite3.OperationalError:
        like_clauses = " OR ".join(["content LIKE ? OR category LIKE ?" for _ in words])
        params = []
        for w in words:
            params.extend([f"%{w}%", f"%{w}%"])
        params.append(limit)
        cursor.execute(
            f"SELECT category, content FROM memories WHERE {like_clauses} LIMIT ?",
            params
        )
        return cursor.fetchall()

def get_recent_conversations(limit: int = 6) -> List[Tuple[str, str]]:
    """Retrieve recent conversation logs"""
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()
    # Reverse to keep chronological order
    return rows[::-1]

def get_db_stats() -> Tuple[int, int, int]:
    """Return count of memories, conversations, and skills in database"""
    conn = _get_conn()
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
    return mem_count, conv_count, skills_count

def get_all_skills() -> List[Tuple[str, str]]:
    """Retrieve all registered skills (name, description)"""
    conn = _get_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name, description FROM skills")
        return cursor.fetchall()
    except Exception:
        return []

# Initialize db when this module is imported
init_db()
