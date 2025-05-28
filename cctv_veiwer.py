import os
import sys
import requests
import vlc
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFrame, QInputDialog
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
        for cctv in self.cctv_list[:10]:
            btn = QPushButton(cctv['cctvname'])
            btn.setFixedHeight(40)
            btn.clicked.connect(lambda _, url=cctv['cctvurl'], name=cctv['cctvname']: self.play_stream(url, name))
            self.button_layout.addWidget(btn)

        # 영상 출력용 프레임
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 24px;")

        # 재생 및 중지 버튼
        self.play_button = QPushButton("URL로 영상 재생")
        self.play_button.setFixedHeight(40)
        self.play_button.clicked.connect(self.prompt_for_video_url)

        self.stop_button = QPushButton("영상 끄기")
        self.stop_button.setFixedHeight(40)
        self.stop_button.clicked.connect(self.stop_stream)

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
        api_url = (
            f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex"
            f"&cctvType=1&minX=126.8&maxX=126.9&minY=36.7&maxY=37.0&getType=json"
        )
        response = requests.get(api_url)
        data = response.json()
        return data['response']['data']

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
