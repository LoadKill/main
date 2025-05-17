from detector import load_model, detect_vehicles
from tracker import init_tracker, update_tracks
from db import init_db, is_already_saved, save_illegal_vehicle
from utils import draw_tracks, match_with_track
from config import get_cctv_stream_url
import cv2


model = load_model("model/yolov8_n.pt")
tracker = init_tracker()
conn, cursor = init_db()

#cap = cv2.VideoCapture(get_cctv_stream_url())
cap = cv2.VideoCapture("sample/KakaoTalk_20250516_000636132.mp4")

while cap.isOpened():
    ret, frame = cap.read()

    if not ret:
        break

    detections, illegal_boxes = detect_vehicles(model, frame)
    tracks = update_tracks(tracker, detections)

    for box in illegal_boxes:
        matched_id = match_with_track(box, tracks)

        if matched_id and not is_already_saved(cursor, matched_id):
            save_illegal_vehicle(frame, box, matched_id, cursor, conn)

    draw_tracks(frame, tracks)
    cv2.imshow("ITS CCTV", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
conn.close()