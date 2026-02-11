#!/usr/bin/env bash
# Kein set -e: Nicht-kritische Fehler (z.B. ollama pull) sollen Script nicht abbrechen

# ============================================
#  Unzensierter KI Chat - Auto-Starter
#  Doppelklick oder: ./start.sh
# ============================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
DEFAULT_MODEL="qwen2.5-coder:32b"

# Modelle neben dem Bot speichern (gleiches Laufwerk)
export OLLAMA_MODELS="$SCRIPT_DIR/ollama_models"
mkdir -p "$OLLAMA_MODELS"

echo ""
echo "  ========================================"
echo "     Unzensierter KI Chat - Starter"
echo "  ========================================"
echo ""

# ============================================
# Schritt 1: Python finden
# ============================================
echo "[1/5] Suche Python..."

PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo "0")
        if [ "$ver" = "3" ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  [!] Python 3 nicht gefunden. Versuche automatische Installation..."

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
# Schritt 2: Ollama pruefen
# ============================================
echo "[2/5] Pruefe Ollama..."

if command -v ollama &>/dev/null; then
    echo "  [OK] Ollama gefunden"
elif curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "  [OK] Ollama laeuft bereits"
else
    echo "  [*] Ollama nicht gefunden - installiere..."
    curl -fsSL https://ollama.com/install.sh | sh
    if [ $? -ne 0 ]; then
        echo "  [FEHLER] Ollama Installation fehlgeschlagen."
        echo "  Bitte manuell installieren: https://ollama.com/download"
        exit 1
    fi
    echo "  [OK] Ollama installiert"
fi

# Ollama Server starten falls nicht laeuft
echo "  [*] Modell-Pfad: $OLLAMA_MODELS"
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "  [*] Starte Ollama Server..."
    ollama serve &>/dev/null &
    OLLAMA_PID=$!

    WAIT=0
    while [ $WAIT -lt 30 ]; do
        sleep 1
        WAIT=$((WAIT + 1))
        if curl -s http://localhost:11434/api/tags &>/dev/null; then
            echo "  [OK] Ollama Server laeuft"
            break
        fi
    done

    if [ $WAIT -ge 30 ]; then
        echo "  [!] Ollama Server startet nicht - starte App trotzdem..."
    fi
fi

# ============================================
# Schritt 3: Virtual Environment + Dependencies
# ============================================
echo "[3/5] Pruefe Dependencies..."

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

if ! "$VPYTHON" -c "import PyQt6" &>/dev/null; then
    echo "  [*] Installiere Pakete (PyQt6, requests)..."
    "$VPYTHON" -m pip install --upgrade pip --quiet 2>/dev/null
    "$VPYTHON" -m pip install PyQt6 requests
    if [ $? -ne 0 ]; then
        echo "  [FEHLER] Paketinstallation fehlgeschlagen!"
        exit 1
    fi
    echo "  [OK] Pakete installiert"
else
    echo "  [OK] Alle Pakete vorhanden"
fi

# ============================================
# Schritt 4: KI-Modell pruefen
# ============================================
echo "[4/5] Pruefe KI-Modell..."

if ollama list 2>/dev/null | grep -qi "qwen2.5-coder:32b"; then
    echo "  [OK] $DEFAULT_MODEL ist vorhanden"
else
    echo ""
    echo "  ========================================"
    echo "  Das Standard-Modell $DEFAULT_MODEL"
    echo "  ist noch nicht heruntergeladen."
    echo "  Download-Groesse: ca. 20 GB"
    echo "  ========================================"
    echo ""
    read -p "  Druecke Enter um den Download zu starten (Ctrl+C zum Abbrechen)... "
    echo ""
    echo "  [*] Lade $DEFAULT_MODEL herunter..."
    echo "  [*] Das kann je nach Leitung dauern..."
    echo ""
    ollama pull "$DEFAULT_MODEL" || {
        echo "  [!] Download fehlgeschlagen - du kannst das Modell spaeter in der App laden."
    }
    echo "  [OK] $DEFAULT_MODEL bereit!"
fi

# ============================================
# Schritt 5: App starten
# ============================================
echo "[5/5] Starte KI Chat..."
echo ""
echo "  ========================================"
echo "    App startet... Viel Spass!"
echo "  ========================================"
echo ""

cd "$SCRIPT_DIR"
"$VPYTHON" "$SCRIPT_DIR/main.py"
