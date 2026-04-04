import json
import asyncio
import threading
from typing import Optional

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal

from desktop.config import (
    ASR_MODEL_SIZE, ASR_DEVICE, ASR_COMPUTE_TYPE,
    ASR_SAMPLE_RATE, VIBING_CONFIG_PATH,
)


class ASREngine(QObject):
    """Speech-to-text via faster-whisper (local) or Vibing cloud API."""

    model_loaded = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._local_model = None
        self._cloud_url: Optional[str] = None
        self._load_cloud_config()

    def _load_cloud_config(self):
        """Read Vibing's cloud API URL if available."""
        try:
            if VIBING_CONFIG_PATH.exists():
                import yaml
                with open(VIBING_CONFIG_PATH) as f:
                    config = yaml.safe_load(f)
                self._cloud_url = config.get("pipeline_api", {}).get("url")
        except Exception:
            # yaml might not be installed, or config might be malformed
            try:
                text = VIBING_CONFIG_PATH.read_text()
                for line in text.splitlines():
                    if "url:" in line and "wss://" in line:
                        self._cloud_url = line.split("url:")[-1].strip().strip('"')
                        break
            except Exception:
                pass

    def load(self, model_size: Optional[str] = None):
        """Load faster-whisper model. Call from a background thread."""
        try:
            from faster_whisper import WhisperModel
            size = model_size or ASR_MODEL_SIZE
            self._local_model = WhisperModel(
                size, device=ASR_DEVICE, compute_type=ASR_COMPUTE_TYPE
            )
            self.model_loaded.emit()
        except Exception as e:
            self.error.emit(f"ASR load failed: {e}")

    @property
    def is_loaded(self) -> bool:
        return self._local_model is not None

    @property
    def has_cloud(self) -> bool:
        return self._cloud_url is not None

    def transcribe(
        self,
        audio: np.ndarray,
        hotwords: Optional[list[str]] = None,
        mode: str = "local",
    ) -> str:
        """Transcribe audio to text.

        Args:
            audio: float32 numpy array at 16kHz
            hotwords: list of custom words to bias recognition
            mode: "local" for faster-whisper, "cloud" for Vibing API
        """
        if mode == "cloud" and self._cloud_url:
            return self._transcribe_cloud(audio, hotwords)
        return self._transcribe_local(audio, hotwords)

    def _transcribe_local(self, audio: np.ndarray, hotwords: Optional[list[str]] = None) -> str:
        if not self._local_model:
            return ""

        initial_prompt = None
        if hotwords:
            initial_prompt = "Terminology: " + ", ".join(hotwords)

        segments, _ = self._local_model.transcribe(
            audio,
            language="en",
            initial_prompt=initial_prompt,
            vad_filter=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()

    def _transcribe_cloud(self, audio: np.ndarray, hotwords: Optional[list[str]] = None) -> str:
        """Send audio to Vibing cloud API via WebSocket."""
        try:
            import websockets.sync.client as ws_client

            # Convert to PCM16 bytes
            pcm16 = (audio * 32767).astype(np.int16).tobytes()

            # Build message
            with ws_client.connect(self._cloud_url, close_timeout=10) as ws:
                # Send audio data
                ws.send(pcm16)
                # Receive transcription
                response = ws.recv()
                if isinstance(response, str):
                    data = json.loads(response)
                    # Extract text from response (format may vary)
                    if isinstance(data, dict):
                        return data.get("text", data.get("transcription", str(data)))
                    return str(data)
                return ""
        except Exception as e:
            # Fall back to local on cloud failure
            self.error.emit(f"Cloud ASR failed, falling back to local: {e}")
            return self._transcribe_local(audio, hotwords)
