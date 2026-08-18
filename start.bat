@echo off
chcp 65001 >nul
title Discord Control Bot

set "PY_EXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if exist "%PY_EXE%" (
    "%PY_EXE%" run.py
) else (
    python run.py
)

pause
