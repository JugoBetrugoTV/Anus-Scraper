#!/bin/bash
echo "============================================"
echo "  PreisHai - Build Script"
echo "============================================"
echo ""

echo "[1/3] Installiere Abhängigkeiten..."
pip install -r requirements.txt || { echo "FEHLER beim Installieren!"; exit 1; }

echo ""
echo "[2/3] Erstelle Executable..."
pyinstaller --noconfirm --onefile --windowed \
    --name "PreisHai" \
    --add-data "app:app" \
    main.py || { echo "FEHLER beim Erstellen!"; exit 1; }

echo ""
echo "[3/3] Fertig!"
echo ""
echo "============================================"
echo "  Die Datei befindet sich in: dist/PreisHai"
echo "============================================"
