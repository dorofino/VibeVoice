"""AI-powered text processing: Enhanced Intent Recognition + Text Polishing.

Uses Claude API (haiku) for fast, cheap post-processing of ASR output.
"""
import ctypes
import ctypes.wintypes
import os
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal


def _get_foreground_window_info() -> dict:
    """Get info about the currently focused window using Win32 API."""
    try:
        user32 = ctypes.windll.user32

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return {}

        # Window title
        length = user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)

        # Window class name
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)

        # Process name
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = ""
        try:
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
            if handle:
                exe_buf = ctypes.create_unicode_buffer(260)
                size = ctypes.wintypes.DWORD(260)
                kernel32.QueryFullProcessImageNameW(handle, 0, exe_buf, ctypes.byref(size))
                kernel32.CloseHandle(handle)
                process_name = os.path.basename(exe_buf.value)
        except Exception:
            pass

        return {
            "title": title_buf.value,
            "class": class_buf.value,
            "process": process_name,
        }
    except Exception:
        return {}


def _detect_context(window_info: dict) -> str:
    """Detect the input context from window info."""
    process = window_info.get("process", "").lower()
    title = window_info.get("title", "").lower()

    # Code editors
    if any(p in process for p in ("code.exe", "devenv.exe", "pycharm", "idea", "sublime_text", "notepad++")):
        return "code_editor"
    # Terminal
    if any(p in process for p in ("windowsterminal.exe", "cmd.exe", "powershell.exe", "wt.exe")):
        return "terminal"
    # Email
    if any(p in process for p in ("outlook.exe", "thunderbird.exe")) or "gmail" in title or "mail" in title:
        return "email"
    # Chat / messaging
    if any(p in process for p in ("slack.exe", "teams.exe", "discord.exe", "telegram.exe", "whatsapp.exe")):
        return "chat"
    # Browser
    if any(p in process for p in ("chrome.exe", "firefox.exe", "msedge.exe", "brave.exe")):
        if any(kw in title for kw in ("github", "stack overflow", "code", "developer")):
            return "code_browser"
        if any(kw in title for kw in ("mail", "gmail", "outlook")):
            return "email"
        if any(kw in title for kw in ("slack", "discord", "teams", "chat")):
            return "chat"
        return "browser"
    # Word processor
    if any(p in process for p in ("winword.exe", "wordpad.exe", "docs")):
        return "document"
    # Notes
    if any(p in process for p in ("onenote.exe", "notion.exe", "obsidian.exe")):
        return "notes"

    return "general"


CONTEXT_INSTRUCTIONS = {
    "code_editor": "The user is dictating in a code editor. Format as appropriate code or code comments. Use technical terminology accurately. Preserve variable names and technical terms.",
    "terminal": "The user is dictating a terminal command. Format as a shell command. Be concise and precise.",
    "email": "The user is composing an email. Use professional tone, proper punctuation, and paragraph formatting.",
    "chat": "The user is in a chat app. Keep it casual and conversational. Short sentences.",
    "code_browser": "The user is browsing code-related sites. Format technically, preserve code terms.",
    "browser": "The user is typing in a browser. Use standard formatting.",
    "document": "The user is in a word processor. Use formal writing, proper paragraph structure.",
    "notes": "The user is taking notes. Use concise bullet-point style if appropriate.",
    "general": "Format naturally with proper punctuation and grammar.",
}


class TextProcessor(QObject):
    """Post-processes ASR text using Claude API."""

    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._client = None
        self._api_key: Optional[str] = None
        self._model = "claude-haiku-4-5-20251001"

    def set_api_key(self, key: str):
        """Set or update the API key. Resets the client so it reconnects."""
        self._api_key = key.strip() if key else None
        self._client = None  # Force re-init on next call

    def _ensure_client(self):
        if self._client is None:
            try:
                import anthropic
                # Use explicit key if set, otherwise fall back to env var
                if self._api_key:
                    self._client = anthropic.Anthropic(api_key=self._api_key)
                else:
                    self._client = anthropic.Anthropic()
            except Exception as e:
                self.error.emit(f"Claude API init failed: {e}")
                return False
        return True

    def polish_text(
        self,
        raw_text: str,
        enhanced_intent: bool = True,
        polish: bool = True,
    ) -> str:
        """Process raw ASR text with optional intent recognition and polishing.

        Args:
            raw_text: Raw transcription from ASR
            enhanced_intent: If True, detect window context and adjust formatting
            polish: If True, fix filler words, homophones, formatting

        Returns:
            Processed text, or raw_text if processing fails
        """
        if not polish and not enhanced_intent:
            return raw_text

        if not self._ensure_client():
            return raw_text

        # Build the prompt
        system_parts = ["You are a speech-to-text post-processor. Return ONLY the corrected text, nothing else. No explanations, no quotes, no markdown."]

        if polish:
            system_parts.append(
                "Fix filler words (um, uh, like, you know), correct homophones, "
                "fix grammar, and adjust punctuation. Keep the original meaning intact."
            )

        context_hint = ""
        if enhanced_intent:
            window_info = _get_foreground_window_info()
            context = _detect_context(window_info)
            context_hint = CONTEXT_INSTRUCTIONS.get(context, CONTEXT_INSTRUCTIONS["general"])
            system_parts.append(f"Context: {context_hint}")
            if window_info.get("title"):
                system_parts.append(f"Active window: {window_info['title'][:80]}")

        import threading

        result_holder = [raw_text]
        error_holder = [None]

        def _call_api():
            try:
                response = self._client.messages.create(
                    model=self._model,
                    max_tokens=1024,
                    timeout=8.0,
                    system="\n".join(system_parts),
                    messages=[{"role": "user", "content": raw_text}],
                )
                text = response.content[0].text.strip()
                if text:
                    result_holder[0] = text
            except Exception as e:
                error_holder[0] = str(e)

        thread = threading.Thread(target=_call_api, daemon=True)
        thread.start()
        thread.join(timeout=10.0)  # Hard 10s deadline

        if thread.is_alive():
            self.error.emit("Text processing timed out")
            return raw_text

        if error_holder[0]:
            self.error.emit(f"Text processing failed: {error_holder[0]}")

        return result_holder[0]
