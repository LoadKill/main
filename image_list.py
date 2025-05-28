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

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        content = QWidget()
        self.vbox = QVBoxLayout(content)
        content.setLayout(self.vbox)
        scroll.setWidget(content)

        self.items = []
        self.image_paths = set()
        self.analysis_queue = []
        self.analysis_index = 0
        self.processing = False

        self.populate_image_items()

    def populate_image_items(self):
        conn, cursor = init_db()
        try:
            cursor.execute("SELECT timestamp, image_path, cctvname FROM illegal_vehicles ORDER BY timestamp DESC")
            for timestamp, path, cctvname in cursor.fetchall():
                if not os.path.exists(path):
                    continue
                item = ImageListItem(timestamp, path, cctvname, self)
                #item.setFixedHeight(100)
                self.vbox.addWidget(item)
                self.items.append(item)
                self.analysis_queue.append(item)
            self.vbox.addStretch()
            self.run_next_analysis()
        finally:
            conn.close()

    def add_new_image_item(self, timestamp, path, cctvname, to_top=True):
        """새 이미지 감지(또는 DB에 추가)시 리스트에 동적으로 추가"""
        if path in self.image_paths:    # 중복 방지
            return
        item = ImageListItem(timestamp, path, cctvname, self)
        if to_top:
            self.vbox.insertWidget(0, item)      # 최신 이미지는 맨 위에 추가
            self.items.insert(0, item)
        else:
            self.vbox.addWidget(item)
            self.items.append(item)
        self.image_paths.add(path)               # 중복 방지용 집합에 경로 등록
        self.analysis_queue.append(item)
        self.run_next_analysis()                 # 필요시 바로 분석


    def handle_new_detection(self):
        """새 탐지 발생(시그널)시 DB에서 가장 최근 이미지 하나만 추가"""
        conn, cursor = init_db()
        try:
            cursor.execute("SELECT timestamp, image_path, cctvname FROM illegal_vehicles ORDER BY timestamp DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                timestamp, path, cctvname = row
                if os.path.exists(path):
                    self.add_new_image_item(timestamp, path, cctvname)
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