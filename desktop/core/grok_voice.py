"""Grok Voice API client for ASR and TTS.

TTS uses the REST endpoint POST https://api.x.ai/v1/tts
ASR uses the Realtime WebSocket API.
"""

import base64
import io
import json
import threading
from typing import Iterator, Optional

import numpy as np

GROK_TTS_URL = "https://api.x.ai/v1/tts"
GROK_REALTIME_URL = "wss://api.x.ai/v1/realtime"
GROK_REALTIME_MODEL = "grok-voice-think-fast-1.0"
GROK_SAMPLE_RATE = 24_000
RECV_TIMEOUT = 30

# Available Grok voices
GROK_VOICES = ["eve", "ara", "rex", "sal", "leo"]


# --- TTS via REST API ---

def stream_tts(
    text: str,
    api_key: str,
    voice: str = "eve",
    stop_event: Optional[threading.Event] = None,
) -> Iterator[np.ndarray]:
    """Synthesize speech via the Grok REST TTS endpoint.

    Requests raw PCM at 24kHz, yields float32 numpy arrays.
    """
    import requests

    print(f"[grok] stream_tts: voice={voice} text={text[:60]!r}")

    resp = requests.post(
        GROK_TTS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "text": text,
            "voice_id": voice,
            "language": "en",
            "output_format": {
                "codec": "pcm",
                "sample_rate": GROK_SAMPLE_RATE,
            },
        },
        timeout=60,
        stream=True,
    )

    if resp.status_code != 200:
        body = resp.text[:200]
        print(f"[grok] TTS error {resp.status_code}: {body}")
        raise RuntimeError(f"Grok TTS HTTP {resp.status_code}: {body}")

    # Stream PCM16 bytes as they arrive — yield float32 chunks
    # so the audio player can start playback before the full
    # response is downloaded.
    total_samples = 0
    pcm_chunk_bytes = 9600  # 4800 samples * 2 bytes = 200ms at 24kHz
    leftover = b""
    for raw in resp.iter_content(chunk_size=pcm_chunk_bytes):
        if stop_event and stop_event.is_set():
            break
        raw = leftover + raw
        # Ensure we have an even number of bytes (PCM16 = 2 bytes/sample)
        usable = len(raw) - (len(raw) % 2)
        if usable > 0:
            chunk = np.frombuffer(raw[:usable], dtype=np.int16).astype(np.float32) / 32767.0
            total_samples += len(chunk)
            yield chunk
        leftover = raw[usable:]

    # Flush any remaining bytes
    if leftover and len(leftover) >= 2:
        usable = len(leftover) - (len(leftover) % 2)
        chunk = np.frombuffer(leftover[:usable], dtype=np.int16).astype(np.float32) / 32767.0
        total_samples += len(chunk)
        yield chunk

    print(f"[grok] Done, yielded {total_samples} samples")


# --- ASR via Realtime API ---

def _connect_realtime(api_key: str, model: str = GROK_REALTIME_MODEL):
    """Open a WebSocket to the Grok Realtime API for ASR."""
    import websockets.sync.client as ws_client

    url = f"{GROK_REALTIME_URL}?model={model}"
    ws = ws_client.connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key}"},
        close_timeout=10,
    )

    # Drain initial handshake events
    while True:
        msg = ws.recv(timeout=RECV_TIMEOUT)
        event = json.loads(msg)
        etype = event.get("type", "")
        if etype in ("session.created", "conversation.created"):
            break
        if etype == "error":
            ws.close()
            raise RuntimeError(event.get("error", {}).get("message", str(event)))
        # Skip ping and other init events
    return ws


def _recv_realtime(ws):
    """Receive the next JSON event from realtime, skipping pings."""
    while True:
        msg = ws.recv(timeout=RECV_TIMEOUT)
        event = json.loads(msg)
        if event.get("type") != "ping":
            return event


def transcribe(
    audio: np.ndarray,
    api_key: str,
    sample_rate: int = 16_000,
) -> str:
    """Send audio to Grok Realtime API and get text back.

    Grok Realtime is conversational — calling response.create would also
    make the model reply (e.g. appending "What's up?" after the transcript).
    Instead we enable input_audio_transcription and only consume the
    input-transcription events, never triggering a response.
    """
    ws = _connect_realtime(api_key)
    try:
        # Configure session: enable input transcription, disable VAD/turn-taking.
        ws.send(json.dumps({
            "type": "session.update",
            "session": {
                "turn_detection": None,
                "audio": {
                    "input": {
                        "format": {"type": "audio/pcm", "rate": sample_rate},
                        "transcription": {"model": "whisper-1"},
                    },
                },
            },
        }))
        while True:
            event = _recv_realtime(ws)
            if event.get("type") == "session.updated":
                break
            if event.get("type") == "error":
                raise RuntimeError(event.get("error", {}).get("message", str(event)))

        # Send audio
        pcm16 = (audio * 32767).astype(np.int16).tobytes()
        chunk_size = 32_000
        for i in range(0, len(pcm16), chunk_size):
            chunk = pcm16[i:i + chunk_size]
            ws.send(json.dumps({
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(chunk).decode(),
            }))

        ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

        # Wait only for the input-transcription events. Ignore any
        # response.* events the server may still emit.
        text_parts = []
        seen_types: list[str] = []
        while True:
            event = _recv_realtime(ws)
            etype = event.get("type", "")
            seen_types.append(etype)
            if "input_audio_transcription" not in etype:
                # Skip response.text.delta and any other conversational reply
                if etype == "error":
                    raise RuntimeError(event.get("error", {}).get("message", str(event)))
                continue
            if etype.endswith(".delta"):
                text_parts.append(event.get("delta", "") or event.get("transcript", ""))
            elif etype.endswith(".completed"):
                full = event.get("transcript") or event.get("text") or ""
                if full and not text_parts:
                    text_parts.append(full)
                break
            elif etype.endswith(".failed"):
                raise RuntimeError(event.get("error", {}).get("message", str(event)))

        result = "".join(text_parts).strip()
        if not result:
            print(f"[grok-asr] empty result; events seen: {seen_types}")
        return result
    finally:
        ws.close()
