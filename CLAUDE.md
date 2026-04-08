# VibeVoice

Microsoft's open-source frontier voice AI framework. Three models built on a continuous speech tokenizer (7.5 Hz frame rate) with a next-token diffusion framework:

- **VibeVoice-ASR** — long-form speech recognition (up to 60 min, diarization, timestamps, hotwords)
- **VibeVoice-TTS** — long-form multi-speaker TTS (up to 90 min, 4 speakers)
- **VibeVoice-Realtime** — 0.5B streaming TTS (~300 ms latency)

## Repository layout

- [vibevoice/](vibevoice/) — main Python package (models, processor, configs, scripts)
- [desktop/](desktop/) — Windows PyQt6 desktop app with local ASR/TTS engines
- [demo/](demo/) — Gradio demos, inference examples, notebooks, web API
- [docs/](docs/) — model docs, architecture notes, technique reports
- [finetuning-asr/](finetuning-asr/) — ASR fine-tuning code and datasets
- [vllm_plugin/](vllm_plugin/) — vLLM inference server integration (registered via `vllm.general_plugins` → `vllm_plugin:register_vibevoice`)

## Tech stack

Python 3.9+. Core deps: `torch`, `transformers==4.51.3`, `accelerate`, `diffusers`, `numba`, `librosa`, `scipy`, `pydub`, `av`, `aiortc`, `fastapi`, `uvicorn`, `gradio`. Desktop adds `PyQt6`, `keyboard`, and direct `ctypes` Win32 calls.

## Run / build

- Install: `pip install -e .` (installs both `vibevoice` and `vllm_plugin`)
- Desktop app: `python -m desktop.main`
- ASR Gradio demo: `python demo/vibevoice_asr_gradio_demo.py`
- Realtime TTS API: `python demo/vibevoice_realtime_demo.py --port 3000 --model_path microsoft/VibeVoice-Realtime-0.5B`
- Fine-tuning: see [finetuning-asr/README.md](finetuning-asr/README.md)

There is no pytest suite — validation happens through the demo / inference scripts.

## Desktop subproject

Windows-only PyQt6 companion app for local push-to-talk dictation and TTS playback.

**Core** ([desktop/core/](desktop/core/)):
- [asr_engine.py](desktop/core/asr_engine.py) — wraps `faster-whisper` (default `base.en`, fp16 on CUDA), optional cloud fallback via Vibing API
- [tts_engine.py](desktop/core/tts_engine.py) — wraps `StreamingTTSService` from `demo.web.app`
- [audio_recorder.py](desktop/core/audio_recorder.py), [audio_player.py](desktop/core/audio_player.py) — audio I/O
- [text_processor.py](desktop/core/text_processor.py) — transcription post-processing
- [clipboard.py](desktop/core/clipboard.py) — Win32 clipboard ops + hotkey edge-case workarounds
- [hotkey_manager.py](desktop/core/hotkey_manager.py) — global hotkeys (ASR press/release push-to-talk, TTS single trigger)

**UI** ([desktop/ui/](desktop/ui/)):
- [main_window.py](desktop/ui/main_window.py), [system_tray.py](desktop/ui/system_tray.py)
- [floating_capsule.py](desktop/ui/floating_capsule.py) — status overlay using **raw Win32 `WS_POPUP` + `UpdateLayeredWindow`** rather than a Qt frameless window, to avoid DWM frame artifacts on Win11 (see memory note `feedback_win32_overlay.md`)
- [pages/](desktop/ui/pages/) — settings, history, hotwords, home

**Storage** ([desktop/storage/](desktop/storage/)) — JSON settings, SQLite history, hotwords config.

**Defaults** ([desktop/config.py](desktop/config.py)) — ASR hotkey `Ctrl+Shift+Win`, TTS hotkey `Ctrl+Shift+Alt`, TTS model `microsoft/VibeVoice-Realtime-0.5B`.

### Desktop gotchas
- Windows-only (Win32 APIs, `keyboard` library constraints).
- Models load on background threads — wait for `model_loaded` signals.
- The `keyboard` library needs careful modifier-release handling; see comments in [clipboard.py](desktop/core/clipboard.py) and [hotkey_manager.py](desktop/core/hotkey_manager.py).
- Do **not** convert the floating capsule to a Qt frameless window — it must stay pure Win32 layered.

## Contribution conventions

From [CONTRIBUTING.md](CONTRIBUTING.md):
- **Minimalism first** — concise, clear, research-grade code. No speculative abstraction or refactoring.
- Maintainers do **line-by-line manual review**; over-engineered or LLM-slop PRs are rejected.
- **English-only** comments, docs, and commit messages.
- Treat the codebase as research code, not production scaffolding — match that style when editing.
