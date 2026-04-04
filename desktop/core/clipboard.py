import ctypes
import ctypes.wintypes
import time

import keyboard


def _set_clipboard_text(text: str):
    """Set system clipboard text using Win32 API directly."""
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if not user32.OpenClipboard(0):
        return False

    try:
        user32.EmptyClipboard()

        # Allocate global memory for the text
        encoded = text.encode("utf-16-le") + b"\x00\x00"
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not h_mem:
            return False

        ptr = kernel32.GlobalLock(h_mem)
        ctypes.memmove(ptr, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)

        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        return True
    finally:
        user32.CloseClipboard()


def _get_clipboard_text() -> str:
    """Get system clipboard text using Win32 API directly."""
    CF_UNICODETEXT = 13
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if not user32.OpenClipboard(0):
        return ""

    try:
        h_data = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_data:
            return ""
        ptr = kernel32.GlobalLock(h_data)
        if not ptr:
            return ""
        try:
            text = ctypes.wstring_at(ptr)
            return text
        finally:
            kernel32.GlobalUnlock(h_data)
    finally:
        user32.CloseClipboard()


def grab_selection() -> str:
    """Simulate Ctrl+C to copy selected text, then read clipboard."""
    old_text = _get_clipboard_text()

    # Release all modifier keys first — the user may still be holding
    # the TTS hotkey (e.g. Ctrl+Win+Alt) which interferes with Ctrl+C
    for key in ("ctrl", "alt", "win", "shift"):
        try:
            keyboard.release(key)
        except Exception:
            pass
    time.sleep(0.05)

    keyboard.send("ctrl+c")
    time.sleep(0.15)

    new_text = _get_clipboard_text()
    if new_text and new_text != old_text:
        return new_text
    return new_text or ""


def insert_text(text: str, try_paste: bool = True):
    """Always place text on clipboard. Attempt Ctrl+V paste if possible."""
    _set_clipboard_text(text)

    if try_paste:
        # Release any held modifiers first to avoid conflicts
        for key in ("ctrl", "alt", "shift", "win"):
            try:
                keyboard.release(key)
            except Exception:
                pass
        time.sleep(0.1)
        try:
            keyboard.send("ctrl+v")
        except Exception:
            pass  # Paste failed but text is on clipboard
