
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import QPropertyAnimation, QPoint, QTimer
from datetime import datetime
import requests
import os
from dotenv import load_dotenv

load_dotenv()
weather_api_key = os.getenv('WEATHER_API_KEY')
api_key = os.getenv('ITS_API_KEY')

class IncidentSlider(QWidget):
    def __init__(self, width=800, height=36, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.messages = []
        self.index = -1

        self.label1 = QLabel("", self)
        self.label2 = QLabel("", self)
        for label in (self.label1, self.label2):
            label.setStyleSheet("""
                background-color: rgba(0,0,0,150);
                color: white;
                font-size: 16px;
                padding: 5px;
            """)
            label.setWordWrap(False)
            label.setFixedHeight(height)
            label.setFixedWidth(width)
            label.move(0, 0)
            label.raise_()
        self.current_label = self.label1
        self.next_label = self.label2

        self.slide_timer = QTimer(self)
        self.slide_timer.timeout.connect(self.slide_next)
        self.anim_out = None
        self.anim_in = None

    def set_messages(self, messages):
        self.messages = messages or ["현재 돌발 교통 정보가 없습니다."]
        self.index = -1
        self.current_label.setText(self.messages[0])
        self.next_label.setText("")
        if len(self.messages) > 1:
            self.slide_timer.start(4000)  # 4초마다 슬라이드
        else:
            self.slide_timer.stop()

    def slide_next(self):
        if not self.messages:
            return
        self.index = (self.index + 1) % len(self.messages)
        self.next_label.setText(self.messages[self.index])
        h = self.current_label.height()
        self.next_label.move(0, h)

        self.anim_out = QPropertyAnimation(self.current_label, b"pos")
        self.anim_out.setDuration(800)
        self.anim_out.setStartValue(QPoint(0, 0))
        self.anim_out.setEndValue(QPoint(0, -h))

        self.anim_in = QPropertyAnimation(self.next_label, b"pos")
        self.anim_in.setDuration(800)
        self.anim_in.setStartValue(QPoint(0, h))
        self.anim_in.setEndValue(QPoint(0, 0))

        self.anim_out.start()
        self.anim_in.start()
        # Swap labels after animation starts
        self.current_label, self.next_label = self.next_label, self.current_label

    def stop(self):
        self.slide_timer.stop()


class WeatherSlider(QWidget):
    def __init__(self, width=800, height=36, parent=None):
        super().__init__(parent)
        self.setFixedSize(width, height)
        self.messages = []
        self.index = -1

        self.label1 = QLabel("", self)
        self.label2 = QLabel("", self)
        for label in (self.label1, self.label2):
            label.setStyleSheet("""
                background-color: rgba(0,0,0,150);
                color: white;
                font-size: 16px;
                padding: 5px;
            """)
            label.setWordWrap(False)
            label.setFixedHeight(height)
            label.setFixedWidth(width)
            label.move(0, 0)
            label.raise_()
        self.current_label = self.label1
        self.next_label = self.label2

        self.slide_timer = QTimer(self)
        self.slide_timer.timeout.connect(self.slide_next)
        self.anim_out = None
        self.anim_in = None

    def set_messages(self, messages):
        self.messages = messages or ["현재 날씨 정보가 없습니다."]
        self.index = -1
        self.current_label.setText(self.messages[0])
        self.next_label.setText("")
        if len(self.messages) > 1:
            self.slide_timer.start(4000)
        else:
            self.slide_timer.stop()

    def slide_next(self):
        if not self.messages:
            return
        self.index = (self.index + 1) % len(self.messages)
        self.next_label.setText(self.messages[self.index])
        h = self.current_label.height()
        self.next_label.move(0, h)

        self.anim_out = QPropertyAnimation(self.current_label, b"pos")
        self.anim_out.setDuration(800)
        self.anim_out.setStartValue(QPoint(0, 0))
        self.anim_out.setEndValue(QPoint(0, -h))

        self.anim_in = QPropertyAnimation(self.next_label, b"pos")
        self.anim_in.setDuration(800)
        self.anim_in.setStartValue(QPoint(0, h))
        self.anim_in.setEndValue(QPoint(0, 0))

        self.anim_out.start()
        self.anim_in.start()
        self.current_label, self.next_label = self.next_label, self.current_label

    def stop(self):
        self.slide_timer.stop()

def get_weather_messages():
    region_stations = {
        "전라남도": [156, 157],
        "경기도": [112, 115, 116],
        "충청남도": [133, 134],
        "경상북도": [143, 144],
        "강원도": [105, 106],
        "서울": [108, 109],
        "대전": [131],
        "대구": [138],
        "부산": [159]
    }
    api_url = "https://apihub.kma.go.kr/api/typ01/url/kma_sfctm2.php"
    auth_key = weather_api_key
    messages = []

    for region, stations in region_stations.items():
        for stn in stations:
            params = {"stn": stn, "authKey": auth_key}
            try:
                response = requests.get(api_url, params=params, timeout=2)
            except Exception:
                continue
            if response.status_code != 200:
                continue
            lines = response.text.strip().splitlines()
            for line in lines:
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 4:
                    continue
                time_str = parts[0]
                month = time_str[4:6]
                day = time_str[6:8]
                hour = time_str[8:10]
                minute = time_str[10:12]
                temp = parts[2]
                rain = parts[3]
                humidity = parts[13] if len(parts) > 13 else "-9"
                if temp == "-9" or rain == "-9" or humidity == "-9":
                    continue
                msg = (
                    f"📍{region}  📅{month}월{day}일 🕒{hour}:{minute} "
                    f"🌡️{temp}°C 🌧️{rain}mm 💧{humidity}%"
                )
                messages.append(msg)
                break  # stn별 최신 1건만
    return messages

def load_incident_data():
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