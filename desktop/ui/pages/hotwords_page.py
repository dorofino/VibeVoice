from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal


class HotwordsPage(QWidget):
    """Page for managing custom hotwords."""

    word_added = pyqtSignal(str)
    word_removed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        # Title
        title = QLabel("HOTWORDS")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        desc = QLabel("Custom words to improve speech recognition accuracy.")
        desc.setObjectName("shortcutDesc")
        layout.addWidget(desc)

        # Input row
        input_row = QHBoxLayout()
        self._input = QLineEdit()
        self._input.setPlaceholderText("Enter a new hotword...")
        self._input.setObjectName("hotwordInput")
        self._input.returnPressed.connect(self._add_word)
        input_row.addWidget(self._input)

        self._add_btn = QPushButton("Add")
        self._add_btn.setObjectName("accentButton")
        self._add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._add_btn.clicked.connect(self._add_word)
        input_row.addWidget(self._add_btn)
        layout.addLayout(input_row)

        # Word list
        self._list = QListWidget()
        self._list.setObjectName("hotwordList")
        layout.addWidget(self._list)

    def _add_word(self):
        word = self._input.text().strip()
        if word:
            self.word_added.emit(word)
            self._input.clear()

    def refresh(self, words: list[str]):
        self._list.clear()
        for word in words:
            item = QListWidgetItem()
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 4, 12, 4)

            label = QLabel(word)
            label.setObjectName("hotwordLabel")
            row_layout.addWidget(label)
            row_layout.addStretch()

            remove_btn = QPushButton("\u00D7")  # ×
            remove_btn.setObjectName("removeButton")
            remove_btn.setFixedSize(28, 28)
            remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            remove_btn.clicked.connect(lambda _, w=word: self.word_removed.emit(w))
            row_layout.addWidget(remove_btn)

            item.setSizeHint(row.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, row)
