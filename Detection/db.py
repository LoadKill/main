import sqlite3
from datetime import datetime
import cv2
import os


def init_db():
    base_dir =  os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'illegal_vehicle.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS illegal_vehicles (
        track_id INTEGER PRIMARY KEY,
        timestamp TEXT,
        class TEXT,
        x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
        image_path TEXT,
        cctvname TEXT
    )""")
    conn.commit()

    return conn, cursor


def is_already_saved(cursor, track_id):
    cursor.execute("SELECT 1 FROM illegal_vehicles WHERE track_id=?", (track_id,))
    return cursor.fetchone() is not None


def save_illegal_vehicle(frame, box, track_id, cursor, conn, cctvname=""):
    x1, y1, x2, y2, _ = map(int, box)
    roi = frame[y1:y2, x1:x2]

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")

    folder_path = os.path.join("Detection", "saved_illegal", date_str)
    os.makedirs(folder_path, exist_ok=True)

    filename = f"illegal_{track_id}_{time_str}.jpg"
    save_path = os.path.join(folder_path, filename)
    cv2.imwrite(save_path, roi)

    db_path = os.path.join("Detection", "saved_illegal", date_str, filename)

    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO illegal_vehicles (track_id, timestamp, class, x1, y1, x2, y2, image_path, cctvname)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (track_id, timestamp, 'illegal', x1, y1, x2, y2, db_path, cctvname))
    conn.commit()

    print(f"[✅ 저장 완료] {db_path}")