import os
import sys
import requests
import vlc
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFrame, QInputDialog, QLabel
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from dotenv import load_dotenv
import googlemaps
from detection_worker import DetectionWorker
from datetime import datetime

# VLC DLL 경로 추가
os.add_dll_directory(r"C:\Program Files\VLC")
load_dotenv()
api_key = os.getenv('ITS_API_KEY')
google_api_key = os.getenv('GOOGLE_API_KEY')


class WorkerSignals(QObject):
    detection_made = pyqtSignal()
    image_saved = pyqtSignal(str)


class CCTVViewer(QWidget):
    def __init__(self, signals):
        super().__init__()
        self.signals = signals
        self.worker = None

        # 버튼 레이아웃
        self.button_layout = QVBoxLayout()
        self.cctv_list = self.get_cctv_list()
        self.test_urls = [
            "Detection/sample/bandicam 2025-05-15 14-21-50-048.mp4",
            "Detection/sample/bandicam 2025-05-28 10-48-03-117.mp4",
            ""
        ]

        # CCTV 버튼 (좌표도 전달!)
        for cctv in self.cctv_list[:10]:
            btn = QPushButton(cctv['cctvname'])
            btn.setFixedHeight(40)
            btn.clicked.connect(
                lambda _, url=cctv['cctvurl'], name=cctv['cctvname'], x=cctv['coordx'], y=cctv['coordy']:
                    self.play_stream(url, name, x, y)
            )
            self.button_layout.addWidget(btn)

        # 테스트(시연) 버튼 (좌표 없음)
        for i in range(1, 4):
            test_btn = QPushButton(f"시연{i}")
            test_btn.setFixedHeight(40)
            test_btn.clicked.connect(
                lambda _, url=self.test_urls[i-1], name=f"시연{i}":
                    self.play_stream(url, name)
            )
            self.button_layout.addWidget(test_btn)

        # 영상 출력용 프레임
        self.video_frame = QFrame()
        self.video_frame.setFixedHeight(500)
        self.video_frame.setStyleSheet("background-color: #000; border-radius: 24px;")

        self.stop_button = QPushButton("영상 끄기")
        self.stop_button.setFixedHeight(40)
        self.stop_button.clicked.connect(self.stop_stream)

        self.video_desc_label = QLabel("여기에 CCTV 영상에 대한 설명이 나옵니다.")
        self.video_desc_label.setWordWrap(True)
        self.video_desc_label.setStyleSheet(
            "font-size: 15px; color: #333; background: #f5f5f5; padding: 6px; border-radius: 10px;")
        self.video_desc_label.setMinimumHeight(36)
        self.video_desc_label.setMaximumHeight(100)

        # 구글맵 클라이언트
        self.gmaps = googlemaps.Client(key=google_api_key)

        # 시계+스톱워치 타이머
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_timers)
        self.clock_timer.start(1000)  # 1초마다
        self.current_clock = datetime.now().strftime('%H:%M:%S')
        self.watch_start_time = None
        self.elapsed_str = "00:00:00"
        self.current_cctv_desc = ""

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
        api_url = f"https://openapi.its.go.kr:9443/cctvInfo?apiKey={api_key}&type=ex&cctvType=1&minX=124&maxX=130&minY=33&maxY=39&getType=json"
        response = requests.get(api_url)
        data = response.json()
        target_names = [
            "하동터널(순천1 1)", "부곡1교", "횡성대교시점", "[인천2]광교방음터널(인천2외부1)",
            "광교방음터널(강릉외부1)", "광교방음터널(강릉5)", "광교방음터널(인천2)",
            "[인천2]광교방음터널(인천2외부2)", "광교방음터널(인천2 5)", "싸리재", "싸리재1", "서초"
        ]
        cctv_list = [
            cctv for cctv in data['response']['data']
            if any(name in cctv['cctvname'] for name in target_names)
        ]
        
        return cctv_list

    def get_address_from_coord(self, lat, lng):
        try:
            result = self.gmaps.reverse_geocode((lat, lng), language='ko')
            if not result:
                return "주소 정보 없음"
            return result[0]['formatted_address']
        except Exception:
            return "주소 정보 가져오기 실패"

    def update_timers(self):
        # 실시간 시계
        self.current_clock = datetime.now().strftime('%H:%M:%S')
        # 스톱워치
        if self.watch_start_time:
            elapsed = datetime.now() - self.watch_start_time
            h, rem = divmod(elapsed.seconds, 3600)
            m, s = divmod(rem, 60)
            self.elapsed_str = f"{h:02d}:{m:02d}:{s:02d}"
            self.update_video_desc_label(show_time=True)
        else:
            self.elapsed_str = "00:00:00"
            self.update_video_desc_label(show_time=False)

    def update_video_desc_label(self, show_time=False):
        # 두 정보 모두 포함해서 표시
        if show_time:
            self.video_desc_label.setText(
                f"현재 시간: {self.current_clock}\n"
                f"시청 시간: {self.elapsed_str}\n"
                f"{self.current_cctv_desc}"
            )
        else:
            self.video_desc_label.setText(self.current_cctv_desc)
    

    def play_stream(self, url, cctvname, coordx=None, coordy=None):
        # 영상 바뀔 때마다 스톱워치 리셋
        self.watch_start_time = datetime.now()
        self.elapsed_str = "00:00:00"

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

        desc = f"재생중인 cctv : {cctvname}"
        if coordx and coordy:
            try:
                address = self.get_address_from_coord(coordy, coordx)  # lat, lng 순서!
                desc += f"\n[위치]: {address}"
            except Exception:
                desc += f"\n[위치]: 주소 정보 가져오기 실패"
        self.current_cctv_desc = desc
        self.update_video_desc_label()

    def stop_stream(self):
        self.player.stop()
        if self.worker:
            self.worker.stop()
            self.worker.join()
            self.worker = None
        print("🛑 영상 중지됨")
        self.watch_start_time = None  # 스톱워치 정지 및 리셋
        self.elapsed_str = "00:00:00"
        self.current_cctv_desc = "영상이 중지되었습니다."
        self.update_video_desc_label(show_time=False)
