from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QRectF, QPropertyAnimation, QEasingCurve, pyqtSignal, pyqtProperty
from PyQt6.QtGui import QPainter, QColor, QPen


class ToggleSwitch(QWidget):
    """iOS-style toggle switch."""

    toggled_signal = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(50, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._checked = False
        self._circle_pos = 4.0

        self._anim = QPropertyAnimation(self, b"circle_pos")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, checked: bool):
        if self._checked == checked:
            return
        self._checked = checked
        target = 26.0 if checked else 4.0
        self._anim.setStartValue(self._circle_pos)
        self._anim.setEndValue(target)
        self._anim.start()

    @pyqtProperty(float)
    def circle_pos(self):
        return self._circle_pos

    @circle_pos.setter
    def circle_pos(self, pos):
        self._circle_pos = pos
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        target = 26.0 if self._checked else 4.0
        self._anim.setStartValue(self._circle_pos)
        self._anim.setEndValue(target)
        self._anim.start()
        self.toggled_signal.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track
        if self._checked:
            track_color = QColor(76, 175, 80)  # Green
        else:
            track_color = QColor(120, 120, 130)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track_color)
        p.drawRoundedRect(QRectF(0, 0, 50, 28), 14, 14)

        # Circle
        p.setBrush(QColor(255, 255, 255))
        p.drawEllipse(QRectF(self._circle_pos, 4, 20, 20))
        p.end()
