@echo off
echo ============================================
echo   PreisHai - Build Script
echo ============================================
echo.

REM Finde Python - probiere verschiedene Varianten
set PYTHON_CMD=
where python >nul 2>&1 && set PYTHON_CMD=python
if not defined PYTHON_CMD (
    where py >nul 2>&1 && set PYTHON_CMD=py
)
if not defined PYTHON_CMD (
    where python3 >nul 2>&1 && set PYTHON_CMD=python3
)

if not defined PYTHON_CMD (
    echo ============================================
    echo   FEHLER: Python nicht gefunden!
    echo ============================================
    echo.
    echo Python ist nicht installiert oder nicht im PATH.
    echo.
    echo So behebst du das:
    echo   1. Lade Python 3.10+ herunter:
    echo      https://www.python.org/downloads/
    echo.
    echo   2. WICHTIG: Bei der Installation den Haken setzen bei:
    echo      [x] "Add Python to PATH"
    echo.
    echo   3. Nach der Installation ein NEUES Terminal oeffnen
    echo      und build.bat erneut starten.
    echo.
    echo   Alternativ: Wenn Python schon installiert ist,
    echo   oeffne die Systemsteuerung ^> "Umgebungsvariablen"
    echo   und fuege den Python-Pfad zum PATH hinzu.
    echo   Typischer Pfad: C:\Users\DEINNAME\AppData\Local\Programs\Python\Python3xx\
    echo ============================================
    pause
    exit /b 1
)

echo Python gefunden: %PYTHON_CMD%
%PYTHON_CMD% --version
echo.

REM Finde pip
set PIP_CMD=
where pip >nul 2>&1 && set PIP_CMD=pip
if not defined PIP_CMD (
    set PIP_CMD=%PYTHON_CMD% -m pip
)

echo [1/3] Installiere Abhaengigkeiten...
%PIP_CMD% install -r requirements.txt
if errorlevel 1 (
    echo.
    echo FEHLER beim Installieren der Abhaengigkeiten!
    echo Versuche: %PYTHON_CMD% -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo [2/3] Erstelle EXE-Datei...
%PYTHON_CMD% -m PyInstaller --noconfirm --onefile --windowed ^
    --name "PreisHai" ^
    --add-data "app;app" ^
    main.py
if errorlevel 1 (
    echo FEHLER beim Erstellen der EXE!
    pause
    exit /b 1
)

echo.
echo [3/3] Fertig!
echo.
echo ============================================
echo   Die EXE-Datei befindet sich in: dist\PreisHai.exe
echo ============================================
echo.
pause
