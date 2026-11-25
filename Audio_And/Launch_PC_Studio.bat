@echo off
chcp 65001 >nul
title BEST SOUND DSP STUDIO — PC Multi-Profile Controller
echo ==============================================================================
echo     BEST SOUND T1V2 — PC MULTI-PROFILE STUDIO (MVSILICON BP1048B2)
echo ==============================================================================
echo [*] Đang khởi động phần mềm PC Studio...
echo.

python "%~dp0BestSound_DSP_Studio_PC.py"

if %errorlevel% neq 0 (
    echo.
    echo [!] Đã có lỗi xảy ra khi chạy phần mềm.
    pause
)
