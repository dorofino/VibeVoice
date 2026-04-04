import threading

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

from desktop.config import ASR_SAMPLE_RATE, MAX_RECORDING_SEC


class AudioRecorder(QObject):
    """Records audio from microphone."""

    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._stream = None
        self._chunks: list[np.ndarray] = []
        self._recording = False
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self):
        """Start recording from the default microphone."""
        if self._recording:
            return

        self._chunks = []
        self._recording = True

        self._stream = sd.InputStream(
            samplerate=ASR_SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=self._audio_callback,
        )
        self._stream.start()
        self.recording_started.emit()

    def _audio_callback(self, indata, frames, time_info, status):
        if not self._recording:
            return
        with self._lock:
            self._chunks.append(indata[:, 0].copy())
            # Enforce max recording duration
            total_samples = sum(len(c) for c in self._chunks)
            if total_samples >= ASR_SAMPLE_RATE * MAX_RECORDING_SEC:
                self._recording = False

    def stop(self) -> np.ndarray:
        """Stop recording and return the audio as a float32 numpy array."""
        self._recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        with self._lock:
            if self._chunks:
                audio = np.concatenate(self._chunks)
            else:
                audio = np.array([], dtype=np.float32)
            self._chunks = []

        self.recording_stopped.emit()
        return audio
