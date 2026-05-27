import os
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = REPO_ROOT / "demo"
VOICES_DIR = DEMO_DIR / "voices" / "streaming_model"

DATA_DIR = Path(os.environ.get("APPDATA", Path.home())) / "VibeVoiceDesktop"
SETTINGS_FILE = DATA_DIR / "settings.json"
HISTORY_DB_FILE = DATA_DIR / "history.db"
HOTWORDS_FILE = DATA_DIR / "hotwords.json"

# TTS
TTS_MODEL_PATH = "microsoft/VibeVoice-Realtime-0.5B"
TTS_SAMPLE_RATE = 24_000
TTS_DEFAULT_VOICE = "en-Carter_man"
TTS_DEFAULT_CFG = 1.5
TTS_DEFAULT_STEPS = 10

# ASR
ASR_MODEL_SIZE = "base.en"
ASR_SAMPLE_RATE = 16_000
ASR_DEVICE = "cuda"
ASR_COMPUTE_TYPE = "float16"

# Cloud ASR fallback
VIBING_CONFIG_PATH = Path(os.environ.get("LOCALAPPDATA", "")) / "Vibing" / "config.yaml"

# Grok Voice
GROK_DEFAULT_VOICE = "eve"

# Microsoft Foundry / Azure Speech
FOUNDRY_DEFAULT_VOICE = "en-US-AvaNeural"

# Hotkeys
DEFAULT_HOTKEY_ASR = "ctrl+shift+win"
DEFAULT_HOTKEY_TTS = "ctrl+shift+alt"

# Audio
MAX_RECORDING_SEC = 30
AUDIO_BUFFER_SIZE = 4096
TTS_PREBUFFER_SEC = 2.0

# UI
APP_NAME = "VibeVoice Desktop"
APP_VERSION = "0.1.0"
