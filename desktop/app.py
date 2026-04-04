import sys
import time
import threading
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QTimer, QObject, QMetaObject, Q_ARG, pyqtSlot

from desktop.config import APP_NAME, DATA_DIR, DEFAULT_HOTKEY_ASR, DEFAULT_HOTKEY_TTS
from desktop.core.tts_engine import TTSEngine
from desktop.core.asr_engine import ASREngine
from desktop.core.audio_player import AudioPlayer
from desktop.core.audio_recorder import AudioRecorder
from desktop.core.hotkey_manager import HotkeyManager
from desktop.core import clipboard
from desktop.ui.system_tray import SystemTray
from desktop.ui.main_window import MainWindow
from desktop.ui.floating_capsule import FloatingCapsule
from desktop.ui.pages.home_page import HomePage
from desktop.ui.pages.history_page import HistoryPage
from desktop.ui.pages.hotwords_page import HotwordsPage
from desktop.ui.pages.settings_page import SettingsPage
from desktop.storage.settings import Settings
from desktop.storage.history_db import HistoryDB
from desktop.storage.hotwords import Hotwords
from desktop.core.text_processor import TextProcessor

RESOURCES = Path(__file__).parent / "resources"


class VoiceDesktopApp(QObject):
    """Main application controller."""

    def __init__(self, argv: list[str]):
        self.qt_app = QApplication(argv)
        super().__init__()
        self.qt_app.setApplicationName(APP_NAME)
        self.qt_app.setQuitOnLastWindowClosed(False)

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # Storage
        self.settings = Settings()
        self.history_db = HistoryDB()
        self.hotwords = Hotwords()

        # Core engines
        self.tts_engine = TTSEngine()
        self.asr_engine = ASREngine()
        self.audio_player = AudioPlayer()
        self.audio_recorder = AudioRecorder()
        self.hotkey_manager = HotkeyManager()
        self.text_processor = TextProcessor()

        # UI
        self.tray = SystemTray()
        self.capsule = FloatingCapsule()
        self._build_main_window()
        self._apply_theme()

        # State
        self._asr_active = False
        self._tts_active = False
        self._models_ready = False
        self._recording_start_time = 0.0

        self._connect_signals()

    def _build_main_window(self):
        self.main_window = MainWindow()

        # Pages
        self.home_page = HomePage()
        self.history_page = HistoryPage()
        self.hotwords_page = HotwordsPage()
        self.settings_page = SettingsPage()

        self.main_window.add_page("Home", self.home_page)
        self.main_window.add_page("History", self.history_page)
        self.main_window.add_page("Hotwords", self.hotwords_page)
        self.main_window.add_page("Settings", self.settings_page)

        # Populate pages
        self._refresh_home()
        self._refresh_history()
        self._refresh_hotwords()
        self._apply_settings_to_ui()

    def _apply_theme(self):
        dark = self.settings.get("dark_mode")
        theme_file = RESOURCES / "styles" / ("dark.qss" if dark else "light.qss")
        if theme_file.exists():
            self.qt_app.setStyleSheet(theme_file.read_text())

    def _apply_settings_to_ui(self):
        self.settings_page.set_values(
            dark_mode=self.settings.get("dark_mode"),
            asr_mode=self.settings.get("asr_mode"),
            steps=self.settings.get("tts_steps"),
            enhanced_intent=self.settings.get("enhanced_intent"),
            ai_polish=self.settings.get("ai_polish"),
            api_key=self.settings.get("api_key"),
        )
        # Apply saved API key to text processor
        saved_key = self.settings.get("api_key")
        if saved_key:
            self.text_processor.set_api_key(saved_key)
        self.home_page.set_hotkeys(
            self.settings.get("hotkey_asr"),
            self.settings.get("hotkey_tts"),
        )

    def _connect_signals(self):
        # Tray
        self.tray.quit_requested.connect(self.quit)
        self.tray.show_window_requested.connect(self._toggle_window)

        # Hotkeys
        self.hotkey_manager.asr_pressed.connect(self._on_asr_start)
        self.hotkey_manager.asr_released.connect(self._on_asr_stop)
        self.hotkey_manager.tts_triggered.connect(self._on_tts_read)

        # Engine signals
        self.tts_engine.model_loaded.connect(self._on_tts_ready)
        self.asr_engine.model_loaded.connect(self._on_asr_ready)
        self.tts_engine.error.connect(self._on_error)
        self.asr_engine.error.connect(self._on_error)
        self.text_processor.error.connect(self._on_error)

        # Settings page
        self.settings_page.dark_mode_changed.connect(self._on_dark_mode_changed)
        self.settings_page.enhanced_intent_changed.connect(self._on_enhanced_intent_changed)
        self.settings_page.ai_polish_changed.connect(self._on_ai_polish_changed)
        self.settings_page.api_key_changed.connect(self._on_api_key_changed)
        self.settings_page.voice_changed.connect(self._on_voice_changed)
        self.settings_page.asr_mode_changed.connect(self._on_asr_mode_changed)
        self.settings_page.steps_changed.connect(self._on_steps_changed)

        # Hotwords page
        self.hotwords_page.word_added.connect(self._on_hotword_added)
        self.hotwords_page.word_removed.connect(self._on_hotword_removed)

        # History page
        self.history_page.clear_button.clicked.connect(self._on_history_clear)

    def run(self) -> int:
        self.tray.show()
        self.tray.set_status("Loading models...")
        self.tray.showMessage(APP_NAME, "Loading models, please wait...", self.tray.icon())

        self._load_thread = threading.Thread(target=self._load_models, daemon=True)
        self._load_thread.start()

        return self.qt_app.exec()

    def _load_models(self):
        self.tts_engine.load()
        self.asr_engine.load()

    @pyqtSlot()
    def _on_tts_ready(self):
        self.tray.set_status("TTS ready")
        # Populate voice list in settings
        voices = self.tts_engine.list_voices()
        current_voice = self.settings.get("tts_voice")
        QTimer.singleShot(0, lambda: self.settings_page.set_voices(voices, current_voice))
        self._check_all_ready()

    @pyqtSlot()
    def _on_asr_ready(self):
        self.tray.set_status("ASR ready")
        self._check_all_ready()

    def _check_all_ready(self):
        if self.tts_engine.is_loaded and self.asr_engine.is_loaded:
            self._models_ready = True
            hotkey_asr = self.settings.get("hotkey_asr")
            hotkey_tts = self.settings.get("hotkey_tts")
            self.tray.set_status("Ready")
            self.tray.showMessage(
                APP_NAME,
                f"Ready! Hold {hotkey_asr} to dictate, press {hotkey_tts} to read aloud.",
                self.tray.icon(),
            )
            self.hotkey_manager.register_asr(hotkey_asr)
            self.hotkey_manager.register_tts(hotkey_tts)

    @pyqtSlot(str)
    def _on_error(self, msg: str):
        print(f"[Error] {msg}")
        self.tray.showMessage(APP_NAME, msg, self.tray.icon())

    # --- ASR ---

    @pyqtSlot()
    def _on_asr_start(self):
        if not self._models_ready or self._asr_active:
            return
        self._asr_active = True
        self._recording_start_time = time.time()
        self.tray.set_status("Recording...")
        self.capsule.show_recording()
        self.audio_recorder.start()

    @pyqtSlot()
    def _on_asr_stop(self):
        if not self._asr_active:
            return
        self._asr_active = False
        duration = time.time() - self._recording_start_time
        self.tray.set_status("Transcribing...")
        self.capsule.show_transcribing()
        audio = self.audio_recorder.stop()

        if audio.size < 1600:
            self.capsule.hide_capsule()
            self.tray.set_status("Ready")
            return

        threading.Thread(
            target=self._transcribe_and_insert, args=(audio, duration), daemon=True
        ).start()

    def _invoke_on_main(self, fn):
        """Safely invoke a function on the main thread."""
        QMetaObject.invokeMethod(self, "_run_on_main", Qt.ConnectionType.QueuedConnection,
                                 Q_ARG(object, fn))

    @pyqtSlot(object)
    def _run_on_main(self, fn):
        try:
            fn()
        except Exception as e:
            print(f"[main-thread] Error: {e}")

    def _transcribe_and_insert(self, audio, duration: float):
        try:
            # Stage 1: Transcribe
            print("[pipeline] Transcribing...")
            self._invoke_on_main(self.capsule.show_transcribing)
            asr_mode = self.settings.get("asr_mode")
            hotword_list = self.hotwords.words
            raw_text = self.asr_engine.transcribe(audio, hotwords=hotword_list, mode=asr_mode)
            print(f"[pipeline] Result: {raw_text[:80]!r}")

            if not raw_text.strip():
                print("[pipeline] Empty, hiding")
                self._invoke_on_main(self.capsule.hide_capsule)
                return

            text = raw_text.strip()
            was_processed = False

            # Stage 2: AI
            enhanced_intent = self.settings.get("enhanced_intent")
            ai_polish = self.settings.get("ai_polish")

            if enhanced_intent or ai_polish:
                label = "Enhancing" if enhanced_intent else "Polishing"
                print(f"[pipeline] {label}...")
                if enhanced_intent:
                    self._invoke_on_main(self.capsule.show_enhancing)
                else:
                    self._invoke_on_main(self.capsule.show_polishing)

                text = self.text_processor.polish_text(
                    raw_text.strip(),
                    enhanced_intent=enhanced_intent,
                    polish=ai_polish,
                )
                was_processed = (text != raw_text.strip())
                print(f"[pipeline] AI done: {text[:80]!r}")

            # Stage 3: Insert + hide
            print("[pipeline] Inserting clipboard + hiding capsule")
            clipboard.insert_text(text)

            # Log
            self.history_db.add_entry(
                text=text,
                raw_text=raw_text.strip() if was_processed else None,
                duration_sec=duration,
                source=f"asr-{asr_mode}",
            )

            # Show done briefly then hide
            msg = text[:42] if len(text) <= 42 else text[:40] + "..."
            self._invoke_on_main(lambda: self.capsule.show_done(msg))
            self._invoke_on_main(self._refresh_home)
            self._invoke_on_main(self._refresh_history)

        except Exception as e:
            print(f"[pipeline] ERROR: {e}")
            import traceback
            traceback.print_exc()
            self._invoke_on_main(self.capsule.hide_capsule)
        finally:
            print("[pipeline] Done")
            self._invoke_on_main(lambda: self.tray.set_status("Ready"))

    def _insert_text(self, text: str):
        clipboard.insert_text(text)

    # --- TTS ---

    @pyqtSlot()
    def _on_tts_read(self):
        if not self._models_ready:
            return

        if self._tts_active:
            self.audio_player.stop()
            self.tts_engine.stop()
            self._tts_active = False
            self.capsule.hide_capsule()
            self.tray.set_status("Ready")
            return

        text = clipboard.grab_selection()
        if not text.strip():
            return

        self._tts_active = True
        self.tray.set_status("Speaking...")
        self.capsule.show_speaking()

        threading.Thread(
            target=self._speak_text, args=(text,), daemon=True
        ).start()

    def _speak_text(self, text: str):
        try:
            voice = self.settings.get("tts_voice")
            steps = self.settings.get("tts_steps")
            chunks = self.tts_engine.stream(text, voice_key=voice, inference_steps=steps)
            self.audio_player.play_stream(chunks)
        except Exception as e:
            QTimer.singleShot(0, lambda: self._on_error(f"TTS failed: {e}"))
        finally:
            self._tts_active = False
            QTimer.singleShot(0, self.capsule.hide_capsule)
            QTimer.singleShot(0, lambda: self.tray.set_status("Ready"))

    # --- UI Refresh ---

    def _refresh_home(self):
        self.home_page.refresh(
            self.history_db.get_today_stats(),
            self.history_db.get_total_stats(),
        )

    def _refresh_history(self):
        self.history_page.refresh(self.history_db.get_recent(50))

    def _refresh_hotwords(self):
        self.hotwords_page.refresh(self.hotwords.words)

    # --- Settings handlers ---

    def _on_dark_mode_changed(self, enabled: bool):
        self.settings.set("dark_mode", enabled)
        self._apply_theme()

    def _on_enhanced_intent_changed(self, enabled: bool):
        self.settings.set("enhanced_intent", enabled)

    def _on_ai_polish_changed(self, enabled: bool):
        self.settings.set("ai_polish", enabled)

    def _on_api_key_changed(self, key: str):
        self.settings.set("api_key", key)
        self.text_processor.set_api_key(key)

    def _on_voice_changed(self, voice: str):
        self.settings.set("tts_voice", voice)

    def _on_asr_mode_changed(self, mode: str):
        self.settings.set("asr_mode", mode)

    def _on_steps_changed(self, steps: int):
        self.settings.set("tts_steps", steps)

    def _on_hotword_added(self, word: str):
        self.hotwords.add(word)
        self._refresh_hotwords()

    def _on_hotword_removed(self, word: str):
        self.hotwords.remove(word)
        self._refresh_hotwords()

    def _on_history_clear(self):
        self.history_db.clear()
        self._refresh_history()
        self._refresh_home()

    # --- Window ---

    def _toggle_window(self):
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            self._refresh_home()
            self._refresh_history()
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()

    def quit(self):
        self.hotkey_manager.unregister_all()
        self.audio_player.stop()
        self.tts_engine.stop()
        self.capsule.hide_capsule()
        self.tray.hide()
        self.history_db.close()
        self.qt_app.quit()
