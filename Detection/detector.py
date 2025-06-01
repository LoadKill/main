from ultralytics import YOLO
import cv2
import torch
import numpy as np

def load_model(weight_path):
    model = YOLO(weight_path)
    model.to('cuda')

    return model

def detect_trucks(model, frame, truck_class_id=1, conf_threshold=0.3, iou=0.3):
    results = model(frame, conf=conf_threshold, iou=iou)[0]
    truck_boxes = []
    for box in results.boxes:
        cls_id = int(box.cls[0])
        if cls_id == truck_class_id:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            w, h = x2 - x1, y2 - y1
            conf = float(box.conf[0])
            truck_boxes.append(([x1, y1, w, h], conf, cls_id))
    return truck_boxes

def preprocess_for_classifier(img, input_size=224):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (input_size, input_size))
    img = img / 255.0
    img = (img - 0.5) / 0.5  # Normalize [0,1] -> [-1,1]
    img = np.transpose(img, (2,0,1))  # HWC -> CHW
    img = np.expand_dims(img, axis=0) # 배치 차원
    return torch.tensor(img, dtype=torch.float32)

def classify_truck_img(truck_img, classifier_model, device='cuda'):
    img_tensor = preprocess_for_classifier(truck_img)
    img_tensor = img_tensor.to(device)
    with torch.no_grad():
        output = classifier_model(img_tensor)
        pred = (output > 0.5).item()   # 0.5 이상이면 불법(1)
        if pred == 1:
            return 'illegal'
        else:
            return 'normal'
