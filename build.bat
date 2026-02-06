@echo off
setlocal enabledelayedexpansion
echo ============================================
echo   PreisHai - Build Script
echo   Kein Python noetig - alles automatisch!
echo ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "PYTHON_DIR=%PROJECT_DIR%python"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PYTHON_VER=3.12.8"
set "PYTHON_ZIP=python-%PYTHON_VER%-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VER%/%PYTHON_ZIP%"
set "GETPIP_URL=https://bootstrap.pypa.io/get-pip.py"

REM =============================================
REM  Schritt 0: Pruefen ob portable Python da ist
REM =============================================
if exist "%PYTHON_EXE%" (
    echo Portable Python gefunden: %PYTHON_EXE%
    goto :have_python
)

REM Pruefen ob systemweites Python vorhanden
REM WICHTIG: Windows hat einen Fake python.exe der zum Microsoft Store leitet
REM Deshalb testen wir ob Python WIRKLICH funktioniert mit --version
set PYTHON_CMD=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
)
if not defined PYTHON_CMD (
    py --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=py
    )
)
if not defined PYTHON_CMD (
    python3 --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=python3
    )
)
if defined PYTHON_CMD (
    echo System-Python gefunden: %PYTHON_CMD%
    set "PYTHON_EXE=%PYTHON_CMD%"
    goto :have_python
)

echo Kein Python gefunden - lade portable Version herunter...
echo.

REM =============================================
REM  Schritt 0a: Python herunterladen
REM =============================================
echo [0/4] Lade Python %PYTHON_VER% herunter...
echo       URL: %PYTHON_URL%
echo.

REM Nutze PowerShell zum Download (auf jedem Windows vorhanden)
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PROJECT_DIR%%PYTHON_ZIP%' }"
if errorlevel 1 (
    echo FEHLER: Download fehlgeschlagen!
    echo Bitte pruefe deine Internetverbindung.
    pause
    exit /b 1
)

echo       Download OK!
echo.

REM =============================================
REM  Schritt 0b: Python entpacken
REM =============================================
echo       Entpacke Python...
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"
powershell -Command "& { Expand-Archive -Path '%PROJECT_DIR%%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force }"
if errorlevel 1 (
    echo FEHLER: Entpacken fehlgeschlagen!
    pause
    exit /b 1
)

REM Loesche ZIP
del "%PROJECT_DIR%%PYTHON_ZIP%" >nul 2>&1
echo       Entpackt nach: %PYTHON_DIR%
echo.

REM =============================================
REM  Schritt 0c: pip installieren
REM =============================================
echo       Installiere pip...

REM WICHTIG: Python Embed hat ein ._pth File das imports blockiert
REM Wir muessen "import site" aktivieren
for %%F in ("%PYTHON_DIR%\python*._pth") do (
    powershell -Command "& { (Get-Content '%%F') -replace '#import site','import site' | Set-Content '%%F' }"
)

REM get-pip.py herunterladen
powershell -Command "& { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%GETPIP_URL%' -OutFile '%PYTHON_DIR%\get-pip.py' }"
if errorlevel 1 (
    echo FEHLER: get-pip.py Download fehlgeschlagen!
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location
if errorlevel 1 (
    echo FEHLER: pip Installation fehlgeschlagen!
    pause
    exit /b 1
)
del "%PYTHON_DIR%\get-pip.py" >nul 2>&1
echo       pip OK!
echo.

:have_python
echo.
echo Verwende: %PYTHON_EXE%
"%PYTHON_EXE%" --version
echo.

REM =============================================
REM  Schritt 1: Abhaengigkeiten installieren
REM =============================================
echo [1/3] Installiere Abhaengigkeiten...
"%PYTHON_EXE%" -m pip install -r "%PROJECT_DIR%requirements.txt" --no-warn-script-location
if errorlevel 1 (
    echo.
    echo FEHLER beim Installieren der Abhaengigkeiten!
    pause
    exit /b 1
)

echo.
echo [2/3] Erstelle EXE-Datei (das dauert 1-2 Minuten)...
"%PYTHON_EXE%" -m PyInstaller --noconfirm --onefile --windowed ^
    --name "PreisHai" ^
    --add-data "app;app" ^
    "%PROJECT_DIR%main.py"
if errorlevel 1 (
    echo FEHLER beim Erstellen der EXE!
    pause
    exit /b 1
)

echo.
echo [3/3] Fertig!
echo.
echo ============================================
echo   Die EXE-Datei befindet sich in:
echo   %PROJECT_DIR%dist\PreisHai.exe
echo.
echo   Einfach PreisHai.exe doppelklicken!
echo ============================================
echo.
pause
