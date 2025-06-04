import os
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap

from Detection.db import init_db
from chatbot import analyze_image

class ImageListItem(QWidget):
    def __init__(self, timestamp, path, cctvname, parent):
        super().__init__()
        self.parent_widget = parent
        self.image_path = path
        self.is_expanded = False
        self.analysis_result = None
        self.analysis_running = False

        self.setFixedWidth(400)

        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

        # 썸네일 + 제목
        top_row = QHBoxLayout()
        self.thumbnail = QLabel()
        self.thumbnail.setFixedSize(60, 40)
        self.thumbnail.setScaledContents(True)
        if os.path.exists(self.image_path):
            pixmap = QPixmap(self.image_path).scaled(60, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail.setPixmap(pixmap)

        self.header = QLabel(f"[{cctvname}] {timestamp}")
        self.header.setWordWrap(True)
        self.header.setFixedWidth(320)
        self.header.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.header.setStyleSheet("padding: 5px; background: transparent;")
        self.header.mousePressEvent = lambda event: self.toggle_expand()

        top_row.addWidget(self.thumbnail)
        top_row.addWidget(self.header)
        self.main_layout.addLayout(top_row)

        # 요약
        self.preview_label = QLabel("⏳ 분석 대기 중...")
        self.preview_label.setStyleSheet("color: gray; font-size: 12px; margin-left: 64px;")
        self.main_layout.addWidget(self.preview_label)

        # 확장 프레임
        self.expand_frame = QFrame()
        self.expand_frame.setStyleSheet("background-color: #f9f9f9; border: 1px solid #ccc;")
        self.expand_frame.setVisible(False)
        expand_layout = QVBoxLayout()
        self.expand_frame.setLayout(expand_layout)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setFixedHeight(350)

        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)

        self.close_button = QPushButton("닫기")
        self.close_button.clicked.connect(self.collapse)

        expand_layout.addWidget(self.image_label)
        expand_layout.addWidget(self.chat_display)
        expand_layout.addWidget(self.close_button)

        self.main_layout.addWidget(self.expand_frame)

    def start_analysis(self):
        if self.analysis_running or self.analysis_result:
            return
        
        conn, cursor = init_db()

        try:
            cursor.execute("SELECT analysis_result FROM illegal_vehicles WHERE image_path = ?", (self.image_path,))
            row = cursor.fetchone()
            if row and row[0]:
                self.analysis_result = row[0]
                self.preview_label.setText(row[0].strip().splitlines()[0])
                return  # 🔹 이미 분석된 결과가 있으므로 여기서 종료
        finally:
            conn.close()

        self.analysis_running = True
        self.preview_label.setText("🧠 분석 중...")

        result = analyze_image(self.image_path)
        print(result)
        self.analysis_result = result
        self.analysis_running = False
        first_line = result.strip().splitlines()[0] if result else "(결과 없음)"
        self.preview_label.setText(first_line)

        conn, cursor = init_db()
        try:
            cursor.execute("UPDATE illegal_vehicles SET analysis_result = ? WHERE image_path = ?", (result, self.image_path))
            conn.commit()
        finally:
            conn.close()


    def toggle_expand(self):
        self.parent_widget.collapse_all_except(self)

        if not self.is_expanded:
            if os.path.exists(self.image_path):
                pixmap = QPixmap(self.image_path).scaled(400, 250, Qt.KeepAspectRatio)
                self.image_label.setPixmap(pixmap)
            if self.analysis_result:
                self.chat_display.setText(f"분석 결과:\n{self.analysis_result}")
            else:
                self.chat_display.setText("아직 분석되지 않았습니다.")
            self.expand_frame.setVisible(True)
            self.is_expanded = True
        else:
            self.collapse()

    def collapse(self):
        self.expand_frame.setVisible(False)
        self.is_expanded = False




class ImageBrowserWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(500)
        layout = QVBoxLayout(self)
        self.setLayout(layout)

        # 1. [필터 버튼] 영역
        button_row = QHBoxLayout()
        self.btn_all = QPushButton("전체")
        self.btn_yes = QPushButton("적재불량(예)")
        self.btn_no = QPushButton("정상(아니오)")
        button_row.addWidget(self.btn_all)
        button_row.addWidget(self.btn_yes)
        button_row.addWidget(self.btn_no)
        layout.addLayout(button_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        content = QWidget()
        self.vbox = QVBoxLayout(content)
        content.setLayout(self.vbox)
        scroll.setWidget(content)

        self.items = []
        self.all_db_rows = []
        self.image_paths = set()
        self.analysis_queue = []
        self.analysis_index = 0
        self.processing = False

        # 버튼 이벤트 연결
        self.btn_all.clicked.connect(lambda: self.refresh_list("all"))
        self.btn_yes.clicked.connect(lambda: self.refresh_list("yes"))
        self.btn_no.clicked.connect(lambda: self.refresh_list("no"))

        self.populate_image_items()
        self.refresh_list("all")

    def populate_image_items(self):
        # 모든 DB 데이터를 미리 다 불러와 저장 (필터링 시 다시 리스트 구성)
        conn, cursor = init_db()
        try:
            cursor.execute("SELECT timestamp, image_path, cctvname, analysis_result FROM illegal_vehicles ORDER BY timestamp DESC")
            self.all_db_rows = [
                (timestamp, path, cctvname, analysis_result)
                for timestamp, path, cctvname, analysis_result in cursor.fetchall()
                if os.path.exists(path)
            ]
        finally:
            conn.close()

    def refresh_list(self, mode="all"):
        # 기존 아이템 clear (stretch도 함께 지워짐)
        for i in reversed(range(self.vbox.count())):
            item = self.vbox.itemAt(i)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            else:
                self.vbox.removeItem(item)
        self.items = []

        # 필터에 맞는 데이터만 리스트에 추가
        if mode == "all":
            filtered = self.all_db_rows
        elif mode == "yes":
            filtered = [row for row in self.all_db_rows if row[3] and "적재불량 여부: 예" in row[3]]
        elif mode == "no":
            filtered = [row for row in self.all_db_rows if row[3] and "적재불량 여부: 아니오" in row[3]]
        else:
            filtered = self.all_db_rows

        for timestamp, path, cctvname, _ in filtered:
            item = ImageListItem(timestamp, path, cctvname, self)
            self.vbox.addWidget(item)
            self.items.append(item)

        self.vbox.addStretch()

        # (필요하다면) 분석 큐도 재설정
        self.analysis_queue = self.items
        self.analysis_index = 0
        self.run_next_analysis()


    def handle_new_detection(self):
        # 새 탐지 발생(시그널)시 DB에서 가장 최근 이미지 1개만 추가
        conn, cursor = init_db()
        try:
            cursor.execute(
                "SELECT timestamp, image_path, cctvname, analysis_result FROM illegal_vehicles ORDER BY timestamp DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                timestamp, path, cctvname, analysis_result = row
                # 이미 리스트에 있는지 확인 (image_path 또는 timestamp 비교)
                for existing in self.all_db_rows:
                    if existing[1] == path:
                        return  # 이미 존재하면 추가하지 않음

                # 새 이미지는 항상 전체 목록에는 추가
                self.all_db_rows.insert(0, (timestamp, path, cctvname, analysis_result))

                # 현재 필터(모드) 상태 가져오기 (없으면 "all"로)
                current_mode = getattr(self, "last_mode", "all")

                # 필터 조건에 맞으면 리스트에 추가
                should_add = (
                    current_mode == "all" or
                    (current_mode == "yes" and analysis_result and "적재불량 여부: 예" in analysis_result) or
                    (current_mode == "no" and analysis_result and "적재불량 여부: 아니오" in analysis_result)
                )

                if should_add:
                    item = ImageListItem(timestamp, path, cctvname, self)
                    self.vbox.insertWidget(0, item)
                    self.items.insert(0, item)
                    self.analysis_queue.insert(0, item)
                    self.run_next_analysis()
        finally:
            conn.close()



    def run_next_analysis(self):
        if self.processing or self.analysis_index >= len(self.analysis_queue):
            return

        self.processing = True
        item = self.analysis_queue[self.analysis_index]

        def process():
            item.start_analysis()
            self.analysis_index += 1
            self.processing = False
            QTimer.singleShot(100, self.run_next_analysis)

        QTimer.singleShot(10, process)

    def collapse_all_except(self, current_item):
        for item in self.items:
            if item != current_item and item.is_expanded:
                item.expand_frame.setVisible(False)
                item.is_expanded = False