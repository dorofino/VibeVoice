from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QFrame, QSlider, QLineEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal

from desktop.ui.pages._toggle_switch import ToggleSwitch


class SettingRow(QFrame):
    """A single settings row with label, description, and control."""

    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settingRow")
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(20, 14, 20, 14)

        text_col = QVBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("settingTitle")
        text_col.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setObjectName("settingDesc")
        desc_label.setWordWrap(True)
        text_col.addWidget(desc_label)

        self._layout.addLayout(text_col, stretch=1)

    def add_control(self, widget: QWidget):
        self._layout.addWidget(widget)


class SettingsPage(QWidget):
    """Settings page with toggles, dropdowns, and sliders."""

    dark_mode_changed = pyqtSignal(bool)
    enhanced_intent_changed = pyqtSignal(bool)
    ai_polish_changed = pyqtSignal(bool)
    api_key_changed = pyqtSignal(str)
    voice_changed = pyqtSignal(str)
    asr_mode_changed = pyqtSignal(str)
    steps_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        layout.addSpacing(8)

        # Dark Mode
        self._dark_toggle = ToggleSwitch()
        self._dark_toggle.toggled_signal.connect(self.dark_mode_changed.emit)
        row1 = SettingRow("Dark Mode", "Switch to a darker color scheme.")
        row1.add_control(self._dark_toggle)
        layout.addWidget(row1)

        # Anthropic API Key
        self._api_key_input = QLineEdit()
        self._api_key_input.setObjectName("apiKeyInput")
        self._api_key_input.setPlaceholderText("sk-ant-...")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setMinimumWidth(240)
        self._api_key_input.editingFinished.connect(
            lambda: self.api_key_changed.emit(self._api_key_input.text().strip())
        )
        row_api = SettingRow(
            "Anthropic API Key",
            "Required for Enhanced Intent Recognition and AI Text Polishing.",
        )
        row_api.add_control(self._api_key_input)
        layout.addWidget(row_api)

        # Enhanced Intent Recognition
        self._intent_toggle = ToggleSwitch()
        self._intent_toggle.toggled_signal.connect(self.enhanced_intent_changed.emit)
        row_intent = SettingRow(
            "Enhanced Intent Recognition",
            "Understands the current window context, improving input accuracy and formatting.",
        )
        row_intent.add_control(self._intent_toggle)
        layout.addWidget(row_intent)

        # AI Text Polishing
        self._polish_toggle = ToggleSwitch()
        self._polish_toggle.toggled_signal.connect(self.ai_polish_changed.emit)
        row_polish = SettingRow(
            "AI Text Polishing",
            "Uses Claude to polish the speech recognition result \u2014 fixing filler words, correcting homophones, and adjusting formatting.",
        )
        row_polish.add_control(self._polish_toggle)
        layout.addWidget(row_polish)

        # Voice selection
        self._voice_combo = QComboBox()
        self._voice_combo.setObjectName("settingCombo")
        self._voice_combo.setMinimumWidth(200)
        self._voice_combo.currentTextChanged.connect(self.voice_changed.emit)
        row2 = SettingRow("TTS Voice", "Select the voice for text-to-speech.")
        row2.add_control(self._voice_combo)
        layout.addWidget(row2)

        # ASR mode
        self._asr_combo = QComboBox()
        self._asr_combo.setObjectName("settingCombo")
        self._asr_combo.addItems(["local", "cloud"])
        self._asr_combo.currentTextChanged.connect(self.asr_mode_changed.emit)
        row3 = SettingRow("ASR Mode", "Local (faster-whisper) or cloud (Vibing API) for speech recognition.")
        row3.add_control(self._asr_combo)
        layout.addWidget(row3)

        # Inference steps
        steps_widget = QWidget()
        steps_layout = QHBoxLayout(steps_widget)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        self._steps_slider = QSlider(Qt.Orientation.Horizontal)
        self._steps_slider.setRange(3, 15)
        self._steps_slider.setValue(5)
        self._steps_slider.setFixedWidth(160)
        self._steps_label = QLabel("5")
        self._steps_label.setObjectName("sliderValue")
        self._steps_slider.valueChanged.connect(self._on_steps_changed)
        steps_layout.addWidget(self._steps_slider)
        steps_layout.addWidget(self._steps_label)
        row4 = SettingRow("Inference Steps", "Higher = better quality but slower TTS generation.")
        row4.add_control(steps_widget)
        layout.addWidget(row4)

        layout.addStretch()

    def _on_steps_changed(self, value: int):
        self._steps_label.setText(str(value))
        self.steps_changed.emit(value)

    def set_voices(self, voices: list[str], current: str):
        self._voice_combo.blockSignals(True)
        self._voice_combo.clear()
        self._voice_combo.addItems(voices)
        if current in voices:
            self._voice_combo.setCurrentText(current)
        self._voice_combo.blockSignals(False)

    def set_values(self, dark_mode: bool, asr_mode: str, steps: int,
                   enhanced_intent: bool = True, ai_polish: bool = True,
                   api_key: str = ""):
        self._dark_toggle.setChecked(dark_mode)
        self._intent_toggle.setChecked(enhanced_intent)
        self._polish_toggle.setChecked(ai_polish)
        if api_key:
            self._api_key_input.setText(api_key)
        self._asr_combo.blockSignals(True)
        self._asr_combo.setCurrentText(asr_mode)
        self._asr_combo.blockSignals(False)
        self._steps_slider.blockSignals(True)
        self._steps_slider.setValue(steps)
        self._steps_label.setText(str(steps))
        self._steps_slider.blockSignals(False)
