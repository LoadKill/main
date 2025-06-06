import os
import sys
import subprocess
from PyQt5.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QScrollArea,
    QPushButton, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap

from Detection.db import init_db


class AnalyzeWorker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, img_path):
        super().__init__()
        self.img_path = img_path

    def run(self):
        from chatbot import analyze_image
        result = analyze_image(self.img_path)
        self.finished.emit(result)


class ImageListItem(QWidget):
    analysis_finished = pyqtSignal()
    delete_requested = pyqtSignal(str)

    def __init__(self, timestamp, path, cctvname, parent):
        super().__init__()

        self.setFixedWidth(400)
        self.parent_widget = parent
        self.image_path = path
        self.is_expanded = False
        self.analysis_result = None
        self.analysis_running = False



        # 메인 레이아웃
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(5, 5, 5, 5)

       # 썸네일 + 제목 + 삭제 버튼 한 줄
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

        self.top_delete_button = QPushButton("삭제")
        self.top_delete_button.setStyleSheet("color: red; font-size: 12px; padding: 3px;")
        self.top_delete_button.setFixedWidth(48)
        self.top_delete_button.clicked.connect(self.request_delete)

        top_row.addWidget(self.thumbnail)
        top_row.addWidget(self.header)
        top_row.addWidget(self.top_delete_button)

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

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.close_button)

        expand_layout.addWidget(self.image_label)
        expand_layout.addWidget(self.chat_display)
        expand_layout.addLayout(btn_row)
        self.main_layout.addWidget(self.expand_frame)


        # [핵심 추가] 생성시 분석 결과가 있으면 즉시 preview_label에 표시
        from Detection.db import init_db
        conn, cursor = init_db()
        try:
            cursor.execute("SELECT analysis_result FROM illegal_vehicles WHERE image_path = ?", (self.image_path,))
            row = cursor.fetchone()
            if row and row[0]:
                first_line = row[0].strip().splitlines()[0]
                self.preview_label.setText(first_line)
                self.analysis_result = row[0]
        finally:
            conn.close()


    def request_delete(self):
        """부모에게 삭제 요청 신호 emit"""
        self.delete_requested.emit(self.image_path)

    def start_analysis(self):
        if self.analysis_running or self.analysis_result:
            return

        real_path = self.image_path
        print(f"[분석 시작] 이미지 경로: {real_path}")

        conn, cursor = init_db()
        try:
            cursor.execute("SELECT analysis_result FROM illegal_vehicles WHERE image_path = ?", (real_path,))
            row = cursor.fetchone()
            print("DB 결과:", row)

            if row and row[0]:
                self.analysis_result = row[0]
                first_line = row[0].strip().splitlines()[0]
                print("불러온 분석 요약:", first_line)
                self.preview_label.setText(first_line)

                self.analysis_finished.emit()
                return
        finally:
            conn.close()

        self.analysis_running = True
        self.preview_label.setText("🧠 분석 중...")

        # 🔵 QThread로 analyze_image 비동기 실행!
        self.worker = AnalyzeWorker(self.image_path)
        self.worker.finished.connect(self.analysis_done)
        self.worker.start()

    def analysis_done(self, result):

        self.analysis_result = result
        self.analysis_running = False
        first_line = result.strip().splitlines()[0] if result else "(결과 없음)"
        self.preview_label.setText(first_line)

        # DB에 분석결과 저장
        conn, cursor = init_db()
        try:
            cursor.execute("UPDATE illegal_vehicles SET analysis_result = ? WHERE image_path = ?", (result, self.image_path))
            conn.commit()
        finally:
            conn.close()

        self.parent_widget.update_analysis_result(self.image_path, result)# 분석이 끝난 뒤 메모리 리스트도 갱신
        self.analysis_finished.emit()

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
        self.all_db_rows = self.load_all_images_from_db()   # 처음 한 번만!
        self.current_filter = "all"

        # 버튼 이벤트 연결
        self.btn_all.clicked.connect(lambda: self.set_filter_mode("all"))
        self.btn_yes.clicked.connect(lambda: self.set_filter_mode("yes"))
        self.btn_no.clicked.connect(lambda: self.set_filter_mode("no"))

        self.populate_image_items()
        self.refresh_list("all")

        # 아래에 폴더 열기 버튼 추가
        self.open_folder_button = QPushButton("탐지 이미지 폴더 열기")
        self.open_folder_button.setStyleSheet("font-size: 13px; padding: 8px;")
        self.open_folder_button.clicked.connect(self.open_detected_folder)
        layout.addWidget(self.open_folder_button)

    def open_detected_folder(self):
        folder_path = "탐지 이미지"  # 실제 탐지 이미지 폴더 경로로 맞추세요
        abs_path = os.path.abspath(folder_path)
        if not os.path.exists(abs_path):
            os.makedirs(abs_path)  # 폴더 없으면 생성

        if sys.platform.startswith('darwin'):      # macOS
            subprocess.call(['open', abs_path])
        elif os.name == 'nt':                      # Windows
            os.startfile(abs_path)
        elif os.name == 'posix':                   # Linux
            subprocess.call(['xdg-open', abs_path])

    def load_all_images_from_db(self):
        conn, cursor = init_db()
        try:
            cursor.execute("SELECT timestamp, image_path, cctvname, analysis_result FROM illegal_vehicles ORDER BY timestamp DESC")
            return [
                (timestamp, path, cctvname, analysis_result)
                for timestamp, path, cctvname, analysis_result in cursor.fetchall()
                if os.path.exists(path)
            ]
        finally:
            conn.close()

    def set_filter_mode(self, mode):
        self.current_filter = mode
        self.refresh_list(mode)

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

        # 메모리 리스트에서 필터링
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
            item.delete_requested.connect(self.delete_image_item)
            self.vbox.addWidget(item)
            self.items.append(item)
            item.start_analysis()

        self.vbox.addStretch()
        # 분석 큐도 재설정
        self.analysis_queue = self.items
        self.analysis_index = 0
        self.run_next_analysis()



    def handle_new_detection(self, image_path):
        """새로 감지된 이미지 1건만 DB에서 불러와 메모리/화면에 추가."""
        conn, cursor = init_db()
        try:
            cursor.execute(
                "SELECT timestamp, image_path, cctvname, analysis_result FROM illegal_vehicles WHERE image_path=?",
                (image_path,)
            )
            row = cursor.fetchone()
            if row and os.path.exists(row[1]):
                self.all_db_rows.insert(0, row)  # 최신순 맨 앞에 추가
        finally:
            conn.close()
        self.refresh_list(self.current_filter)

    def update_analysis_result(self, image_path, new_result):
        """분석 결과만 UPDATE, 메모리에도 반영."""
        conn, cursor = init_db()
        try:
            cursor.execute("UPDATE illegal_vehicles SET analysis_result = ? WHERE image_path = ?", (new_result, image_path))
            conn.commit()
        finally:
            conn.close()
        # 메모리(리스트)에서 갱신
        for idx, (timestamp, path, cctvname, analysis_result) in enumerate(self.all_db_rows):
            if path == image_path:
                self.all_db_rows[idx] = (timestamp, path, cctvname, new_result)
                break

    def delete_image_item(self, image_path):
        # 1. DB에서 삭제
        conn, cursor = init_db()
        try:
            cursor.execute("DELETE FROM illegal_vehicles WHERE image_path = ?", (image_path,))
            conn.commit()
        finally:
            conn.close()
        # 2. 실제 파일 삭제
        if os.path.exists(image_path):
            try:
                os.remove(image_path)
            except Exception as e:
                print(f"파일 삭제 실패: {e}")

        # 3. 메모리에서 제거
        self.all_db_rows = [row for row in self.all_db_rows if row[1] != image_path]

        # 4. 리스트 새로고침
        self.refresh_list(self.current_filter)

    def run_next_analysis(self):
        if self.processing or not self.analysis_queue:
            return

        self.processing = True
        item = self.analysis_queue.pop(0)

        def on_finished():
            print(f"[✔] 분석 완료: {item.image_path}")
            self.processing = False
            item.analysis_finished.disconnect(on_finished)
            QTimer.singleShot(0, self.run_next_analysis)

        print(f"[▶] 분석 시작: {item.image_path}")
        item.analysis_finished.connect(on_finished)
        item.start_analysis()

    def collapse_all_except(self, current_item):
        for item in self.items:
            if item != current_item and item.is_expanded:
                item.expand_frame.setVisible(False)
                item.is_expanded = False