import ctypes
import ctypes.wintypes
import time

import keyboard


def _declare_win32_signatures():
    """Set argtypes/restype on Win32 calls so 64-bit handles aren't truncated.

    Without this, ctypes defaults the return type to C int (32-bit) and any
    handle/pointer above 2 GiB gets sign-extended into a garbage address,
    causing access violations in GlobalLock / wstring_at.
    """
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    HANDLE = ctypes.wintypes.HANDLE
    HGLOBAL = HANDLE
    LPVOID = ctypes.c_void_p

    user32.OpenClipboard.argtypes = [HANDLE]
    user32.OpenClipboard.restype = ctypes.wintypes.BOOL
    user32.CloseClipboard.argtypes = []
    user32.CloseClipboard.restype = ctypes.wintypes.BOOL
    user32.EmptyClipboard.argtypes = []
    user32.EmptyClipboard.restype = ctypes.wintypes.BOOL
    user32.GetClipboardData.argtypes = [ctypes.wintypes.UINT]
    user32.GetClipboardData.restype = HANDLE
    user32.SetClipboardData.argtypes = [ctypes.wintypes.UINT, HANDLE]
    user32.SetClipboardData.restype = HANDLE

    kernel32.GlobalAlloc.argtypes = [ctypes.wintypes.UINT, ctypes.c_size_t]
    kernel32.GlobalAlloc.restype = HGLOBAL
    kernel32.GlobalLock.argtypes = [HGLOBAL]
    kernel32.GlobalLock.restype = LPVOID
    kernel32.GlobalUnlock.argtypes = [HGLOBAL]
    kernel32.GlobalUnlock.restype = ctypes.wintypes.BOOL


_declare_win32_signatures()


def _set_clipboard_text(text: str):
    """Set system clipboard text using Win32 API directly."""
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x0002

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    for _ in range(15):
        if user32.OpenClipboard(0):
            break
        time.sleep(0.02)
    else:
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

    for _ in range(10):
        if user32.OpenClipboard(0):
            break
        time.sleep(0.01)
    else:
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


def _send_ctrl_v_win32() -> bool:
    """Fallback Ctrl+V via SendInput when keyboard.send is unreliable."""

    user32 = ctypes.windll.user32
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL = 0x11
    VK_V = 0x56

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.wintypes.WORD),
            ("wScan", ctypes.wintypes.WORD),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("time", ctypes.wintypes.DWORD),
            ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
        ]

    class INPUT(ctypes.Structure):
        class _UNION(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]
        _anonymous_ = ("u",)
        _fields_ = [
            ("type", ctypes.wintypes.DWORD),
            ("u", _UNION),
        ]

    inputs = (INPUT * 4)()
    inputs[0].type = INPUT_KEYBOARD
    inputs[0].ki = KEYBDINPUT(VK_CONTROL, 0, 0, 0, None)
    inputs[1].type = INPUT_KEYBOARD
    inputs[1].ki = KEYBDINPUT(VK_V, 0, 0, 0, None)
    inputs[2].type = INPUT_KEYBOARD
    inputs[2].ki = KEYBDINPUT(VK_V, 0, KEYEVENTF_KEYUP, 0, None)
    inputs[3].type = INPUT_KEYBOARD
    inputs[3].ki = KEYBDINPUT(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0, None)

    sent = user32.SendInput(len(inputs), ctypes.byref(inputs), ctypes.sizeof(INPUT))
    return sent == len(inputs)


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
            _send_ctrl_v_win32()  # Paste failed but text is on clipboard
