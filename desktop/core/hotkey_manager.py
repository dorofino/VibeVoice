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

    def register_asr(self, hotkey: str):
        """Register push-to-talk hotkey (press to start, release to stop)."""
        self.unregister("asr")
        self._asr_hotkey = hotkey

        # Parse the hotkey parts for press/release detection
        parts = hotkey.split("+")
        trigger_key = parts[-1]  # Last key is the trigger

        hooks = []
        hooks.append(keyboard.on_press_key(trigger_key, self._on_asr_press, suppress=False))
        hooks.append(keyboard.on_release_key(trigger_key, self._on_asr_release, suppress=False))
        self._registered["asr"] = hooks

    def _on_asr_press(self, event):
        if not self._asr_hotkey:
            return
        # Check if modifier keys are held
        parts = self._asr_hotkey.split("+")
        modifiers = parts[:-1]
        if all(keyboard.is_pressed(mod) for mod in modifiers):
            self.asr_pressed.emit()

    def _on_asr_release(self, event):
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

    def unregister_all(self):
        for name in list(self._registered.keys()):
            self.unregister(name)
