import cv2


def draw_tracks(frame, tracks):
    
    for track in tracks:
        x1, y1, x2, y2, track_id = track.astype(int)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"ID: {track_id}", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)


def compute_iou(box1, box2):
    x1, y1, x2, y2 = box1
    tx1, ty1, tx2, ty2 = box2

    inter_w = max(0, min(x2, tx2) - max(x1, tx1))
    inter_h = max(0, min(y2, ty2) - max(y1, ty1))
    intersection = inter_w * inter_h

    box_area = (x2 - x1) * (y2 - y1)
    track_area = (tx2 - tx1) * (ty2 - ty1)
    union = box_area + track_area - intersection

    return intersection / union if union > 0 else 0


def match_with_track(box, tracks, iou_threshold=0.1):
    x1, y1, x2, y2, _ = box

    for track in tracks:
        tx1, ty1, tx2, ty2, track_id = track.astype(int)

        iou = compute_iou((x1, y1, x2, y2), (tx1, ty1, tx2, ty2))

        if iou > iou_threshold:

            return int(track_id)

    return None