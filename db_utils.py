import sqlite3
import hashlib
from datetime import date

DB_NAME = "lol_pick.db"
SECRET_SALT = "LoLSuperSecret2026"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS champions (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            damage_type TEXT,
            early_power INTEGER,
            late_power INTEGER,
            cc_level INTEGER,
            tankiness INTEGER,
            mobility INTEGER,
            burst INTEGER,
            armor_mr INTEGER
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            is_pro INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS usage (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            analysis_date TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            champion_name TEXT NOT NULL,
            rating INTEGER NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
    ''')
    try:
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_usage_user_date ON usage(user_id, analysis_date)")
    except:
        pass
    conn.commit()
    conn.close()

def seed_champions():
    conn = get_connection()
    existing = conn.execute("SELECT COUNT(*) FROM champions").fetchone()[0]
    # Eğer mevcut sayı 45'ten azsa eksikleri ekle (tekrar çalıştırmada var olanları atla)
    if existing < 45:
        sample = [
            # Top (8)
            ("Aatrox", "Top", "AD", 7, 6, 3, 4, 3, 4, 3),
            ("Malphite", "Top", "AP", 4, 7, 4, 5, 2, 3, 5),
            ("Darius", "Top", "AD", 8, 5, 2, 4, 1, 5, 3),
            ("Ornn", "Top", "Mixed", 5, 8, 5, 5, 1, 2, 5),
            ("Shen", "Top", "Mixed", 5, 7, 3, 4, 3, 2, 4),
            ("Garen", "Top", "AD", 7, 6, 1, 5, 2, 4, 4),
            ("Camille", "Top", "AD", 6, 8, 3, 2, 4, 4, 2),
            ("Mordekaiser", "Top", "AP", 5, 8, 2, 4, 1, 4, 4),
            # Jungle (8)
            ("Lee Sin", "Jungle", "AD", 8, 4, 3, 3, 4, 4, 3),
            ("Master Yi", "Jungle", "AD", 3, 10, 1, 1, 4, 5, 1),
            ("Sejuani", "Jungle", "AP", 4, 7, 5, 4, 3, 2, 4),
            ("Kha'Zix", "Jungle", "AD", 6, 6, 1, 1, 4, 5, 1),
            ("Amumu", "Jungle", "AP", 3, 8, 5, 4, 2, 2, 4),
            ("Nidalee", "Jungle", "AP", 7, 5, 1, 1, 5, 4, 1),
            ("Kayn", "Jungle", "AD", 5, 8, 2, 2, 5, 4, 2),
            ("Viego", "Jungle", "AD", 6, 7, 1, 3, 4, 5, 2),
            # Mid (8)
            ("Zed", "Mid", "AD", 6, 5, 1, 1, 5, 5, 1),
            ("Syndra", "Mid", "AP", 6, 7, 3, 1, 2, 5, 1),
            ("Viktor", "Mid", "AP", 5, 9, 3, 1, 2, 4, 1),
            ("Fizz", "Mid", "AP", 4, 8, 2, 2, 5, 5, 2),
            ("Twisted Fate", "Mid", "AP", 4, 8, 3, 1, 3, 3, 1),
            ("Yasuo", "Mid", "AD", 7, 8, 3, 1, 4, 5, 1),
            ("Ahri", "Mid", "AP", 6, 7, 4, 1, 4, 4, 1),
            ("Katarina", "Mid", "AP", 4, 9, 1, 1, 5, 5, 1),
            # ADC (8)
            ("Jhin", "ADC", "AD", 7, 8, 2, 1, 2, 5, 1),
            ("Kai'Sa", "ADC", "Mixed", 5, 9, 1, 2, 4, 5, 2),
            ("Miss Fortune", "ADC", "AD", 8, 6, 2, 1, 2, 4, 1),
            ("Ezreal", "ADC", "Mixed", 5, 7, 1, 1, 4, 4, 1),
            ("Caitlyn", "ADC", "AD", 7, 7, 2, 1, 2, 4, 1),
            ("Ashe", "ADC", "AD", 6, 8, 3, 1, 2, 4, 1),
            ("Lucian", "ADC", "AD", 8, 6, 1, 1, 3, 5, 1),
            ("Jinx", "ADC", "AD", 5, 10, 2, 1, 2, 5, 1),
            # Support (8)
            ("Leona", "Support", "AP", 5, 4, 5, 5, 2, 2, 4),
            ("Lulu", "Support", "AP", 4, 8, 4, 2, 2, 2, 2),
            ("Thresh", "Support", "AP", 5, 6, 5, 4, 2, 2, 3),
            ("Nautilus", "Support", "AP", 5, 5, 5, 5, 1, 2, 4),
            ("Pyke", "Support", "AD", 6, 5, 4, 1, 5, 5, 1),
            ("Yuumi", "Support", "AP", 2, 9, 3, 1, 5, 1, 1),
            ("Blitzcrank", "Support", "AP", 6, 4, 5, 4, 2, 2, 4),
            ("Soraka", "Support", "AP", 4, 8, 3, 1, 2, 1, 1),
        ]
        conn.executemany(
            "INSERT OR IGNORE INTO champions (name, role, damage_type, early_power, late_power, cc_level, tankiness, mobility, burst, armor_mr) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            sample
        )
        conn.commit()
    conn.close()

def get_champions():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM champions").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user(username):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(user) if user else None

def create_user(username):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def check_daily_limit(user_id):
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute("SELECT count FROM usage WHERE user_id = ? AND analysis_date = ?", (user_id, today)).fetchone()
    conn.close()
    return row['count'] if row else 0

def increment_usage(user_id):
    today = date.today().isoformat()
    conn = get_connection()
    conn.execute(
        "INSERT INTO usage (user_id, analysis_date, count) VALUES (?, ?, 1) "
        "ON CONFLICT(user_id, analysis_date) DO UPDATE SET count = count + 1",
        (user_id, today)
    )
    conn.commit()
    conn.close()

def set_pro(username):
    conn = get_connection()
    conn.execute("UPDATE users SET is_pro = 1 WHERE username = ?", (username,))
    conn.commit()
    conn.close()

def save_feedback(user_id, champion_name, rating):
    conn = get_connection()
    conn.execute("INSERT INTO feedback (user_id, champion_name, rating) VALUES (?, ?, ?)", (user_id, champion_name, rating))
    conn.commit()
    conn.close()

def generate_personal_key(username):
    raw = username + SECRET_SALT
    return hashlib.sha256(raw.encode()).hexdigest()[:12].upper()
