# Unzensierter KI Chat

Ein lokaler KI-Chatbot ohne Einschränkungen, powered by [Ollama](https://ollama.com). Apple-inspiriertes Dark Mode Design.

## Features

- **Keine Zensur** - Lokale LLMs via Ollama, komplett offline und privat
- **Apple Dark Mode Design** - Elegantes UI mit iMessage-Style Bubbles
- **Streaming** - Antworten werden Token für Token in Echtzeit angezeigt
- **Mehrere Chat-Sessions** - Mit Ordnern, Pins und Auto-Titel
- **5 Farbthemen** - Blau, Lila, Gruen, Rot, Orange (Apple System Colors)
- **Markdown-Rendering** - Code-Bloecke mit Syntax-Highlight, Tabellen, Listen
- **Bilder senden** - Drag & Drop oder Ctrl+V (fuer multimodale Modelle)
- **Export** - Als .txt, .json, .html oder .md
- **Globale Suche** - Alle Chats durchsuchen (Ctrl+Shift+F)
- **Nachrichten bewerten** - Gute/schlechte Antworten markieren
- **Nachrichten bearbeiten/regenerieren** - Mit Modellauswahl
- **Chat-Statistiken** - Uebersicht ueber alle Sessions
- **System Tray** - Laeuft im Hintergrund
- **Presets** - Vorgefertigte Personas (Unzensiert, Roleplay, Kreativ, Coder)
- **Token-Limit** - Maximale Antwortlaenge einstellbar
- **Vollbild** - F11

---

## Installation

### Schritt 1: Python installieren

**Python 3.11+** wird benoetigt.

- **Windows**: [python.org/downloads](https://www.python.org/downloads/) herunterladen und installieren. Haken bei "Add Python to PATH" setzen!
- **macOS**: `brew install python` oder von [python.org](https://www.python.org/downloads/)
- **Linux**: `sudo apt install python3 python3-pip` (Ubuntu/Debian) oder `sudo pacman -S python` (Arch)

Pruefen ob Python installiert ist:
```bash
python --version
# oder
python3 --version
```

### Schritt 2: Repository klonen

```bash
git clone https://github.com/JugoBetrugoTV/Anus-Scraper.git
cd Anus-Scraper
```

### Schritt 3: Dependencies installieren

```bash
pip install -r requirements.txt
```

Das installiert:
- **PyQt6** - GUI Framework
- **requests** - HTTP Client fuer Ollama API

### Schritt 4: Ollama installieren

Die App nutzt [Ollama](https://ollama.com) als lokale KI-Engine.

- **Windows/macOS**: [ollama.com/download](https://ollama.com/download) herunterladen und installieren
- **Linux**:
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

Oder: Die App hat einen eingebauten Setup-Wizard der Ollama automatisch installiert!

### Schritt 5: App starten

```bash
python main.py
```

Beim ersten Start oeffnet sich der **Setup-Wizard** der dich durch alles fuehrt:
1. Ollama Installation pruefen/starten
2. Server starten
3. Ein Modell herunterladen

---

## Empfohlene Modelle

| Modell | Groesse | Beschreibung |
|--------|---------|-------------|
| `dolphin-mistral` | ~4GB | Schnell, unzensiert, gut fuer Deutsch |
| `dolphin-llama3` | ~4.7GB | Sehr gut fuer Roleplay |
| `llama3.1` | ~4.7GB | Meta Llama 3.1, starkes Allround-Modell |
| `nous-hermes2` | ~4GB | Guter Allrounder |
| `llava` | ~4.5GB | Kann Bilder verstehen (multimodal) |
| `gemma2` | ~5.4GB | Google Gemma 2 |

Modelle herunterladen (im Terminal):
```bash
ollama pull dolphin-mistral
```

Oder direkt in der App ueber den Setup-Wizard / Einstellungen.

---

## Tastenkuerzel

| Taste | Funktion |
|-------|----------|
| `Enter` | Nachricht senden |
| `Shift+Enter` | Neue Zeile |
| `Ctrl+N` | Neuer Chat |
| `Escape` | Streaming stoppen |
| `Ctrl+F` | Chat-Suche (in Session) |
| `Ctrl+Shift+F` | Globale Suche (alle Sessions) |
| `Ctrl+E` | Export als .txt |
| `Ctrl+Shift+E` | Export als .json |
| `Ctrl+Shift+H` | Export als .html |
| `Ctrl+Shift+M` | Export als .md |
| `Ctrl+D` | Chat duplizieren |
| `Ctrl+I` | Chat importieren |
| `Ctrl+L` | Chat leeren |
| `Ctrl+` / `Ctrl-` | Zoom ein/aus |
| `Ctrl+0` | Zoom zuruecksetzen |
| `F11` | Vollbild |
| `Ctrl+?` | Shortcuts-Hilfe |
| `Ctrl+V` | Bild einfuegen |
| `Drag & Drop` | Dateien/Bilder einfuegen |

---

## Als EXE/App bauen (optional)

```bash
# Windows
build.bat

# Linux/Mac
chmod +x build.sh
./build.sh
```

Erstellt eine standalone Executable in `dist/KI-Chat`.

---

## Daten

Alle Daten werden lokal gespeichert unter:
- **Sessions**: `~/.ki-chat/sessions/`
- **Einstellungen**: `~/.ki-chat/settings.json`
- **Logs**: `~/.ki-chat/logs/`

---

## Voraussetzungen

- Python 3.11+
- Ollama (wird beim ersten Start automatisch eingerichtet)
- ~4-8 GB RAM (je nach Modell)
- ~4-8 GB Festplatte (fuer Modelle)
