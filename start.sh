#!/usr/bin/env bash
set -e

# ============================================
#  Unzensierter KI Chat - Auto-Starter
#  Doppelklick oder: ./start.sh
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║    Unzensierter KI Chat - Starter    ║"
echo "  ╚══════════════════════════════════════╝"
echo ""

# ============================================
# Schritt 1: Python finden
# ============================================
echo "[1/4] Suche Python..."

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        # Pruefe ob es wirklich Python 3 ist
        ver=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
        if [ "$ver" = "3" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  [!] Python 3 nicht gefunden. Versuche automatische Installation..."

    # Versuche automatisch zu installieren
    if command -v apt-get &>/dev/null; then
        echo "  [*] Installiere via apt..."
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip python3-venv
        PYTHON="python3"
    elif command -v dnf &>/dev/null; then
        echo "  [*] Installiere via dnf..."
        sudo dnf install -y python3 python3-pip
        PYTHON="python3"
    elif command -v pacman &>/dev/null; then
        echo "  [*] Installiere via pacman..."
        sudo pacman -Sy --noconfirm python python-pip
        PYTHON="python3"
    elif command -v brew &>/dev/null; then
        echo "  [*] Installiere via Homebrew..."
        brew install python
        PYTHON="python3"
    else
        echo "  [FEHLER] Python 3 konnte nicht installiert werden."
        echo "  Bitte manuell installieren:"
        echo "    Ubuntu/Debian: sudo apt install python3 python3-pip python3-venv"
        echo "    Arch:          sudo pacman -S python python-pip"
        echo "    macOS:         brew install python"
        exit 1
    fi
fi

PYVER=$("$PYTHON" --version 2>&1)
echo "  [OK] $PYVER gefunden ($PYTHON)"

# ============================================
# Schritt 2: Virtual Environment
# ============================================
echo "[2/4] Richte Umgebung ein..."

if [ ! -f "$VENV_DIR/bin/python" ]; then
    echo "  [*] Erstelle virtuelle Umgebung..."
    "$PYTHON" -m venv "$VENV_DIR" 2>/dev/null || {
        echo "  [!] venv fehlgeschlagen, versuche python3-venv zu installieren..."
        if command -v apt-get &>/dev/null; then
            sudo apt-get install -y python3-venv
            "$PYTHON" -m venv "$VENV_DIR"
        else
            echo "  [!] Nutze System-Python als Fallback..."
            VPYTHON="$PYTHON"
        fi
    }
fi

if [ -f "$VENV_DIR/bin/python" ]; then
    VPYTHON="$VENV_DIR/bin/python"
else
    VPYTHON="${VPYTHON:-$PYTHON}"
fi
echo "  [OK] Umgebung bereit"

# ============================================
# Schritt 3: Dependencies installieren
# ============================================
echo "[3/4] Pruefe Dependencies..."

if ! "$VPYTHON" -c "import PyQt6" &>/dev/null; then
    echo "  [*] Installiere Pakete (PyQt6, requests)..."
    "$VPYTHON" -m pip install --upgrade pip --quiet 2>/dev/null
    "$VPYTHON" -m pip install -r "$SCRIPT_DIR/requirements.txt"
    if [ $? -ne 0 ]; then
        echo "  [FEHLER] Paketinstallation fehlgeschlagen!"
        exit 1
    fi
    echo "  [OK] Pakete installiert"
else
    echo "  [OK] Alle Pakete vorhanden"
fi

# ============================================
# Schritt 4: App starten
# ============================================
echo "[4/4] Starte KI Chat..."
echo ""
echo "  ========================================"
echo "    App startet... Viel Spass!"
echo "  ========================================"
echo ""

"$VPYTHON" "$SCRIPT_DIR/main.py"
