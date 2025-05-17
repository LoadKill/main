import sqlite3


# DB 연결 및 테이블 생성
conn = sqlite3.connect('1_illegal_vehicle.db')
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS illegal_vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    track_id INTEGER UNIQUE,
    timestamp TEXT,
    class TEXT,
    x1 INTEGER,
    y1 INTEGER,
    x2 INTEGER,
    y2 INTEGER,
    image_path TEXT
)
""")
conn.commit()