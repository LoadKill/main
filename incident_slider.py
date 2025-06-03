
from PyQt5.QtWidgets import QWidget, QLabel
from PyQt5.QtCore import QPropertyAnimation, QPoint, QTimer

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