@echo off
title MVSilicon DSP Assistant & Auto-Fixer
cd /d "%~dp0"
python acp_dsp_assistant.py
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong the chay Python. Vui long kiem tra lai moi truong Python.
    pause
)
