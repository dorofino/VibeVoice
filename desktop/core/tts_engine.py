import sys
import threading
from pathlib import Path
from typing import Iterator, Optional

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from desktop.config import REPO_ROOT, TTS_MODEL_PATH, TTS_DEFAULT_VOICE, TTS_DEFAULT_CFG, TTS_DEFAULT_STEPS

# Add repo root so we can import demo.web.app
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class TTSEngine(QObject):
    """Wraps StreamingTTSService for desktop use."""

    model_loaded = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, device: str = "cuda"):
        super().__init__()
        self._service = None
        self._device = device
        self._stop_event = threading.Event()

    def load(self):
        """Load TTS model. Call from a background thread."""
        try:
            from demo.web.app import StreamingTTSService
            self._service = StreamingTTSService(
                model_path=TTS_MODEL_PATH,
                device=self._device,
                inference_steps=TTS_DEFAULT_STEPS,
            )
            self._service.load()
            self.model_loaded.emit()
        except Exception as e:
            self.error.emit(f"TTS load failed: {e}")

    @property
    def is_loaded(self) -> bool:
        return self._service is not None and self._service.model is not None

    def list_voices(self) -> list[str]:
        if not self._service:
            return []
        return sorted(self._service.voice_presets.keys())

    def stream(
        self,
        text: str,
        voice_key: Optional[str] = None,
        cfg_scale: float = TTS_DEFAULT_CFG,
        inference_steps: int = TTS_DEFAULT_STEPS,
    ) -> Iterator[np.ndarray]:
        """Yield audio chunks (float32 numpy arrays at 24kHz)."""
        if not self.is_loaded:
            return

        self._stop_event.clear()
        yield from self._service.stream(
            text=text,
            cfg_scale=cfg_scale,
            inference_steps=inference_steps,
            voice_key=voice_key or TTS_DEFAULT_VOICE,
            stop_event=self._stop_event,
        )

    def stop(self):
        self._stop_event.set()
