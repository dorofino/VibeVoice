Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "I:\2026\VibeVoice"
WshShell.Run """C:\Program Files\Python313\python.exe"" -m desktop.main", 0, False
