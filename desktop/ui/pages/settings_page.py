from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QFrame, QSlider, QLineEdit, QScrollArea, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal

from desktop.ui.pages._toggle_switch import ToggleSwitch


GROK_VOICES = ["eve", "ara", "rex", "sal", "leo"]


class SettingRow(QFrame):
    """A single settings row with label, description, and control."""

    def __init__(self, title: str, description: str, parent=None):
        super().__init__(parent)
        self.setObjectName("settingRow")
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(20, 14, 20, 14)
        self._layout.setSpacing(16)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
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
    grok_api_key_changed = pyqtSignal(str)
    engine_changed = pyqtSignal(str)      # "local" or "grok"
    voice_changed = pyqtSignal(str)       # local voice name
    grok_voice_changed = pyqtSignal(str)  # grok voice name
    asr_mode_changed = pyqtSignal(str)    # "local" or "cloud" (within local engine)
    steps_changed = pyqtSignal(int)
    cfg_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._local_voices: list[str] = []
        self._local_voice = ""
        self._grok_voice = "eve"

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Fixed title above the scroll area
        title_bar = QWidget()
        title_layout = QVBoxLayout(title_bar)
        title_layout.setContentsMargins(32, 28, 32, 8)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        title_layout.addWidget(title)
        outer.addWidget(title_bar)

        # Scroll area wraps the rows so the page stays usable at any height
        scroll = QScrollArea()
        scroll.setObjectName("settingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        outer.addWidget(scroll, stretch=1)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 8, 32, 28)
        layout.setSpacing(12)

        # Dark Mode
        self._dark_toggle = ToggleSwitch()
        self._dark_toggle.toggled_signal.connect(self.dark_mode_changed.emit)
        row_dark = SettingRow("Dark Mode", "Switch to a darker color scheme.")
        row_dark.add_control(self._dark_toggle)
        layout.addWidget(row_dark)

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

        # --- Speech Engine section ---

        self._engine_combo = QComboBox()
        self._engine_combo.setObjectName("settingCombo")
        self._engine_combo.addItems(["Local (VibeVoice)", "Grok Voice"])
        self._engine_combo.currentIndexChanged.connect(self._on_engine_toggled)
        row_engine = SettingRow(
            "Speech Engine",
            "Switch between local VibeVoice models and Grok Voice API for both ASR and TTS.",
        )
        row_engine.add_control(self._engine_combo)
        layout.addWidget(row_engine)

        # Grok API Key (only visible when engine = grok)
        self._grok_key_input = QLineEdit()
        self._grok_key_input.setObjectName("apiKeyInput")
        self._grok_key_input.setPlaceholderText("xai-...")
        self._grok_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._grok_key_input.setMinimumWidth(240)
        self._grok_key_input.editingFinished.connect(
            lambda: self.grok_api_key_changed.emit(self._grok_key_input.text().strip())
        )
        self._row_grok_key = SettingRow(
            "Grok API Key",
            "xAI API key. Get one at console.x.ai.",
        )
        self._row_grok_key.add_control(self._grok_key_input)
        layout.addWidget(self._row_grok_key)

        # Voice selection (shared row — contents swap based on engine)
        self._voice_combo = QComboBox()
        self._voice_combo.setObjectName("settingCombo")
        self._voice_combo.setMinimumWidth(200)
        self._voice_combo.currentTextChanged.connect(self._on_voice_picked)
        self._row_voice = SettingRow("Voice", "Select the voice for text-to-speech.")
        self._row_voice.add_control(self._voice_combo)
        layout.addWidget(self._row_voice)

        # ASR source (only visible when engine = local)
        self._asr_combo = QComboBox()
        self._asr_combo.setObjectName("settingCombo")
        self._asr_combo.addItems(["local", "cloud"])
        self._asr_combo.currentTextChanged.connect(self.asr_mode_changed.emit)
        self._row_asr = SettingRow(
            "ASR Source",
            "Local (faster-whisper) or cloud (Vibing API) for speech recognition.",
        )
        self._row_asr.add_control(self._asr_combo)
        layout.addWidget(self._row_asr)

        # Inference steps (local only)
        steps_widget = QWidget()
        steps_layout = QHBoxLayout(steps_widget)
        steps_layout.setContentsMargins(0, 0, 0, 0)
        self._steps_slider = QSlider(Qt.Orientation.Horizontal)
        self._steps_slider.setRange(3, 20)
        self._steps_slider.setValue(10)
        self._steps_slider.setFixedWidth(160)
        self._steps_label = QLabel("10")
        self._steps_label.setObjectName("sliderValue")
        self._steps_slider.valueChanged.connect(self._on_steps_changed)
        steps_layout.addWidget(self._steps_slider)
        steps_layout.addWidget(self._steps_label)
        self._row_steps = SettingRow("Inference Steps", "Higher = better quality but slower TTS generation.")
        self._row_steps.add_control(steps_widget)
        layout.addWidget(self._row_steps)

        # CFG scale (local only)
        cfg_widget = QWidget()
        cfg_layout = QHBoxLayout(cfg_widget)
        cfg_layout.setContentsMargins(0, 0, 0, 0)
        self._cfg_slider = QSlider(Qt.Orientation.Horizontal)
        self._cfg_slider.setRange(10, 30)
        self._cfg_slider.setValue(15)
        self._cfg_slider.setFixedWidth(160)
        self._cfg_label = QLabel("1.5")
        self._cfg_label.setObjectName("sliderValue")
        self._cfg_slider.valueChanged.connect(self._on_cfg_changed)
        cfg_layout.addWidget(self._cfg_slider)
        cfg_layout.addWidget(self._cfg_label)
        self._row_cfg = SettingRow(
            "Voice Guidance (CFG)",
            "Higher values follow the voice prompt more closely; too high can sound robotic. Default 1.5.",
        )
        self._row_cfg.add_control(cfg_widget)
        layout.addWidget(self._row_cfg)

        layout.addStretch()

    # --- Engine toggle logic ---

    def _engine_key(self) -> str:
        return "grok" if self._engine_combo.currentIndex() == 1 else "local"

    def _on_engine_toggled(self, _index: int):
        engine = self._engine_key()
        is_grok = engine == "grok"

        # Show/hide context-dependent rows
        self._row_grok_key.setVisible(is_grok)
        self._row_asr.setVisible(not is_grok)
        self._row_steps.setVisible(not is_grok)
        self._row_cfg.setVisible(not is_grok)

        # Swap voice list
        self._voice_combo.blockSignals(True)
        self._voice_combo.clear()
        if is_grok:
            self._voice_combo.addItems(GROK_VOICES)
            if self._grok_voice in GROK_VOICES:
                self._voice_combo.setCurrentText(self._grok_voice)
        else:
            if self._local_voices:
                self._voice_combo.addItems(self._local_voices)
                if self._local_voice in self._local_voices:
                    self._voice_combo.setCurrentText(self._local_voice)
        self._voice_combo.blockSignals(False)

        self.engine_changed.emit(engine)

    def _on_voice_picked(self, voice: str):
        if not voice:
            return
        if self._engine_key() == "grok":
            self._grok_voice = voice
            self.grok_voice_changed.emit(voice)
        else:
            self._local_voice = voice
            self.voice_changed.emit(voice)

    def _on_steps_changed(self, value: int):
        self._steps_label.setText(str(value))
        self.steps_changed.emit(value)

    def _on_cfg_changed(self, value: int):
        cfg = value / 10.0
        self._cfg_label.setText(f"{cfg:.1f}")
        self.cfg_changed.emit(cfg)

    # --- Public API ---

    def set_voices(self, voices: list[str], current: str):
        self._local_voices = voices
        self._local_voice = current
        if self._engine_key() == "local":
            self._voice_combo.blockSignals(True)
            self._voice_combo.clear()
            self._voice_combo.addItems(voices)
            if current in voices:
                self._voice_combo.setCurrentText(current)
            self._voice_combo.blockSignals(False)

    def set_values(self, dark_mode: bool, asr_mode: str, steps: int,
                   cfg: float = 1.5,
                   enhanced_intent: bool = True, ai_polish: bool = True,
                   api_key: str = "", grok_api_key: str = "",
                   engine: str = "local", grok_voice: str = "eve"):
        self._dark_toggle.setChecked(dark_mode)
        self._intent_toggle.setChecked(enhanced_intent)
        self._polish_toggle.setChecked(ai_polish)
        if api_key:
            self._api_key_input.setText(api_key)
        if grok_api_key:
            self._grok_key_input.setText(grok_api_key)

        # Store voice state before triggering engine toggle
        self._grok_voice = grok_voice

        # Engine combo (triggers _on_engine_toggled which sets row visibility)
        self._engine_combo.blockSignals(True)
        self._engine_combo.setCurrentIndex(1 if engine == "grok" else 0)
        self._engine_combo.blockSignals(False)

        # Apply visibility manually since we blocked the signal
        is_grok = engine == "grok"
        self._row_grok_key.setVisible(is_grok)
        self._row_asr.setVisible(not is_grok)
        self._row_steps.setVisible(not is_grok)
        self._row_cfg.setVisible(not is_grok)

        # Populate voice combo for current engine
        self._voice_combo.blockSignals(True)
        self._voice_combo.clear()
        if is_grok:
            self._voice_combo.addItems(GROK_VOICES)
            if grok_voice in GROK_VOICES:
                self._voice_combo.setCurrentText(grok_voice)
        # Local voices populated later via set_voices() once model loads
        self._voice_combo.blockSignals(False)

        self._asr_combo.blockSignals(True)
        self._asr_combo.setCurrentText(asr_mode)
        self._asr_combo.blockSignals(False)
        self._steps_slider.blockSignals(True)
        self._steps_slider.setValue(steps)
        self._steps_label.setText(str(steps))
        self._steps_slider.blockSignals(False)
        self._cfg_slider.blockSignals(True)
        cfg_int = max(10, min(30, round(cfg * 10)))
        self._cfg_slider.setValue(cfg_int)
        self._cfg_label.setText(f"{cfg_int / 10.0:.1f}")
        self._cfg_slider.blockSignals(False)
