"""Create desktop shortcut and optional Windows startup entry for VibeVoice Desktop."""
import os
import sys
import winreg

PYTHON_EXE = sys.executable
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = "VibeVoice Desktop"
COMMAND = f'"{PYTHON_EXE}" -m desktop.main'


def _create_vbs_launcher():
    """Create a silent .vbs launcher that runs without a console window."""
    vbs_path = os.path.join(REPO_DIR, "desktop", "VibeVoiceDesktop.vbs")
    with open(vbs_path, "w") as f:
        f.write(f'Set WshShell = CreateObject("WScript.Shell")\n')
        f.write(f'WshShell.CurrentDirectory = "{REPO_DIR}"\n')
        f.write(f'WshShell.Run """{PYTHON_EXE}"" -m desktop.main", 0, False\n')
    return vbs_path


def create_desktop_shortcut():
    """Create a .lnk shortcut on the desktop."""
    try:
        import ctypes.wintypes

        # Get Desktop path
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")

        # Create VBS launcher (hides console)
        vbs_path = _create_vbs_launcher()

        # Use PowerShell to create .lnk (most reliable on Windows)
        ps_cmd = f'''
$ws = New-Object -ComObject WScript.Shell
$s = $ws.CreateShortcut("{shortcut_path}")
$s.TargetPath = "wscript.exe"
$s.Arguments = '"{vbs_path}"'
$s.WorkingDirectory = "{REPO_DIR}"
$s.Description = "{APP_NAME}"
$s.Save()
'''
        os.system(f'powershell -Command "{ps_cmd.strip()}"')
        print(f"Desktop shortcut created: {shortcut_path}")
        return shortcut_path
    except Exception as e:
        print(f"Failed to create desktop shortcut: {e}")
        return None


def add_to_startup():
    """Add VibeVoice Desktop to Windows startup via registry."""
    try:
        vbs_path = _create_vbs_launcher()
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'wscript.exe "{vbs_path}"')
        winreg.CloseKey(key)
        print(f"Added to Windows startup: {APP_NAME}")
    except Exception as e:
        print(f"Failed to add to startup: {e}")


def remove_from_startup():
    """Remove VibeVoice Desktop from Windows startup."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print(f"Removed from Windows startup: {APP_NAME}")
    except FileNotFoundError:
        print("Not in startup — nothing to remove")
    except Exception as e:
        print(f"Failed to remove from startup: {e}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="VibeVoice Desktop shortcuts")
    parser.add_argument("--desktop", action="store_true", help="Create desktop shortcut")
    parser.add_argument("--startup", action="store_true", help="Add to Windows startup")
    parser.add_argument("--remove-startup", action="store_true", help="Remove from Windows startup")
    parser.add_argument("--all", action="store_true", help="Create desktop shortcut + add to startup")
    args = parser.parse_args()

    if args.all or args.desktop:
        create_desktop_shortcut()
    if args.all or args.startup:
        add_to_startup()
    if args.remove_startup:
        remove_from_startup()

    if not any([args.desktop, args.startup, args.remove_startup, args.all]):
        print("Usage:")
        print("  python -m desktop.create_shortcuts --desktop     # Desktop shortcut")
        print("  python -m desktop.create_shortcuts --startup     # Start with Windows")
        print("  python -m desktop.create_shortcuts --all         # Both")
        print("  python -m desktop.create_shortcuts --remove-startup  # Remove from startup")
