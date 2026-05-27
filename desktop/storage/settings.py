import json
from typing import Any

from desktop.config import (
    SETTINGS_FILE, DEFAULT_HOTKEY_ASR, DEFAULT_HOTKEY_TTS,
    TTS_DEFAULT_VOICE, TTS_DEFAULT_CFG, TTS_DEFAULT_STEPS,
    ASR_MODEL_SIZE, GROK_DEFAULT_VOICE, FOUNDRY_DEFAULT_VOICE,
)

DEFAULTS = {
    "dark_mode": True,
    "tts_voice": TTS_DEFAULT_VOICE,
    "tts_cfg": TTS_DEFAULT_CFG,
    "tts_steps": TTS_DEFAULT_STEPS,
    "engine": "local",  # "local", "grok", or "foundry" (controls both ASR and TTS)
    "asr_model_size": ASR_MODEL_SIZE,
    "asr_mode": "local",  # "local" or "cloud" (only used when engine="local")
    "hotkey_asr": DEFAULT_HOTKEY_ASR,
    "hotkey_tts": DEFAULT_HOTKEY_TTS,
    "enhanced_intent": True,
    "ai_polish": True,
    "api_key": "",
    "grok_api_key": "",
    "grok_voice": GROK_DEFAULT_VOICE,
    "foundry_endpoint": "",
    "foundry_api_key": "",
    "foundry_voice": FOUNDRY_DEFAULT_VOICE,
}


class Settings:
    def __init__(self):
        self._data: dict[str, Any] = dict(DEFAULTS)
        self.load()

    def load(self):
        try:
            if SETTINGS_FILE.exists():
                with open(SETTINGS_FILE) as f:
                    saved = json.load(f)
                self._data.update(saved)
        except Exception:
            pass

    def save(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str) -> Any:
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    @property
    def all(self) -> dict[str, Any]:
        return dict(self._data)
