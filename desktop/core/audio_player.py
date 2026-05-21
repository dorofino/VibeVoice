import threading
from typing import Iterator

import numpy as np
import sounddevice as sd
from PyQt6.QtCore import QObject, pyqtSignal

from desktop.config import TTS_SAMPLE_RATE, TTS_PREBUFFER_SEC


class AudioPlayer(QObject):
    """Streams audio chunks to speakers via sounddevice."""

    playback_started = pyqtSignal()
    playback_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._stream = None
        self._buffer = np.array([], dtype=np.float32)
        self._lock = threading.Lock()
        self._playing = False
        self._stop_event = threading.Event()
        self._thread = None

    @property
    def is_playing(self) -> bool:
        return self._playing

    def play_stream(self, chunk_iterator: Iterator[np.ndarray], prebuffer_sec: float = TTS_PREBUFFER_SEC):
        """Play audio from a chunk iterator in a background thread."""
        self.stop()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._play_worker, args=(chunk_iterator, prebuffer_sec), daemon=True
        )
        self._thread.start()

    def _play_worker(self, chunk_iterator: Iterator[np.ndarray], prebuffer_sec: float = TTS_PREBUFFER_SEC):
        prebuffer_samples = int(TTS_SAMPLE_RATE * prebuffer_sec)
        prebuffer = []
        prebuffer_len = 0

        # Prebuffer phase
        try:
            for chunk in chunk_iterator:
                if self._stop_event.is_set():
                    return
                chunk = self._normalize(chunk)
                prebuffer.append(chunk)
                prebuffer_len += len(chunk)
                if prebuffer_len >= prebuffer_samples:
                    break
        except Exception as e:
            print(f"[audio_player] Prebuffer error: {e}")
            return

        if not prebuffer or self._stop_event.is_set():
            return

        # Concatenate prebuffer
        with self._lock:
            self._buffer = np.concatenate(prebuffer)

        # Start output stream
        self._playing = True
        self.playback_started.emit()

        try:
            self._stream = sd.OutputStream(
                samplerate=TTS_SAMPLE_RATE,
                channels=1,
                dtype="float32",
                blocksize=4096,
                callback=self._audio_callback,
            )
            self._stream.start()

            # Continue feeding chunks
            for chunk in chunk_iterator:
                if self._stop_event.is_set():
                    break
                chunk = self._normalize(chunk)
                with self._lock:
                    self._buffer = np.concatenate([self._buffer, chunk])

            # Wait for buffer to drain
            while not self._stop_event.is_set():
                with self._lock:
                    if len(self._buffer) == 0:
                        break
                sd.sleep(50)

        except Exception as e:
            print(f"[audio_player] Playback error: {e}")
        finally:
            self._cleanup()

    def _audio_callback(self, outdata, frames, time_info, status):
        with self._lock:
            available = len(self._buffer)
            if available >= frames:
                outdata[:, 0] = self._buffer[:frames]
                self._buffer = self._buffer[frames:]
            elif available > 0:
                outdata[:available, 0] = self._buffer
                outdata[available:, 0] = 0.0
                self._buffer = np.array([], dtype=np.float32)
            else:
                outdata[:, 0] = 0.0

    def _normalize(self, chunk: np.ndarray) -> np.ndarray:
        if chunk.ndim > 1:
            chunk = chunk.reshape(-1)
        chunk = chunk.astype(np.float32, copy=False)
        peak = np.max(np.abs(chunk)) if chunk.size else 0.0
        if peak > 1.0:
            chunk = chunk / peak
        return chunk

    def _cleanup(self):
        was_playing = self._playing
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        self._playing = False
        # Only emit if we were actually playing — avoid spurious signals
        # from stop() calls that happen before playback starts.
        if was_playing:
            self.playback_finished.emit()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._cleanup()
        with self._lock:
            self._buffer = np.array([], dtype=np.float32)
