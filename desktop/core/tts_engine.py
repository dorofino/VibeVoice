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
    """Wraps StreamingTTSService (local), Grok Voice, or Microsoft Foundry (Azure Speech) TTS."""

    model_loaded = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, device: str = "cuda"):
        super().__init__()
        self._service = None
        self._device = device
        self._stop_event = threading.Event()

    def load(self):
        """Load local TTS model. Call from a background thread."""
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
        mode: str = "local",
        grok_api_key: str = "",
        grok_voice: str = "eve",
        foundry_endpoint: str = "",
        foundry_api_key: str = "",
        foundry_voice: str = "en-US-AvaNeural",
    ) -> Iterator[np.ndarray]:
        """Yield audio chunks (float32 numpy arrays at 24kHz).

        Args:
            mode: "local" for VibeVoice model, "grok" for Grok Voice API,
                "foundry" for Microsoft Foundry / Azure Speech REST TTS
            grok_api_key: xAI API key (required when mode="grok")
            grok_voice: Grok voice name (eve, ara, rex, sal, leo)
            foundry_endpoint: Azure Speech endpoint URL (required when mode="foundry")
            foundry_api_key: Azure Speech subscription key (required when mode="foundry")
            foundry_voice: Azure Speech neural voice name
        """
        self._stop_event.clear()

        if mode == "grok":
            if not grok_api_key:
                self.error.emit("Grok API key not set.")
                return
            yield from self._stream_grok(text, grok_api_key, grok_voice)
        elif mode == "foundry":
            if not foundry_endpoint or not foundry_api_key:
                self.error.emit("Foundry endpoint and API key not set.")
                return
            yield from self._stream_foundry(text, foundry_endpoint, foundry_api_key, foundry_voice)
        else:
            if not self.is_loaded:
                return
            yield from self._service.stream(
                text=text,
                cfg_scale=cfg_scale,
                inference_steps=inference_steps,
                voice_key=voice_key or TTS_DEFAULT_VOICE,
                stop_event=self._stop_event,
            )

    def _stream_grok(self, text: str, api_key: str, voice: str) -> Iterator[np.ndarray]:
        """Stream TTS via Grok Voice Realtime API.

        Yields chunks directly from the Grok WebSocket. Exceptions are
        emitted on the error signal *and* re-raised so the audio player
        knows the stream failed (instead of seeing an empty generator).
        """
        try:
            from desktop.core.grok_voice import stream_tts
            yield from stream_tts(
                text=text,
                api_key=api_key,
                voice=voice,
                stop_event=self._stop_event,
            )
        except GeneratorExit:
            pass
        except Exception as e:
            self.error.emit(f"Grok TTS failed: {e}")
            raise

    def stop(self):
        self._stop_event.set()
