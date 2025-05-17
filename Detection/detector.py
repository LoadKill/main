from ultralytics import YOLO

def load_model(weight_path):
    model = YOLO(weight_path)
    model.to('cpu')

    return model

def detect_vehicles(model, frame, conf_threshold=0.3):
    results = model(frame, conf=conf_threshold)[0]
    detections, illegal_boxes = [], []

    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        detections.append([x1, y1, x2, y2, conf])

        if cls_id == 1:
            illegal_boxes.append([x1, y1, x2, y2, conf])
    
    return detections, illegal_boxes