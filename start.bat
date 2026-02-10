@echo off
setlocal enabledelayedexpansion
title Unzensierter KI Chat - Starter
color 0F

set "BASEDIR=%~dp0"
set "PYDIR=%BASEDIR%python"
set "PYPYTHON=%PYDIR%\python.exe"
set "PYVERSION=3.12.10"
set "PYZIP=python-%PYVERSION%-embed-amd64.zip"
set "PYURL=https://www.python.org/ftp/python/%PYVERSION%/%PYZIP%"
set "GETPIPURL=https://bootstrap.pypa.io/get-pip.py"

echo.
echo  ========================================
echo     Unzensierter KI Chat - Starter
echo  ========================================
echo.

:: ============================================
:: Schritt 1: Portable Python bereitstellen
:: ============================================
echo [1/4] Suche Python...

:: Pruefen ob portables Python bereits vorhanden
if exist "%PYPYTHON%" (
    echo  [OK] Portables Python gefunden
    goto :python_ready
)

:: Pruefen ob System-Python verfuegbar ist
py --version >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] System-Python gefunden (py)
    set "PYPYTHON=py"
    goto :skip_portable
)

python --version 2>nul | findstr /i "Python 3" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] System-Python gefunden (python)
    set "PYPYTHON=python"
    goto :skip_portable
)

:: Kein Python vorhanden - Portable Version herunterladen
echo  [!] Python nicht gefunden - lade portable Version...
echo  [*] Download: Python %PYVERSION% Embedded...
echo.

:: Ordner erstellen
if not exist "%PYDIR%" mkdir "%PYDIR%"

:: Download mit PowerShell (ist auf jedem Windows vorhanden)
powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYURL%' -OutFile '%BASEDIR%%PYZIP%' -UseBasicParsing; Write-Host ' [OK] Download abgeschlossen' } catch { Write-Host ' [FEHLER] Download fehlgeschlagen:' $_.Exception.Message; exit 1 }"
if %errorlevel% neq 0 (
    echo.
    echo  [FEHLER] Python konnte nicht heruntergeladen werden.
    echo  Pruefe deine Internetverbindung.
    echo.
    pause
    exit /b 1
)

:: Entpacken mit PowerShell
echo  [*] Entpacke Python...
powershell -NoProfile -Command "try { Expand-Archive -Path '%BASEDIR%%PYZIP%' -DestinationPath '%PYDIR%' -Force; Write-Host ' [OK] Entpackt' } catch { Write-Host ' [FEHLER]' $_.Exception.Message; exit 1 }"
if %errorlevel% neq 0 (
    echo  [FEHLER] Entpacken fehlgeschlagen.
    pause
    exit /b 1
)

:: ZIP aufraemen
del /q "%BASEDIR%%PYZIP%" >nul 2>&1

:: PTH-Datei anpassen damit pip und Pakete funktionieren
:: Die _pth Datei muss "import site" enthalten
echo  [*] Konfiguriere Python...
for %%f in ("%PYDIR%\python*._pth") do (
    echo python312.zip> "%%f"
    echo .>> "%%f"
    echo import site>> "%%f"
)

:: pip installieren
echo  [*] Installiere pip...
powershell -NoProfile -Command "try { [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%GETPIPURL%' -OutFile '%PYDIR%\get-pip.py' -UseBasicParsing } catch { Write-Host ' [FEHLER]' $_.Exception.Message; exit 1 }"
if %errorlevel% neq 0 (
    echo  [FEHLER] get-pip.py Download fehlgeschlagen.
    pause
    exit /b 1
)

"%PYPYTHON%" "%PYDIR%\get-pip.py" --no-warn-script-location >nul 2>&1
if %errorlevel% neq 0 (
    echo  [FEHLER] pip Installation fehlgeschlagen.
    echo  Versuche erneut mit Ausgabe:
    "%PYPYTHON%" "%PYDIR%\get-pip.py"
    pause
    exit /b 1
)
del /q "%PYDIR%\get-pip.py" >nul 2>&1
echo  [OK] Portable Python %PYVERSION% bereit!

:python_ready
:skip_portable

:: ============================================
:: Schritt 2: Ollama pruefen
:: ============================================
echo [2/4] Pruefe Ollama...

where ollama >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] Ollama gefunden
    goto :ollama_ready
)

:: Pruefen ob Ollama laeuft
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'http://localhost:11434/api/tags' -UseBasicParsing -TimeoutSec 2 | Out-Null; exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 (
    echo  [OK] Ollama laeuft bereits
    goto :ollama_ready
)

echo  [!] Ollama nicht gefunden.
echo  [*] Versuche Ollama zu installieren...
echo.

where winget >nul 2>&1
if %errorlevel%==0 (
    winget install Ollama.Ollama --accept-source-agreements --accept-package-agreements
    if %errorlevel%==0 (
        echo  [OK] Ollama installiert!
    ) else (
        echo.
        echo  [!] Ollama konnte nicht automatisch installiert werden.
        echo  Bitte installiere Ollama manuell: https://ollama.com/download
        echo.
        pause
        exit /b 1
    )
) else (
    echo  Bitte installiere Ollama manuell: https://ollama.com/download
    echo.
    pause
    exit /b 1
)

:ollama_ready

:: ============================================
:: Schritt 3: Dependencies installieren
:: ============================================
echo [3/4] Pruefe Dependencies...

"%PYPYTHON%" -c "import PyQt6" >nul 2>&1
if %errorlevel% neq 0 (
    echo  [*] Installiere Pakete (PyQt6, requests)...
    "%PYPYTHON%" -m pip install --upgrade pip --no-warn-script-location >nul 2>&1
    "%PYPYTHON%" -m pip install PyQt6 requests --no-warn-script-location
    if %errorlevel% neq 0 (
        echo.
        echo  [FEHLER] Paketinstallation fehlgeschlagen!
        echo.
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

"%PYPYTHON%" "%BASEDIR%main.py"

echo.
if %errorlevel% neq 0 (
    echo  [FEHLER] App wurde mit Fehlercode %errorlevel% beendet.
) else (
    echo  App wurde beendet.
)
echo.
pause
endlocal
