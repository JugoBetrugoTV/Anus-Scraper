@echo off
echo ============================================
echo   PreisHai - Build Script
echo ============================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden! Bitte installiere Python 3.10+
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/3] Installiere Abhaengigkeiten...
pip install -r requirements.txt
if errorlevel 1 (
    echo FEHLER beim Installieren der Abhaengigkeiten!
    pause
    exit /b 1
)

echo.
echo [2/3] Erstelle EXE-Datei...
pyinstaller --noconfirm --onefile --windowed ^
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
