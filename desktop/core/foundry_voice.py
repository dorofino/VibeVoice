"""Microsoft Foundry / Azure Speech TTS client.

REST endpoint: POST {endpoint}/cognitiveservices/v1
Auth: Ocp-Apim-Subscription-Key header.
Output: raw 24kHz 16-bit mono PCM, streamed and yielded as float32 chunks.
"""

import threading
from typing import Iterator, Optional
from xml.sax.saxutils import escape

import numpy as np

FOUNDRY_SAMPLE_RATE = 24_000

# Common neural voices. Full list at the Azure Speech voice gallery.
FOUNDRY_VOICES = [
    "en-US-AvaNeural",
    "en-US-AndrewNeural",
    "en-US-EmmaNeural",
    "en-US-BrianNeural",
    "en-US-JennyNeural",
    "en-US-GuyNeural",
]


def _build_ssml(text: str, voice: str) -> str:
    lang = "-".join(voice.split("-")[:2]) if "-" in voice else "en-US"
    return (
        f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{lang}">'
        f'<voice name="{voice}">{escape(text)}</voice>'
        f'</speak>'
    )


def stream_tts(
    text: str,
    endpoint: str,
    api_key: str,
    voice: str = "en-US-AvaNeural",
    stop_event: Optional[threading.Event] = None,
) -> Iterator[np.ndarray]:
    """Synthesize via Azure Speech REST TTS, yielding float32 PCM chunks at 24kHz."""
    import requests

    url = f"{endpoint.rstrip('/')}/cognitiveservices/v1"
    ssml = _build_ssml(text, voice)
    print(f"[foundry] stream_tts: voice={voice} text={text[:60]!r}")

    resp = requests.post(
        url,
        headers={
            "Ocp-Apim-Subscription-Key": api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "raw-24khz-16bit-mono-pcm",
            "User-Agent": "VibeVoiceDesktop",
        },
        data=ssml.encode("utf-8"),
        timeout=60,
        stream=True,
    )

    if resp.status_code != 200:
        body = resp.text[:200]
        print(f"[foundry] TTS error {resp.status_code}: {body}")
        raise RuntimeError(f"Foundry TTS HTTP {resp.status_code}: {body}")

    total_samples = 0
    pcm_chunk_bytes = 9600  # 200ms at 24kHz
    leftover = b""
    for raw in resp.iter_content(chunk_size=pcm_chunk_bytes):
        if stop_event and stop_event.is_set():
            break
        raw = leftover + raw
        usable = len(raw) - (len(raw) % 2)
        if usable > 0:
            chunk = np.frombuffer(raw[:usable], dtype=np.int16).astype(np.float32) / 32767.0
            total_samples += len(chunk)
            yield chunk
        leftover = raw[usable:]

    if leftover and len(leftover) >= 2:
        usable = len(leftover) - (len(leftover) % 2)
        chunk = np.frombuffer(leftover[:usable], dtype=np.int16).astype(np.float32) / 32767.0
        total_samples += len(chunk)
        yield chunk

    print(f"[foundry] Done, yielded {total_samples} samples")
