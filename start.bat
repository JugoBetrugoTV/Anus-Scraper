@echo off
setlocal
title Unzensierter KI Chat - Starter
color 0F

set "BASEDIR=%~dp0"
set "PYDIR=%BASEDIR%python"
set "PYPYTHON=%PYDIR%\python.exe"
set "PYVERSION=3.12.10"
set "PYZIP=python-%PYVERSION%-embed-amd64.zip"
set "PYURL=https://www.python.org/ftp/python/%PYVERSION%/%PYZIP%"
set "GETPIPURL=https://bootstrap.pypa.io/get-pip.py"

:: Modelle neben dem Bot speichern (gleiches Laufwerk)
set "OLLAMA_MODELS=%BASEDIR%ollama_models"
if not exist "%OLLAMA_MODELS%" mkdir "%OLLAMA_MODELS%"

echo.
echo  ========================================
echo     Unzensierter KI Chat - Starter
echo  ========================================
echo.

:: ============================================
:: Schritt 1: Portable Python bereitstellen
:: ============================================
echo [1/4] Suche Python...

if exist "%PYPYTHON%" (
    echo  [OK] Portables Python gefunden
    goto python_ready
)

py --version >nul 2>&1
if %errorlevel%==0 (
    set "PYPYTHON=py"
    echo  [OK] System-Python gefunden
    goto python_ready
)

echo  [*] Python nicht gefunden - lade portable Version...
echo  [*] Download: Python %PYVERSION% Embedded...
echo.

if not exist "%PYDIR%" mkdir "%PYDIR%"

powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYURL%' -OutFile '%BASEDIR%%PYZIP%' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo  [FEHLER] Python Download fehlgeschlagen.
    pause
    exit /b 1
)
echo  [OK] Download abgeschlossen

echo  [*] Entpacke Python...
powershell -NoProfile -Command "Expand-Archive -Path '%BASEDIR%%PYZIP%' -DestinationPath '%PYDIR%' -Force"
if %errorlevel% neq 0 (
    echo  [FEHLER] Entpacken fehlgeschlagen.
    pause
    exit /b 1
)
echo  [OK] Entpackt

del /q "%BASEDIR%%PYZIP%" >nul 2>&1

echo  [*] Konfiguriere Python...
for %%f in ("%PYDIR%\python*._pth") do (
    echo python312.zip> "%%f"
    echo .>> "%%f"
    echo import site>> "%%f"
)

echo  [*] Installiere pip...
powershell -NoProfile -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%GETPIPURL%' -OutFile '%PYDIR%\get-pip.py' -UseBasicParsing"
if %errorlevel% neq 0 (
    echo  [FEHLER] get-pip.py Download fehlgeschlagen.
    pause
    exit /b 1
)

"%PYPYTHON%" "%PYDIR%\get-pip.py" --no-warn-script-location >nul 2>&1
if %errorlevel% neq 0 (
    echo  [FEHLER] pip Installation fehlgeschlagen.
    pause
    exit /b 1
)
del /q "%PYDIR%\get-pip.py" >nul 2>&1
echo  [OK] Portable Python %PYVERSION% bereit!

:python_ready

:: ============================================
:: Schritt 2: Ollama pruefen
:: ============================================
echo [2/4] Pruefe Ollama...

where ollama >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] Ollama gefunden
    goto ollama_ready
)

powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] Ollama laeuft bereits
    goto ollama_ready
)

echo  [*] Ollama nicht gefunden - installiere...
echo.

where winget >nul 2>&1
if %errorlevel% neq 0 (
    echo  Bitte installiere Ollama manuell: https://ollama.com/download
    pause
    exit /b 1
)

winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
if %errorlevel% neq 0 (
    echo  Bitte installiere Ollama manuell: https://ollama.com/download
    pause
    exit /b 1
)
echo  [OK] Ollama installiert

:ollama_ready

:: ============================================
:: Schritt 3: Dependencies installieren
:: ============================================
echo [3/4] Pruefe Dependencies...

"%PYPYTHON%" -c "import PyQt6" >nul 2>&1
if %errorlevel%==0 goto deps_ok

echo  [*] Installiere Pakete...
"%PYPYTHON%" -m pip install --upgrade pip --no-warn-script-location >nul 2>&1
"%PYPYTHON%" -m pip install PyQt6 requests --no-warn-script-location
if %errorlevel% neq 0 (
    echo  [FEHLER] Paketinstallation fehlgeschlagen!
    pause
    exit /b 1
)
echo  [OK] Pakete installiert
goto deps_done

:deps_ok
echo  [OK] Alle Pakete vorhanden

:deps_done

:: ============================================
:: Schritt 4: App starten
:: ============================================
echo [4/4] Starte KI Chat...
echo.
echo  ========================================
echo    App startet... Viel Spass!
echo  ========================================
echo.

"%PYPYTHON%" "%BASEDIR%main.py"

echo.
if %errorlevel% neq 0 echo  [FEHLER] App wurde mit Fehlercode %errorlevel% beendet.
echo.
pause
endlocal
