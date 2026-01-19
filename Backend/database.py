import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# --- DATABASE CONFIGURATION ---
DB_CONFIG = {
    "dbname": "smartstudy_db",
    "user": "postgres",        
    "password": "Gani@3010",   # Your Password
    "host": "localhost",
    "port": "5432"
}

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Database Connection Error: {e}")
        return None

def init_db():
    """Creates tables if they don't exist."""
    conn = get_db_connection()
    if conn is None: return
    
    cur = conn.cursor()
    
    # 1. Settings Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            start_time TEXT DEFAULT '09:00',
            end_time TEXT DEFAULT '17:00',
            parent_phone TEXT DEFAULT '',
            notify_enabled INTEGER DEFAULT 0
        );
    """)

    # 2. History Table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS history (
            date TEXT PRIMARY KEY,
            detections INTEGER DEFAULT 0
        );
    """)

    # 3. Default Settings
    cur.execute("SELECT count(*) FROM settings;")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO settings (id) VALUES (1);")

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database Initialized (PostgreSQL)")

def get_settings():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM settings WHERE id=1;")
    settings = cur.fetchone()
    cur.close()
    conn.close()
    return dict(settings) if settings else {}

def update_settings(data):
    conn = get_db_connection()
    cur = conn.cursor()
    sql = """
        UPDATE settings 
        SET start_time=%s, end_time=%s, parent_phone=%s, notify_enabled=%s 
        WHERE id=1;
    """
    cur.execute(sql, (data['start_time'], data['end_time'], data['parent_phone'], int(data['notify_enabled'])))
    conn.commit()
    cur.close()
    conn.close()

def log_detection():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cur = conn.cursor()
    # Insert for today if missing
    cur.execute("INSERT INTO history (date, detections) VALUES (%s, 0) ON CONFLICT (date) DO NOTHING;", (today,))
    # Increment count
    cur.execute("UPDATE history SET detections = detections + 1 WHERE date = %s;", (today,))
    conn.commit()
    cur.close()
    conn.close()

def get_history():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM history ORDER BY date DESC LIMIT 7;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(row) for row in rows]

def get_today_count():
    """Returns total distractions for today."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT detections FROM history WHERE date = %s;", (today,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result[0] if result else 0