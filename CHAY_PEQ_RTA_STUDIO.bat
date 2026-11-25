@echo off
title PEQ & RTA Acoustic Calibration Studio
cd /d "%~dp0"
echo ======================================================================
echo    KHOI DONG ACOUSTIC PARAMETRIC EQ (PEQ) & RTA CALIBRATION STUDIO
echo ======================================================================
python peq_studio\serve_studio.py
if errorlevel 1 (
    echo.
    echo Khong tim thay Python! Dang mo truc tiep index.html trong trinh duyet...
    start "" "peq_studio\index.html"
)
pause
