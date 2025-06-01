import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout
)

from PyQt5.QtCore import Qt, QObject, pyqtSignal

from cctv_veiwer import CCTVViewer
from image_list import ImageBrowserWidget


class WorkerSignals(QObject):
    detection_made = pyqtSignal()


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CCTV 모니터링 + 챗봇")
        self.setGeometry(300, 100, 1600, 800)

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        self.signals = WorkerSignals()

        # 1️⃣ 왼쪽: CCTV 버튼 리스트
        self.cctv_viewer = CCTVViewer(signals=self.signals)
        main_layout.addLayout(self.cctv_viewer.button_layout, 2)

        # 2️⃣ 중앙: VLC 영상 영역
        video_layout = QVBoxLayout()
        video_layout.addWidget(self.cctv_viewer.video_frame, 8)
        video_layout.addWidget(self.cctv_viewer.play_button, 1)
        video_layout.addWidget(self.cctv_viewer.stop_button, 1)
        main_layout.addLayout(video_layout, 5)

        # 3️⃣ 오른쪽: 이미지 리스트 (탐지 결과)
        self.image_browser = ImageBrowserWidget()
        self.signals.detection_made.connect(self.image_browser.handle_new_detection)
        main_layout.addWidget(self.image_browser, 5)

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



