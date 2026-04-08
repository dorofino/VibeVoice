from typing import Callable, Optional

import keyboard
from PyQt6.QtCore import QObject, pyqtSignal


class HotkeyManager(QObject):
    """Manages global hotkeys for ASR (push-to-talk) and TTS (read aloud)."""

    asr_pressed = pyqtSignal()
    asr_released = pyqtSignal()
    tts_triggered = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._registered: dict[str, list] = {}
        self._asr_hotkey: Optional[str] = None
        self._tts_hotkey: Optional[str] = None
        self._asr_parts: list[str] = []
        self._asr_combo_active = False

    def register_asr(self, hotkey: str):
        """Register push-to-talk hotkey (press to start, release to stop)."""
        self.unregister("asr")
        self._asr_hotkey = hotkey
        self._asr_parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
        self._asr_combo_active = False

        # Track full combo state on every keyboard event so release is reliable
        # even when Win key events are inconsistent.
        hook = keyboard.hook(self._on_asr_event, suppress=False)
        self._registered["asr"] = [hook]

    def _part_pressed(self, part: str) -> bool:
        aliases = {
            "win": ["windows", "left windows", "right windows", "win"],
            "ctrl": ["ctrl", "left ctrl", "right ctrl"],
            "shift": ["shift", "left shift", "right shift"],
            "alt": ["alt", "left alt", "right alt"],
        }
        keys = aliases.get(part, [part])
        for key in keys:
            try:
                if keyboard.is_pressed(key):
                    return True
            except Exception:
                continue
        return False

    def _on_asr_event(self, event):
        if not self._asr_parts:
            return

        combo_pressed = all(self._part_pressed(part) for part in self._asr_parts)
        if combo_pressed and not self._asr_combo_active:
            self._asr_combo_active = True
            self.asr_pressed.emit()
        elif not combo_pressed and self._asr_combo_active:
            self._asr_combo_active = False
            self.asr_released.emit()

    def register_tts(self, hotkey: str):
        """Register TTS read-aloud hotkey."""
        self.unregister("tts")
        self._tts_hotkey = hotkey

        hook = keyboard.add_hotkey(hotkey, self._on_tts, suppress=False)
        self._registered["tts"] = [hook]

    def _on_tts(self):
        self.tts_triggered.emit()

    def unregister(self, name: str):
        """Unregister a hotkey by name."""
        hooks = self._registered.pop(name, [])
        for hook in hooks:
            try:
                keyboard.unhook(hook)
            except (ValueError, KeyError):
                pass
        if name == "asr":
            self._asr_combo_active = False

    def unregister_all(self):
        for name in list(self._registered.keys()):
            self.unregister(name)
