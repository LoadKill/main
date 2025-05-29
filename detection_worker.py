import threading
import cv2
import torch
import torch.nn as nn
import timm
import logging
from Detection.detector import load_model, detect_trucks, classify_truck_img
from Detection.tracker import init_tracker, update_tracks
from Detection.db import init_db, is_already_saved, save_illegal_vehicle
from Detection.utils import draw_tracks, match_with_track
import onnxruntime
from torchvision import transforms
from PIL import Image
import numpy as np


class DetectionWorker(threading.Thread):
    def __init__(self, stream_url, cctvname, signal_handler=None):
        super().__init__()
        self.stream_url = stream_url
        self.cctvname = cctvname
        self.running = True
        self.signals = signal_handler  # PyQt용 시그널 핸들러 등

        # YOLOv8 로드
        self.model = load_model("yolov8_n.pt").to("cuda")  # !! 모델 경로 확인 필요 !!
        logging.getLogger("ultralytics").setLevel(logging.ERROR)

        # 분류 모델 수정
        self.onnx_session = onnxruntime.InferenceSession(
            'final_classification.onnx',  # !! 모델 경로 확인 필요 !!
            providers = ['CUDAExecutionProvider']
        )

        self.onnx_input_name = self.onnx_session.get_inputs()[0].name

        self.onnx_transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5])
        ])

        # 트래커 초기화
        self.tracker = init_tracker()

    def run(self):
        conn, cursor = init_db()
        cap = cv2.VideoCapture(self.stream_url)
        print(f"[{self.cctvname}] 스트림 시작")

        try:
            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    continue

                # 1. 트럭 감지
                truck_boxes = detect_trucks(self.model, frame)

                # 2. 트래킹
                tracks = update_tracks(self.tracker, truck_boxes)

                for box in truck_boxes:
                    # 3. 트래킹 ID 매칭
                    track_id = match_with_track(box, tracks)
                    if track_id is None:
                        continue

                    # 4. 크롭
                    x1, y1, x2, y2, _ = map(int, box)
                    roi = frame[y1:y2, x1:x2]
                    if roi.size == 0:
                        continue
                    
                    # 5. 분류
                    label = self.classify_onnx(roi)
                    print(f"[{self.cctvname}] 분류 결과: {label} / ID: {track_id}")

                    # 6. DB 저장
                    if label == 'illegal' and not is_already_saved(cursor, track_id):
                        print(f"[{self.cctvname}] 🚨 불법 차량 저장 (ID: {track_id})")
                        save_illegal_vehicle(frame, box, track_id, cursor, conn, self.cctvname)

                        if self.signals:
                            self.signals.detection_made.emit()

        finally:
            cap.release()
            conn.close()
            print(f"[{self.cctvname}] 스트림 종료")


    def classify_onnx(self, image):
        pil_img = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        input_tensor = self.onnx_transform(pil_img).unsqueeze(0).numpy()

        output = self.onnx_session.run(None, {self.onnx_input_name: input_tensor})
        logit = output[0][0][0]
        prob = 1 / (1 + np.exp(-logit))

        return 'illegal' if prob < 0.5 else 'legal'
    
    def stop(self):
        self.running = False