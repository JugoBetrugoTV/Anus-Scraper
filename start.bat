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
echo [1/5] Suche Python...

if exist "%PYPYTHON%" (
    echo  [OK] Portables Python gefunden
    goto python_ready
)

:: py Launcher testen (pruefen dass es echtes Python ist, nicht Store-Alias)
py -3 --version >nul 2>&1
if %errorlevel%==0 (
    set "PYPYTHON=py -3"
    echo  [OK] System-Python gefunden
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
echo [2/5] Pruefe Ollama...

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

:: Ollama Server stoppen und mit korrektem Modell-Pfad neu starten
:: Damit die OLLAMA_MODELS Variable greift
echo  [*] Modell-Pfad: %OLLAMA_MODELS%

:: Alle Ollama-Prozesse stoppen
taskkill /f /im ollama.exe >nul 2>&1
taskkill /f /im "ollama app.exe" >nul 2>&1
timeout /t 3 /nobreak >nul

:: Ollama neu starten mit unserer OLLAMA_MODELS Variable
echo  [*] Starte Ollama Server...

:: Finde Ollama-Pfad (winget installiert nach LOCALAPPDATA)
set "OLLAMA_CMD=ollama"
where ollama >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" set "OLLAMA_CMD=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
)
start "ollama" /MIN cmd /c "%OLLAMA_CMD% serve"

:: Warten bis Server bereit ist
set "WAIT=0"
:wait_ollama
if %WAIT% geq 30 (
    echo  [!] Ollama Server startet nicht - starte App trotzdem...
    goto ollama_running
)
timeout /t 1 /nobreak >nul
set /a WAIT+=1
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 1 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel% neq 0 goto wait_ollama
echo  [OK] Ollama Server laeuft

:ollama_running

:: ============================================
:: Schritt 3: Dependencies installieren
:: ============================================
echo [3/5] Pruefe Dependencies...

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
:: Schritt 4: KI-Modell pruefen
:: ============================================
echo [4/5] Pruefe KI-Modell...

set "DEFAULT_MODEL=qwen2.5-coder:32b"

:: Pruefen ob Modell schon vorhanden
ollama list 2>nul | findstr /i "qwen2.5-coder:32b" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] %DEFAULT_MODEL% ist vorhanden
    goto model_ready
)

echo.
echo  ========================================
echo  Das Standard-Modell %DEFAULT_MODEL%
echo  ist noch nicht heruntergeladen.
echo  Download-Groesse: ca. 20 GB
echo  ========================================
echo.
echo  Druecke eine beliebige Taste um den
echo  Download zu starten, oder schliesse
echo  das Fenster zum Abbrechen.
echo.
pause

echo.
echo  [*] Lade %DEFAULT_MODEL% herunter...
echo  [*] Das kann je nach Leitung dauern...
echo.
ollama pull %DEFAULT_MODEL%
if %errorlevel% neq 0 (
    echo  [!] Download fehlgeschlagen - du kannst das Modell spaeter in der App laden.
    goto model_ready
)
echo  [OK] %DEFAULT_MODEL% bereit!

:model_ready

:: ============================================
:: Schritt 5: App starten
:: ============================================
echo [5/5] Starte KI Chat...
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
