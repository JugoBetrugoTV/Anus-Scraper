@echo off
chcp 65001 >nul 2>&1
title Unzensierter KI Chat - Starter
color 0F

echo.
echo  ╔══════════════════════════════════════╗
echo  ║    Unzensierter KI Chat - Starter    ║
echo  ╚══════════════════════════════════════╝
echo.

:: ============================================
:: Schritt 1: Python finden
:: ============================================
echo [1/4] Suche Python...

where python >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python
    goto :found_python
)
where python3 >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=python3
    goto :found_python
)
where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON=py
    goto :found_python
)

:: Python nicht gefunden - automatisch installieren via winget
echo  [!] Python nicht gefunden.
echo  [*] Versuche Python automatisch zu installieren...
echo.

where winget >nul 2>&1
if %errorlevel%==0 (
    echo  [*] Installiere Python via winget...
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    if %errorlevel%==0 (
        echo  [OK] Python installiert! Bitte starte dieses Script NEU.
        echo.
        pause
        exit /b 0
    )
)

echo  [FEHLER] Python konnte nicht installiert werden.
echo  Bitte installiere Python manuell: https://www.python.org/downloads/
echo  WICHTIG: Haken bei "Add Python to PATH" setzen!
echo.
pause
exit /b 1

:found_python
for /f "tokens=*" %%i in ('%PYTHON% --version 2^>^&1') do set PYVER=%%i
echo  [OK] %PYVER% gefunden (%PYTHON%)

:: ============================================
:: Schritt 2: Virtual Environment
:: ============================================
echo [2/4] Richte Umgebung ein...

set VENV_DIR=%~dp0.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo  [*] Erstelle virtuelle Umgebung...
    %PYTHON% -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo  [!] venv fehlgeschlagen, nutze System-Python...
        set VPYTHON=%PYTHON%
        goto :install_deps
    )
)
set VPYTHON=%VENV_DIR%\Scripts\python.exe
echo  [OK] Virtuelle Umgebung bereit

:: ============================================
:: Schritt 3: Dependencies installieren
:: ============================================
:install_deps
echo [3/4] Pruefe Dependencies...

"%VPYTHON%" -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [*] Installiere Pakete (PyQt6, requests)...
    "%VPYTHON%" -m pip install --upgrade pip >nul 2>&1
    "%VPYTHON%" -m pip install -r "%~dp0requirements.txt"
    if %errorlevel% neq 0 (
        echo  [FEHLER] Paketinstallation fehlgeschlagen!
        pause
        exit /b 1
    )
    echo  [OK] Pakete installiert
) else (
    echo  [OK] Alle Pakete vorhanden
)

:: ============================================
:: Schritt 4: App starten
:: ============================================
echo [4/4] Starte KI Chat...
echo.
echo  ========================================
echo    App startet... Viel Spass!
echo  ========================================
echo.

"%VPYTHON%" "%~dp0main.py"

echo.
if %errorlevel% neq 0 (
    echo  [FEHLER] App wurde mit Fehlercode %errorlevel% beendet.
) else (
    echo  App wurde beendet.
)
echo.
pause
