@echo off
setlocal
cd /d "%~dp0"

echo.
echo  VibeVoice launcher
echo  ==================
echo   1. Desktop app          (python -m desktop.main)
echo   2. ASR Gradio demo
echo   3. Realtime TTS web API (port 3000)
echo   4. Realtime inference from file
echo   5. Install / reinstall  (pip install -e .)
echo.

set /p choice="Select [1-5]: "

if "%choice%"=="1" python -m desktop.main
if "%choice%"=="2" python demo\vibevoice_asr_gradio_demo.py
if "%choice%"=="3" python demo\vibevoice_realtime_demo.py --port 3000 --model_path microsoft/VibeVoice-Realtime-0.5B
if "%choice%"=="4" python demo\realtime_model_inference_from_file.py
if "%choice%"=="5" pip install -e .

echo.
pause
