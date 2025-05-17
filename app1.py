import sys
import requests
import vlc
import os
import sqlite3
import threading
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QTextEdit, QLabel, QInputDialog, QTabWidget, QListWidget,
    QListWidgetItem, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from dotenv import load_dotenv
from chatbot import analyze_image
from Detection.detector import load_model, detect_vehicles
from Detection.tracker import init_tracker, update_tracks
from Detection.db import save_illegal_vehicle, init_db, is_already_saved
from Detection.utils import match_with_track

os.add_dll_directory(r"C:\Program Files\VLC")
load_dotenv()
api_key = os.getenv('ITS_API_KEY')


class DetectionWorker(threading.Thread):
    def __init__(self, stream_url, cctvname):
        super().__init__()
        self.stream_url = stream_url
        self.cctvname = cctvname
        self.running = True
        self.model = load_model("Detection/model/yolov8_n.pt").to('cuda')
        self.tracker = init_tracker()

    def run(self):
        conn, cursor = init_db()  # ✅ 이 위치로 이동
        cap = cv2.VideoCapture(self.stream_url)
        try:
            while self.running and cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    continue

                detections, illegal_boxes = detect_vehicles(self.model, frame)
                tracks = update_tracks(self.tracker, detections)

                for box in illegal_boxes:
                    matched_id = match_with_track(box, tracks)
                    if matched_id and not is_already_saved(cursor, matched_id):
                        save_illegal_vehicle(frame, box, matched_id, cursor, conn, self.cctvname)
        finally:
            cap.release()
            conn.close()  # ✅ 여기는 그대로 유지해도 됨 (같은 스레드이므로)
    
    def stop(self):
        self.running = False    


class CCTVViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITS CCTV Viewer")
        self.setGeometry(300, 100, 1300, 720)
        self.worker = None

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        button_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)

        self.cctv_list = self.get_cctv_list()
        for cctv in self.cctv_list[:10]:
            btn = QPushButton(f"{cctv['cctvname']}")
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda _, url=cctv['cctvurl'], name=cctv['cctvname']: self.play_stream(url, name))
            button_layout.addWidget(btn)

        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout)

        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 24px;")
        right_layout.addWidget(self.video_frame)

        self.play_button = QPushButton("URL로 영상 재생")
        self.play_button.setFixedHeight(40)
        self.play_button.clicked.connect(self.prompt_for_video_url)
        right_layout.addWidget(self.play_button)

        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        if sys.platform.startswith("linux"):
            self.player.set_xwindow(self.video_frame.winId())
        elif sys.platform == "win32":
            self.player.set_hwnd(self.video_frame.winId())
        elif sys.platform == "darwin":
            self.player.set_nsobject(int(self.video_frame.winId()))

    def prompt_for_video_url(self):
        video_url, ok = QInputDialog.getText(self, "URL 입력", "영상 URL을 입력하세요:")
        if ok and video_url:
            self.play_stream(video_url, "사용자입력")

    def get_cctv_list(self):
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=126.8&maxX=126.9&minY=36.7&maxY=37.0&getType=json"
        response = requests.get(api_url)
        data = response.json()
        return data['response']['data']

    def play_stream(self, url, cctvname):
        print(f"\n🎥 재생할 CCTV URL: {url}")
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()

        # ✅ 이전 스레드가 존재하면 안전하게 종료
        if self.worker:
            self.worker.stop()
            self.worker.join()  # <- 완전히 종료될 때까지 기다림

        # ✅ 새로운 탐지 스레드 시작
        self.worker = DetectionWorker(url, cctvname)
        self.worker.start()


class ChatbotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("챗봇")
        self.setGeometry(300, 100, 1000, 700)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.image_label = QLabel("이미지 미리보기")
        self.image_label.setFixedHeight(400)
        self.image_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.image_label)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

    def display_and_analyze_image(self, path):
        if not os.path.exists(path):
            QMessageBox.warning(self, "오류", "이미지 파일이 존재하지 않습니다.")
            return

        pixmap = QPixmap(path).scaled(self.image_label.width(), self.image_label.height(), Qt.KeepAspectRatio)
        self.image_label.setPixmap(pixmap)
        self.chat_display.setText("분석 중...")
        response = analyze_image(path)
        self.chat_display.setText(f"분석 결과:\n{response}")


class ImageBrowserWidget(QWidget):
    def __init__(self, chatbot_widget):
        super().__init__()
        self.setWindowTitle("적재 불량 차량 이미지")
        self.setGeometry(300, 100, 1000, 700)
        self.chatbot_widget = chatbot_widget

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.refresh_image_list)
        layout.addWidget(self.refresh_button)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.open_in_chatbot)
        layout.addWidget(self.list_widget)

        from Detection.db import init_db
        init_db()  # 테이블 보장
        self.populate_image_buttons()

    def populate_image_buttons(self):
        conn = sqlite3.connect("Detection/illegal_vehicle.db")
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT timestamp, image_path, cctvname FROM illegal_vehicles ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            for timestamp, path, cctvname in rows:
                display_text = f"{timestamp} [{cctvname}] {os.path.basename(path)}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, path)
                self.list_widget.addItem(item)
        finally:
            conn.close()

    def refresh_image_list(self):
        self.list_widget.clear()
        self.populate_image_buttons()

    def open_in_chatbot(self, item):
        path = item.data(Qt.UserRole)
        self.chatbot_widget.display_and_analyze_image(path)
        self.chatbot_widget.parent().setCurrentWidget(self.chatbot_widget)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV & Chatbot 탭 화면")
        self.setGeometry(300, 100, 1300, 720)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)

        self.cctv_viewer = CCTVViewer()
        self.chatbot_view = ChatbotWidget()
        self.image_browser = ImageBrowserWidget(self.chatbot_view)

        self.tabs.addTab(self.cctv_viewer, "CCTV 뷰어")
        self.tabs.addTab(self.image_browser, "적재 불량 차량 이미지")
        self.tabs.addTab(self.chatbot_view, "챗봇")

    def on_tab_changed(self, index):
        # 탭 전환 시 이미지 새로고침
        if index == 1:
            self.image_browser.refresh_image_list()

        # CCTV 감시 중지
        if index != 0 and self.cctv_viewer.worker:
            self.cctv_viewer.worker.stop()
            self.cctv_viewer.worker.join()
            self.cctv_viewer.worker = None

    def closeEvent(self, event):
        if self.cctv_viewer.worker:
            self.cctv_viewer.worker.stop()
            self.cctv_viewer.worker.join()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())