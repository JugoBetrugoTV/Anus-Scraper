# Unzensierter KI Chat

Ein lokaler KI-Chatbot ohne Einschränkungen, powered by [Ollama](https://ollama.com).

## Features

- **Keine Zensur** - Nutzt lokale LLMs via Ollama, komplett unzensiert
- **Streaming-Antworten** - Tokens werden in Echtzeit angezeigt
- **Dark Theme** - Modernes, dunkles Design
- **Mehrere Chats** - Verschiedene Chat-Sessions parallel
- **Einstellbar** - Modell, System-Prompt, Temperatur konfigurierbar
- **Presets** - Vorgefertigte Personas (Unzensiert, Roleplay, Kreativ)

## Voraussetzungen

1. **Python 3.11+**
2. **Ollama** installieren: https://ollama.com/download

## Installation

```bash
# Dependencies installieren
pip install -r requirements.txt

# Ollama starten (in separatem Terminal)
ollama serve

# Ein unzensiertes Modell herunterladen
ollama pull dolphin-mistral

# App starten
python main.py
```

## Empfohlene Modelle

| Modell | Größe | Beschreibung |
|--------|-------|-------------|
| `dolphin-mistral` | ~4GB | Schnell, unzensiert, gut für Deutsch |
| `dolphin-llama3` | ~4.7GB | Neuer, sehr gut für Roleplay |
| `nous-hermes2` | ~4GB | Guter Allrounder |
| `llama3-uncensored` | ~4.7GB | Meta Llama 3 ohne Filter |

## Tastenkürzel

- **Enter** - Nachricht senden
- **Shift+Enter** - Neue Zeile

## Build (EXE)

```bash
# Windows
build.bat

# Linux/Mac
chmod +x build.sh && ./build.sh
```
