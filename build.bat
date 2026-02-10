@echo off
setlocal enabledelayedexpansion
title Unzensierter KI Chat - Build
color 0F

set "BASEDIR=%~dp0"
set "PYDIR=%BASEDIR%python"
set "PYPYTHON=%PYDIR%\python.exe"

echo.
echo  === Unzensierter KI Chat - Build ===
echo.

:: Portables Python nutzen falls vorhanden
if exist "%PYPYTHON%" (
    echo  [OK] Portables Python gefunden
    goto :build
)

:: Sonst System-Python
py --version >nul 2>&1
if %errorlevel%==0 (
    set "PYPYTHON=py"
    echo  [OK] System-Python gefunden
    goto :build
)

python --version 2>nul | findstr /i "Python 3" >nul 2>&1
if %errorlevel%==0 (
    set "PYPYTHON=python"
    echo  [OK] System-Python gefunden
    goto :build
)

echo  [FEHLER] Python nicht gefunden!
echo  Bitte zuerst start.bat ausfuehren um Python herunterzuladen.
echo.
pause
exit /b 1

:build
echo  [*] Installiere Build-Dependencies...
"%PYPYTHON%" -m pip install PyQt6 requests pyinstaller --no-warn-script-location
if %errorlevel% neq 0 (
    echo  [FEHLER] Paketinstallation fehlgeschlagen!
    pause
    exit /b 1
)

echo  [*] Baue Executable...
"%PYPYTHON%" -m PyInstaller --onefile --name "KI-Chat" --windowed --clean "%BASEDIR%main.py"
if %errorlevel% neq 0 (
    echo  [FEHLER] Build fehlgeschlagen!
    pause
    exit /b 1
)

echo.
echo  [OK] Fertig! Executable: dist\KI-Chat.exe
echo.
pause
endlocal
