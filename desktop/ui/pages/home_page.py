from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
)
from PyQt6.QtCore import Qt


class StatCard(QFrame):
    """Card displaying a stat (words/uses)."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        self._title = QLabel(title)
        self._title.setObjectName("statTitle")
        layout.addWidget(self._title)

        row = QHBoxLayout()
        self._value = QLabel("0")
        self._value.setObjectName("statValue")
        row.addWidget(self._value)

        self._unit = QLabel("words")
        self._unit.setObjectName("statUnit")
        row.addWidget(self._unit)

        row.addSpacing(20)

        self._uses_value = QLabel("0")
        self._uses_value.setObjectName("statUsesValue")
        row.addWidget(self._uses_value)

        self._uses_unit = QLabel("uses")
        self._uses_unit.setObjectName("statUnit")
        row.addWidget(self._uses_unit)

        row.addStretch()
        layout.addLayout(row)

    def update_stats(self, words: int, uses: int):
        self._value.setText(f"{words:,}")
        self._uses_value.setText(f"{uses:,}")


class HomePage(QWidget):
    """Home page with usage statistics and hotkey info."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)

        # Title
        title = QLabel("Just speak it.")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Hotkey hint
        hint = QLabel("Hold  Ctrl+Shift+Win  to talk, release to insert text.")
        hint.setObjectName("hotkeyHint")
        layout.addWidget(hint)

        # Stat cards
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        self._today_card = StatCard("TODAY")
        cards_row.addWidget(self._today_card)

        self._total_card = StatCard("TOTAL")
        cards_row.addWidget(self._total_card)

        layout.addLayout(cards_row)

        # Keyboard shortcuts section
        shortcuts_frame = QFrame()
        shortcuts_frame.setObjectName("shortcutsFrame")
        sl = QVBoxLayout(shortcuts_frame)
        sl.setContentsMargins(20, 16, 20, 16)

        sl_title = QLabel("KEYBOARD SHORTCUTS")
        sl_title.setObjectName("sectionTitle")
        sl.addWidget(sl_title)

        # Transcribe
        row1 = QHBoxLayout()
        col1 = QVBoxLayout()
        col1.addWidget(QLabel("Transcribe"))
        desc1 = QLabel("Hold to dictate, release to insert text")
        desc1.setObjectName("shortcutDesc")
        col1.addWidget(desc1)
        row1.addLayout(col1)
        row1.addStretch()
        self._asr_key_label = QLabel("Ctrl+Shift+V")
        self._asr_key_label.setObjectName("hotkeyBadge")
        row1.addWidget(self._asr_key_label)
        sl.addLayout(row1)

        # Read aloud
        row2 = QHBoxLayout()
        col2 = QVBoxLayout()
        col2.addWidget(QLabel("Read Aloud"))
        desc2 = QLabel("Select text and press to hear it spoken")
        desc2.setObjectName("shortcutDesc")
        col2.addWidget(desc2)
        row2.addLayout(col2)
        row2.addStretch()
        self._tts_key_label = QLabel("Ctrl+Shift+R")
        self._tts_key_label.setObjectName("hotkeyBadge")
        row2.addWidget(self._tts_key_label)
        sl.addLayout(row2)

        layout.addWidget(shortcuts_frame)
        layout.addStretch()

    def refresh(self, today_stats: dict, total_stats: dict):
        self._today_card.update_stats(today_stats["words"], today_stats["uses"])
        self._total_card.update_stats(total_stats["words"], total_stats["uses"])

    def set_hotkeys(self, asr: str, tts: str):
        self._asr_key_label.setText(asr.replace("+", "+").upper())
        self._tts_key_label.setText(tts.replace("+", "+").upper())
