"""Floating capsule overlay using pure Win32 layered window. No Qt window = no DWM frame."""
import ctypes
import ctypes.wintypes
import math
import random
import threading

from PyQt6.QtCore import QObject, QTimer, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QImage
from PyQt6.QtWidgets import QApplication

# Win32 constants
WS_EX_LAYERED = 0x00080000
WS_EX_TOPMOST = 0x00000008
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_TRANSPARENT = 0x00000020
WS_EX_NOACTIVATE = 0x08000000
WS_POPUP = 0x80000000
ULW_ALPHA = 2
AC_SRC_OVER = 0
AC_SRC_ALPHA = 1
SW_SHOWNOACTIVATE = 4
SW_HIDE = 0

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class SIZE(ctypes.Structure):
    _fields_ = [("cx", ctypes.c_long), ("cy", ctypes.c_long)]


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_byte),
        ("BlendFlags", ctypes.c_byte),
        ("SourceConstantAlpha", ctypes.c_byte),
        ("AlphaFormat", ctypes.c_byte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
        ("biClrImportant", ctypes.c_uint32),
    ]


LRESULT = ctypes.c_ssize_t  # 64-bit on x64
WPARAM = ctypes.c_size_t
LPARAM = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_void_p, ctypes.c_uint, WPARAM, LPARAM)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint), ("style", ctypes.c_uint),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p), ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p), ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", ctypes.c_wchar_p), ("lpszClassName", ctypes.c_wchar_p),
        ("hIconSm", ctypes.c_void_p),
    ]

user32.DefWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_uint, WPARAM, LPARAM]
user32.DefWindowProcW.restype = LRESULT

_wndproc_ref = None  # prevent GC


def _default_wndproc(hwnd, msg, wparam, lparam):
    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


class FloatingCapsule(QObject):
    """Pure Win32 layered window capsule — zero DWM frame."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._pill_w = 310
        self._pill_h = 52
        self._hwnd = None
        self._visible = False

        self._mode = "idle"
        self._status_text = ""
        self._bars = [0.3, 0.5, 0.7, 0.5, 0.3, 0.6, 0.4]
        self._bar_phase = 0

        self._bar_timer = QTimer(self)
        self._bar_timer.timeout.connect(self._tick)
        self._bar_timer.setInterval(80)

        self._create_window()

    def _create_window(self):
        global _wndproc_ref
        _wndproc_ref = WNDPROC(_default_wndproc)

        hInstance = kernel32.GetModuleHandleW(None)
        class_name = "VibeVoiceCapsule"

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = _wndproc_ref
        wc.hInstance = hInstance
        wc.lpszClassName = class_name
        user32.RegisterClassExW(ctypes.byref(wc))

        ex_style = WS_EX_LAYERED | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TRANSPARENT

        self._hwnd = user32.CreateWindowExW(
            ex_style, class_name, "", WS_POPUP,
            0, 0, self._pill_w, self._pill_h,
            None, None, hInstance, None
        )

    def _render(self):
        if not self._hwnd or not self._visible:
            return

        w, h = self._pill_w, self._pill_h
        img = QImage(QSize(w, h), QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(QColor(0, 0, 0, 0))

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._paint(p, w, h)
        p.end()

        hdcScreen = user32.GetDC(0)
        hdcMem = gdi32.CreateCompatibleDC(hdcScreen)

        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth = w
        bmi.biHeight = -h
        bmi.biPlanes = 1
        bmi.biBitCount = 32

        ppvBits = ctypes.c_void_p()
        hBitmap = gdi32.CreateDIBSection(hdcMem, ctypes.byref(bmi), 0, ctypes.byref(ppvBits), None, 0)

        if hBitmap and ppvBits.value:
            hOld = gdi32.SelectObject(hdcMem, hBitmap)
            bits = img.constBits()
            bits.setsize(w * h * 4)
            ctypes.memmove(ppvBits.value, bytes(bits), w * h * 4)

            pos = self._get_position()
            ptDst = POINT(pos[0], pos[1])
            szWnd = SIZE(w, h)
            ptSrc = POINT(0, 0)
            blend = BLENDFUNCTION(AC_SRC_OVER, 0, 255, AC_SRC_ALPHA)

            user32.UpdateLayeredWindow(
                self._hwnd, hdcScreen, ctypes.byref(ptDst), ctypes.byref(szWnd),
                hdcMem, ctypes.byref(ptSrc), 0, ctypes.byref(blend), ULW_ALPHA
            )

            gdi32.SelectObject(hdcMem, hOld)
            gdi32.DeleteObject(hBitmap)

        gdi32.DeleteDC(hdcMem)
        user32.ReleaseDC(0, hdcScreen)

    def _get_position(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self._pill_w) // 2
            y = geo.y() + geo.height() - self._pill_h - 80
            return (x, y)
        return (100, 100)

    # --- Public API ---

    def show_loading(self, text: str = "Loading models..."):
        self._set("loading", text)
        self._bar_timer.start()
        self._show()

    def update_loading(self, text: str):
        self._status_text = text

    def show_ready(self):
        self._set("done", "VibeVoice Active")
        self._bar_timer.stop()
        self._render()
        QTimer.singleShot(2000, self.hide_capsule)

    def show_recording(self):
        self._set("recording", "Listening...")
        self._bar_timer.start()
        self._show()

    def show_transcribing(self):
        self._set("processing", "Transcribing...")
        if not self._bar_timer.isActive():
            self._bar_timer.start()

    def show_enhancing(self):
        self._set("processing", "Enhancing...")

    def show_polishing(self):
        self._set("processing", "Polishing...")

    def show_done(self, text: str = ""):
        preview = text[:42] + "..." if len(text) > 42 else text
        self._set("done", preview or "Done")
        self._bar_timer.stop()
        self._render()
        QTimer.singleShot(1800, self.hide_capsule)

    def show_speaking(self):
        self._set("speaking", "Speaking...")
        self._bar_timer.start()
        self._show()

    def hide_capsule(self):
        self._mode = "idle"
        self._status_text = ""
        self._bar_timer.stop()
        self._visible = False
        if self._hwnd:
            user32.ShowWindow(self._hwnd, SW_HIDE)

    # --- Internals ---

    def _set(self, mode, text):
        self._mode = mode
        self._status_text = text

    def _show(self):
        self._visible = True
        if self._hwnd:
            user32.ShowWindow(self._hwnd, SW_SHOWNOACTIVATE)
        self._render()

    def _tick(self):
        self._bars = [min(1.0, max(0.15, b + random.uniform(-0.3, 0.3))) for b in self._bars]
        self._bar_phase += 1
        self._render()

    def _paint(self, p: QPainter, w: int, h: int):
        r = h / 2

        # Background
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(14, 15, 35, 245))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # Border
        bc = {
            "recording": QColor(255, 80, 80),
            "processing": QColor(108, 143, 255),
            "loading": QColor(180, 140, 255),
            "done": QColor(76, 175, 80),
            "speaking": QColor(108, 143, 255),
        }.get(self._mode, QColor(50, 50, 80))

        p.setPen(QPen(bc, 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(1, 1, w - 2, h - 2), r - 1, r - 1)

        # Left indicator
        ix = 18
        if self._mode == "recording":
            self._draw_bars(p, ix, 0, h, QColor(255, 100, 100))
        elif self._mode in ("processing", "loading"):
            self._draw_spinner(p, ix + 20, 0, h)
        elif self._mode == "done":
            p.setPen(QPen(QColor(76, 175, 80), 2.5))
            p.setFont(QFont("Segoe UI", 16))
            p.drawText(ix + 6, int(h / 2 + 7), "\u2713")
        elif self._mode == "speaking":
            self._draw_bars(p, ix, 0, h, QColor(108, 143, 255))

        # Text
        tx = 88 if self._mode != "done" else 50
        p.setPen(QColor(220, 220, 240))
        p.setFont(QFont("Segoe UI", 12))
        p.drawText(QRectF(tx, 0, w - tx - 16, h),
                   Qt.AlignmentFlag.AlignVCenter, self._status_text)

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
