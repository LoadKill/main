import sys
import requests
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal
from dotenv import load_dotenv
import os
from cctv_veiwer import CCTVViewer
from image_list import ImageBrowserWidget
from slider import IncidentSlider, WeatherSlider, get_weather_messages, load_incident_data

load_dotenv()
api_key = os.getenv('ITS_API_KEY')

class WorkerSignals(QObject):
    detection_made = pyqtSignal()
    image_saved = pyqtSignal(str)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV 모니터링 + 돌발정보")
        self.setGeometry(300, 100, 1600, 800)

        # 전체 수평 레이아웃
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        self.signals = WorkerSignals()

        # 1️⃣ 왼쪽: CCTV 버튼 리스트 (버튼만! 영상/설명 넣지 마세요)
        self.cctv_viewer = CCTVViewer(signals=self.signals)
        main_layout.addLayout(self.cctv_viewer.button_layout, 2)

        # 2️⃣ 중앙: 한줄 슬라이드 + CCTV영상 + 끄기버튼 + 설명란 (위에서 아래로 세로배치)
        video_layout = QVBoxLayout()
        video_layout.setAlignment(Qt.AlignTop)  # 중앙에 위로 붙이기



        # 2-1 슬라이드

        self.weather_slider = WeatherSlider(width=self.cctv_viewer.video_frame.width())
        video_layout.addWidget(self.weather_slider)

        self.incident_slider = IncidentSlider(
            width=self.cctv_viewer.video_frame.width()
        )
        video_layout.addWidget(self.incident_slider)

        # 2-2 영상
        video_layout.addWidget(self.cctv_viewer.video_frame, 8)

        # 2-3 끄기버튼
        video_layout.addWidget(self.cctv_viewer.stop_button, 1)

        # 2-4 설명란
        video_layout.addWidget(self.cctv_viewer.video_desc_label)

        # 2-5 아래에 빈 공간
        video_layout.addStretch(1)

        # 중앙 영역 붙이기
        main_layout.addLayout(video_layout, 5)

        # 3️⃣ 오른쪽: 이미지 탐지 결과
        
        self.image_browser = ImageBrowserWidget()
        self.signals.image_saved.connect(self.image_browser.handle_new_detection)
        main_layout.addWidget(self.image_browser, 5)

        # 돌발 정보 메시지 로드 및 슬라이더에 세팅
        self.incident_messages = load_incident_data()
        if not self.incident_messages:
            self.incident_messages = ["현재 돌발 교통 정보가 없습니다."]
        self.incident_slider.set_messages(self.incident_messages)

        # API 주기적 갱신 타이머
        self.api_refresh_timer = QTimer()
        self.api_refresh_timer.timeout.connect(self.refresh_api_data)
        self.api_refresh_timer.start(1800 * 1000)  # 30분마다 API 갱신


        # [날씨] 메시지 세팅 및 타이머
        weather_msgs = get_weather_messages()
        if not weather_msgs:
            weather_msgs = ["현재 날씨 정보가 없습니다."]
        self.weather_slider.set_messages(weather_msgs)

        self.weather_timer = QTimer()
        self.weather_timer.timeout.connect(self.refresh_weather_data)
        self.weather_timer.start(3600 * 1000)

    def refresh_api_data(self):
        self.incident_messages = load_incident_data()
        if not self.incident_messages:
            self.incident_messages = ["현재 돌발 교통 정보가 없습니다."]
        self.incident_slider.set_messages(self.incident_messages)

    def refresh_weather_data(self):
        weather_msgs = get_weather_messages()
        if not weather_msgs:
            weather_msgs = ["현재 날씨 정보가 없습니다."]
        self.weather_slider.set_messages(weather_msgs)


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