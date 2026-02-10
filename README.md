# Unzensierter KI Chat

Ein lokaler KI-Chatbot ohne Einschraenkungen, powered by [Ollama](https://ollama.com). Apple-inspiriertes Dark Mode Design.

## Features

- **Keine Zensur** - Lokale LLMs via Ollama, komplett offline und privat
- **Apple Dark Mode Design** - Elegantes UI mit iMessage-Style Bubbles
- **Streaming** - Antworten werden Token fuer Token in Echtzeit angezeigt
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

## Installation (Einfach)

### Windows

```
1. Repository herunterladen (Code > Download ZIP > entpacken)
2. start.bat doppelklicken
3. Fertig!
```

### Linux / macOS

```bash
git clone https://github.com/JugoBetrugoTV/Anus-Scraper.git
cd Anus-Scraper
chmod +x start.sh
./start.sh
```

**Das war's.** Die Launcher-Scripts machen automatisch alles:
- Python pruefen (und installieren falls noetig)
- Virtuelle Umgebung erstellen
- Alle Pakete (PyQt6, requests) installieren
- App starten

Beim ersten Start richtet die App dann auch **Ollama** automatisch ein:
- Ollama installieren
- Server starten
- Standard-Modell herunterladen

---

## Manuelle Installation (falls noetig)

Falls die automatische Installation nicht klappt:

```bash
# 1. Python 3.11+ installieren (python.org/downloads)
# 2. Pakete installieren
pip install -r requirements.txt

# 3. App starten
python main.py
```

---

## Empfohlene Modelle

| Modell | Groesse | Beschreibung |
|--------|---------|-------------|
| `dolphin-mistral` | ~4GB | Schnell, unzensiert, gut fuer Deutsch |
| `dolphin-llama3` | ~4.7GB | Sehr gut fuer Roleplay |
| `llama3.1` | ~4.7GB | Meta Llama 3.1, starkes Allround-Modell |
| `nous-hermes2` | ~4GB | Guter Allrounder |
| `llava` | ~4.5GB | Kann Bilder verstehen (multimodal) |

---

## Tastenkuerzel

| Taste | Funktion |
|-------|----------|
| `Enter` | Nachricht senden |
| `Shift+Enter` | Neue Zeile |
| `Ctrl+N` | Neuer Chat |
| `Escape` | Streaming stoppen |
| `Ctrl+F` | Chat-Suche |
| `Ctrl+Shift+F` | Globale Suche |
| `Ctrl+E` | Export .txt |
| `Ctrl+Shift+E` | Export .json |
| `Ctrl+Shift+H` | Export .html |
| `Ctrl+Shift+M` | Export .md |
| `Ctrl+D` | Chat duplizieren |
| `Ctrl+I` | Chat importieren |
| `Ctrl+L` | Chat leeren |
| `Ctrl+` / `Ctrl-` | Zoom |
| `F11` | Vollbild |
| `Ctrl+?` | Shortcuts-Hilfe |

---

## Als EXE bauen (optional)

```bash
# Windows
build.bat

# Linux/Mac
chmod +x build.sh && ./build.sh
```

---

## Daten

Alle Daten werden lokal gespeichert:
- **Sessions**: `~/.ki-chat/sessions/`
- **Einstellungen**: `~/.ki-chat/settings.json`
- **Logs**: `~/.ki-chat/logs/`

## Voraussetzungen

- Python 3.11+ (wird automatisch installiert)
- Ollama (wird automatisch installiert)
- ~4-8 GB RAM (je nach Modell)
- ~4-8 GB Festplatte (fuer Modelle)
