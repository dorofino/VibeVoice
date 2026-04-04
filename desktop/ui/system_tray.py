from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import pyqtSignal


def _create_default_icon() -> QIcon:
    """Create a simple colored icon programmatically."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(85, 98, 255))
    painter.setPen(QColor(85, 98, 255))
    painter.drawEllipse(4, 4, 56, 56)
    painter.setPen(QColor(255, 255, 255))
    painter.setFont(QFont("Arial", 28, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), 0x0084, "V")  # AlignCenter
    painter.end()
    return QIcon(pixmap)


class SystemTray(QSystemTrayIcon):
    """System tray icon with context menu."""

    show_window_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(_create_default_icon())
        self.setToolTip("VibeVoice Desktop")

        menu = QMenu()
        self._show_action = menu.addAction("Open VibeVoice")
        self._show_action.triggered.connect(self.show_window_requested.emit)
        menu.addSeparator()
        self._quit_action = menu.addAction("Quit")
        self._quit_action.triggered.connect(self.quit_requested.emit)
        self.setContextMenu(menu)

        self.activated.connect(self._on_activated)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show_window_requested.emit()

    def set_status(self, text: str):
        self.setToolTip(f"VibeVoice Desktop - {text}")
