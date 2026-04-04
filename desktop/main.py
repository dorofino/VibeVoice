"""VibeVoice Desktop - Voice AI for your desktop.

Usage:
    python -m desktop.main
"""
import sys
from pathlib import Path

# Ensure repo root is on the path so we can import vibevoice and demo modules
repo_root = str(Path(__file__).resolve().parent.parent)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from desktop.app import VoiceDesktopApp


def main():
    app = VoiceDesktopApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
