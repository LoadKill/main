import sys
import requests
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

from cctv_veiwer import CCTVViewer
from image_list import ImageBrowserWidget
from incident_slider import IncidentSlider


class WorkerSignals(QObject):
    detection_made = pyqtSignal()


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
        self.signals.detection_made.connect(self.image_browser.handle_new_detection)
        main_layout.addWidget(self.image_browser, 5)

        # 돌발 정보 메시지 로드 및 슬라이더에 세팅
        self.incident_messages = self.load_incident_data()
        if not self.incident_messages:
            self.incident_messages = ["현재 돌발 교통 정보가 없습니다."]
        self.incident_slider.set_messages(self.incident_messages)

        # API 주기적 갱신 타이머
        self.api_refresh_timer = QTimer()
        self.api_refresh_timer.timeout.connect(self.refresh_api_data)
        self.api_refresh_timer.start(1800 * 1000)  # 30분마다 API 갱신

    def refresh_api_data(self):
        self.incident_messages = self.load_incident_data()
        if not self.incident_messages:
            self.incident_messages = ["현재 돌발 교통 정보가 없습니다."]
        self.incident_slider.set_messages(self.incident_messages)

    def load_incident_data(self):
        api_key = "8637559074094717b79ee9d5cbcabb0c"
        url = (
            f"https://openapi.its.go.kr:9443/eventInfo"
            f"?apiKey={api_key}&type=ex&eventType=all"
            f"&minX=124&maxX=132&minY=33&maxY=39&getType=json"
        )

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            events = data.get("body", {}).get("items", [])
            if not events:
                return []

            target_roads = ["남해선", "서해안선", "영동선", "경부선"]
            today = datetime.now().date()
            messages = []

            for event in events:
                road_name = event.get("roadName", "정보없음")
                if road_name not in target_roads:
                    continue

                start_raw = event.get("startDate", "")
                if not start_raw:
                    continue

                start_dt = datetime.strptime(start_raw, "%Y%m%d%H%M%S")
                if start_dt.date() != today:
                    continue

                event_type = event.get("eventType", "정보없음")
                msg = event.get("message", "정보없음")
                time_str = f"{start_dt.month}월{start_dt.day}일 {start_dt.hour:02d}:{start_dt.minute:02d}"

                messages.append(f"[{road_name}][{event_type}] {msg} ({time_str})")

            return messages

        except Exception as e:
            return [f"[API 오류] {str(e)}"]

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
