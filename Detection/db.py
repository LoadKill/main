import sqlite3
from datetime import datetime
import cv2
import os
import numpy as np

def init_db():
    # 항상 Detection 폴더 내 DB로 고정
    db_path = os.path.join(os.path.dirname(__file__), "illegal_vehicle.db")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS illegal_vehicles (
        track_id INTEGER PRIMARY KEY,
        timestamp TEXT,
        class TEXT,
        x1 INTEGER, y1 INTEGER, x2 INTEGER, y2 INTEGER,
        image_path TEXT,
        cctvname TEXT,
        analysis_result TEXT
    )""")
    conn.commit()

    return conn, cursor



def is_already_saved(cursor, track_id):
    cursor.execute("SELECT 1 FROM illegal_vehicles WHERE track_id=?", (track_id,))
    return cursor.fetchone() is not None


def save_illegal_vehicle(frame, box_or_track, track_id, cursor, conn, cctvname=""):
    if hasattr(box_or_track, "to_ltrb"):
        x1, y1, x2, y2 = map(int, box_or_track.to_ltrb())
    else:
        x1, y1, x2, y2 = map(int, box_or_track)
    h, w = frame.shape[:2]

    # (선택) margin 조금 넓히기
    margin = 0.1
    bw, bh = x2 - x1, y2 - y1
    x1 = max(0, int(x1 - bw * margin))
    y1 = max(0, int(y1 - bh * margin))
    x2 = min(w, int(x2 + bw * margin))
    y2 = min(h, int(y2 + bh * margin))

    roi = frame[y1:y2, x1:x2]
    
    # (선택) 보간법
    MIN_SIZE = 224
    rh, rw = roi.shape[:2]
    if rh < MIN_SIZE or rw < MIN_SIZE:
        roi = cv2.resize(roi, (max(rw, MIN_SIZE), max(rh, MIN_SIZE)), interpolation=cv2.INTER_CUBIC)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")

    folder_path = os.path.join("Detection", "saved_illegal", date_str)
    os.makedirs(folder_path, exist_ok=True)

    filename = f"illegal_{track_id}_{time_str}.jpg"
    save_path = os.path.join(folder_path, filename)
    cv2.imwrite(save_path, roi, [cv2.IMWRITE_JPEG_QUALITY, 95])

   # 전체 프레임에 박스 그려 저장
    frame_with_box = frame.copy()
    # 원본 박스 좌표로 그림 (margin 좌표 말고!)
    if hasattr(box_or_track, "to_ltrb"):
        x1_box, y1_box, x2_box, y2_box = map(int, box_or_track.to_ltrb())
    else:
        x1_box, y1_box, x2_box, y2_box = map(int, box_or_track[:4])
    cv2.rectangle(frame_with_box, (x1_box, y1_box), (x2_box, y2_box), (0, 0, 255), 3)  # 빨간 박스

    # 원본이미지 저장 폴더 위치:/탐지 이미지/
    original_path = os.path.join("탐지 이미지", date_str)
    os.makedirs(original_path, exist_ok=True)
    original_save_path = os.path.join(original_path, f"{cctvname}_{time_str}.jpg")
    cv2.imwrite(original_save_path, frame_with_box, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    #crop된 이미지 저장 폴더 위치:/Detection/saved_illegal
    db_path = os.path.join("Detection", "saved_illegal", date_str, filename)
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")


    cursor.execute("""
        INSERT INTO illegal_vehicles (track_id, timestamp, class, x1, y1, x2, y2, image_path, cctvname, analysis_result)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (track_id, timestamp, 'illegal', x1, y1, x2, y2, db_path, cctvname, None))
    conn.commit()

    print(f"[✅ 저장 완료] {db_path}")