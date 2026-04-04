import ctypes
import math
import random

from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QRegion, QBitmap, QPainterPath


class FloatingCapsule(QWidget):
    """Floating pill-shaped widget showing processing stages.

    Uses a window region mask to eliminate the DWM border entirely.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._pill_w = 310
        self._pill_h = 52
        # No shadow margin — we clip to pill shape so no room for shadow anyway
        self.setFixedSize(self._pill_w, self._pill_h)

        # Apply a rounded region mask to completely remove any OS frame
        self._apply_mask()

        self._mode = "idle"
        self._status_text = ""
        self._bars = [0.3, 0.5, 0.7, 0.5, 0.3, 0.6, 0.4]
        self._bar_phase = 0

        # Safety: force hide after 12s no matter what
        self._safety_timer = QTimer(self)
        self._safety_timer.setSingleShot(True)
        self._safety_timer.timeout.connect(self._force_hide)

        self._bar_timer = QTimer(self)
        self._bar_timer.timeout.connect(self._bar_tick)
        self._bar_timer.setInterval(100)

    def _apply_mask(self):
        """Set a pill-shaped window mask. This completely removes any DWM frame."""
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self._pill_w, self._pill_h),
                            self._pill_h / 2, self._pill_h / 2)
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    # --- Public API ---

    def show_recording(self):
        self._set("recording", "Listening...")
        self._bar_timer.start()
        self._safety_timer.start(12000)
        self._position_on_screen()
        self.show()
        self.raise_()

    def show_transcribing(self):
        self._set("processing", "Transcribing...")
        self._safety_timer.start(12000)
        if not self._bar_timer.isActive():
            self._bar_timer.start()

    def show_enhancing(self):
        self._set("processing", "Enhancing...")
        self._safety_timer.start(12000)

    def show_polishing(self):
        self._set("processing", "Polishing...")
        self._safety_timer.start(12000)

    def show_done(self, text: str = ""):
        self._safety_timer.stop()
        preview = text[:42] + "..." if len(text) > 42 else text
        self._set("done", preview or "Done")
        self._bar_timer.stop()
        QTimer.singleShot(1800, self.hide_capsule)

    def show_speaking(self):
        self._set("speaking", "Speaking...")
        self._bar_timer.start()
        self._safety_timer.start(120000)
        self._position_on_screen()
        self.show()
        self.raise_()

    def hide_capsule(self):
        self._mode = "idle"
        self._status_text = ""
        self._bar_timer.stop()
        self._safety_timer.stop()
        self.hide()

    # --- Internals ---

    def _force_hide(self):
        """Safety timeout — force hide and print warning."""
        print("[capsule] Safety timeout — force hiding")
        self.hide_capsule()

    def _set(self, mode: str, text: str):
        self._mode = mode
        self._status_text = text
        self.update()

    def _position_on_screen(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + geo.height() - self.height() - 80
            self.move(x, y)

    def _bar_tick(self):
        self._bars = [min(1.0, max(0.15, b + random.uniform(-0.3, 0.3))) for b in self._bars]
        self._bar_phase += 1
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self._pill_w, self._pill_h
        r = h / 2

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(14, 15, 35))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Border
        border_color = {
            "recording": QColor(255, 80, 80),
            "processing": QColor(108, 143, 255),
            "done": QColor(76, 175, 80),
            "speaking": QColor(108, 143, 255),
        }.get(self._mode, QColor(50, 50, 80))

        p.setPen(QPen(border_color, 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r - 1, r - 1)

        # Left indicator
        ix = 18
        if self._mode == "recording":
            self._draw_bars(p, ix, 0, h, QColor(255, 100, 100))
        elif self._mode == "processing":
            self._draw_spinner(p, ix + 20, 0, h)
        elif self._mode == "done":
            p.setPen(QPen(QColor(76, 175, 80), 2.5))
            p.setFont(QFont("Segoe UI", 16))
            p.drawText(ix + 6, int(h / 2 + 7), "\u2713")
        elif self._mode == "speaking":
            self._draw_bars(p, ix, 0, h, QColor(108, 143, 255))

        # Status text
        tx = 88 if self._mode != "done" else 50
        p.setPen(QColor(220, 220, 240))
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(QRectF(tx, 0, w - tx - 16, h),
                   Qt.AlignmentFlag.AlignVCenter, self._status_text)

        p.end()

    def _draw_bars(self, p, x0, y0, h, color):
        bw, gap = 4, 5
        cy = y0 + h / 2
        for i, lv in enumerate(self._bars):
            bh = lv * 22
            c = QColor(color)
            c.setAlpha(int(180 * lv + 75))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x0 + i * (bw + gap), cy - bh / 2, bw, bh), 2, 2)

    def _draw_spinner(self, p, cx, y0, h):
        cy = y0 + h / 2
        r = 10
        phase = (self._bar_phase % 30) / 30.0 * 2 * math.pi
        for i in range(3):
            a = phase + i * (2 * math.pi / 3)
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            alpha = 150 + int(105 * (1 + math.sin(a)) / 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(108, 143, 255, alpha))
            p.drawEllipse(QRectF(x - 3, y - 3, 6, 6))
