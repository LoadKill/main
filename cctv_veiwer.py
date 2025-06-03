import os
import sys
import requests
import vlc
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFrame, QInputDialog, QLabel
from PyQt5.QtCore import QObject, pyqtSignal
from dotenv import load_dotenv

from detection_worker import DetectionWorker  # 👈 경로에 맞게 조정 필요

# VLC DLL 경로 추가
os.add_dll_directory(r"C:\Program Files\VLC")  # 실제 경로 확인 필요
load_dotenv()
api_key = os.getenv('ITS_API_KEY')


class WorkerSignals(QObject):
    detection_made = pyqtSignal()


class CCTVViewer(QWidget):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals
        self.worker = None

        # 버튼 레이아웃
        self.button_layout = QVBoxLayout()

        self.cctv_list = self.get_cctv_list()
        # 📌 시연 영상 URL 리스트
        self.test_urls = [
            "Detection/sample/bandicam 2025-05-15 14-21-50-048.mp4",  # 시연1 영상 URL 나중에 넣으면 됨용
            "Detection/sample/bandicam 2025-05-28 10-48-03-117.mp4",  # 시연2
            ""   # 시연3
        ]

        for cctv in self.cctv_list[:10]:
            btn = QPushButton(cctv['cctvname'])
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda _, url=cctv['cctvurl'], name=cctv['cctvname']: self.play_stream(url, name))
            self.button_layout.addWidget(btn)

        for i in range(1, 4):
            test_btn = QPushButton(f"시연{i}")
            test_btn.setFixedHeight(40)
            test_btn.clicked.connect(lambda _, url=self.test_urls[i-1], name=f"시연{i}": self.play_stream(url, name))
            self.button_layout.addWidget(test_btn)        


        # 영상 출력용 프레임
        self.video_frame = QFrame()
        self.video_frame.setFixedHeight(500)
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 24px;")


        self.stop_button = QPushButton("영상 끄기")
        self.stop_button.setFixedHeight(40)
        self.stop_button.clicked.connect(self.stop_stream)

            # 👉 영상 설명란 (아래에 추가)
        self.video_desc_label = QLabel("여기에 CCTV 영상에 대한 설명이 나옵니다.")
        self.video_desc_label.setWordWrap(True)
        self.video_desc_label.setStyleSheet("font-size: 15px; color: #333; background: #f5f5f5; padding: 6px; border-radius: 10px;")
        self.video_desc_label.setMinimumHeight(36)
        self.video_desc_label.setMaximumHeight(60)  # 2줄 정도

        # VLC 초기화
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        self.set_vlc_output()

    def set_vlc_output(self):
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
        api_key = "b226eb0b73d2424487a3928f519a9ea4"
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=124&maxX=130&minY=33&maxY=39&getType=json"
        response = requests.get(api_url)
        data = response.json()

        # 내가 보고싶은 CCTV 이름 리스트
        target_names = [
            "하동터널(순천1 1)", "부곡1교", "횡성대교시점", "[인천2]광교방음터널(인천2외부1)",
            "광교방음터널(강릉외부1)", "광교방음터널(강릉5)", "광교방음터널(인천2)",
            "[인천2]광교방음터널(인천2외부2)", "광교방음터널(인천2 5)", "싸리재", "싸리재1", "서초"
        ]

        # target_names 중 이름이 포함된 CCTV만 필터링
        cctv_list = [
            cctv for cctv in data['response']['data']
            if any(name in cctv['cctvname'] for name in target_names)
        ]

        return cctv_list


    def play_stream(self, url, cctvname):
        print(f"\n🎥 재생할 CCTV URL: {url}")
        self.player.stop()
        media = self.instance.media_new(url)
        self.player.set_media(media)
        self.player.play()

        if self.worker:
            self.worker.stop()
            self.worker.join()

        self.worker = DetectionWorker(url, cctvname, signal_handler=self.signals)
        self.worker.start()

    def stop_stream(self):
        self.player.stop()
        if self.worker:
            self.worker.stop()
            self.worker.join()
            self.worker = None
        print("🛑 영상 중지됨")

