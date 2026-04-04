from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal


class HistoryEntry(QFrame):
    """Single history entry widget."""

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("historyEntry")
        self._data = data
        self._text = data.get("text", "")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        # Top row: timestamp + copy button
        top_row = QHBoxLayout()

        ts = data.get("timestamp", "")
        if "T" in ts:
            ts = ts.replace("T", " ").split(".")[0]
        time_label = QLabel(ts[-5:] if len(ts) > 5 else ts)
        time_label.setObjectName("entryTime")
        top_row.addWidget(time_label)
        top_row.addStretch()

        copy_btn = QPushButton("Copy")
        copy_btn.setObjectName("copyButton")
        copy_btn.setFixedHeight(26)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.clicked.connect(self._on_copy)
        top_row.addWidget(copy_btn)

        layout.addLayout(top_row)

        # Text (selectable)
        text_label = QLabel(self._text)
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        text_label.setObjectName("entryText")
        layout.addWidget(text_label)

        # Raw text (if different)
        raw = data.get("raw_text")
        if raw and raw != self._text:
            raw_label = QLabel(raw)
            raw_label.setWordWrap(True)
            raw_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            raw_label.setObjectName("entryRawText")
            layout.addWidget(raw_label)

    def _on_copy(self):
        from desktop.core.clipboard import _set_clipboard_text
        _set_clipboard_text(self._text)
        # Brief visual feedback
        btn = self.sender()
        if btn:
            btn.setText("Copied!")
            QTimer.singleShot(1500, lambda: btn.setText("Copy"))


class HistoryPage(QWidget):
    """History page showing transcription log."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("History")
        title.setObjectName("pageTitle")
        header.addWidget(title)
        header.addStretch()

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setObjectName("secondaryButton")
        self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("historyScroll")

        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(8)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

    @property
    def clear_button(self) -> QPushButton:
        return self._clear_btn

    def refresh(self, entries: list[dict]):
        # Clear existing
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add entries (most recent first)
        for entry in entries:
            widget = HistoryEntry(entry)
            self._container_layout.insertWidget(
                self._container_layout.count() - 1, widget
            )
