from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon

from desktop.config import APP_NAME, APP_VERSION


class SidebarButton(QPushButton):
    """Navigation button for the sidebar."""

    def __init__(self, text: str, icon_char: str = "", parent=None):
        super().__init__(parent)
        label = f"  {icon_char}  {text}" if icon_char else f"  {text}"
        self.setText(label)
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("sidebarButton")


class MainWindow(QMainWindow):
    """Main application window with sidebar navigation (Vibing-like)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(800, 550)
        self.resize(900, 600)
        self.setObjectName("mainWindow")

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 16)
        sidebar_layout.setSpacing(4)

        # App title in sidebar
        from PyQt6.QtWidgets import QLabel
        title = QLabel(f"V  {APP_NAME.split()[0]}")
        title.setObjectName("sidebarTitle")
        title.setFixedHeight(48)
        sidebar_layout.addWidget(title)
        sidebar_layout.addSpacing(16)

        # Nav buttons
        self._nav_buttons: list[SidebarButton] = []
        nav_items = [
            ("Home", "\u2302"),       # ⌂
            ("History", "\u21BA"),     # ↺
            ("Hotwords", "\u2726"),    # ✦
            ("Settings", "\u2699"),    # ⚙
        ]
        for text, icon in nav_items:
            btn = SidebarButton(text, icon)
            btn.clicked.connect(lambda checked, t=text: self._on_nav(t))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Version label
        ver_label = QLabel(f"v{APP_VERSION}")
        ver_label.setObjectName("versionLabel")
        sidebar_layout.addWidget(ver_label)

        layout.addWidget(sidebar)

        # Content area
        self._stack = QStackedWidget()
        self._stack.setObjectName("contentStack")
        layout.addWidget(self._stack)

        # Page index map
        self._page_map: dict[str, int] = {}

    def add_page(self, name: str, widget: QWidget):
        idx = self._stack.addWidget(widget)
        self._page_map[name] = idx
        if len(self._page_map) == 1:
            self._select_nav(name)

    def _on_nav(self, name: str):
        self._select_nav(name)

    def _select_nav(self, name: str):
        if name in self._page_map:
            self._stack.setCurrentIndex(self._page_map[name])
        # Update button states
        for btn in self._nav_buttons:
            btn.setChecked(name in btn.text())

    def closeEvent(self, event):
        # Hide instead of close
        event.ignore()
        self.hide()
