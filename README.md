# PreisHai - Europäischer Preisvergleich

Preisvergleichs-Tool ähnlich wie Geizhals.de und Idealo. Durchsucht Google Shopping nach den günstigsten Angeboten in Europa und zeigt die 20 besten Ergebnisse an.

## Features

- **Produktsuche** über Google Shopping in mehreren EU-Ländern
- **20 günstigste Händler** pro Suche (große und kleine Shops)
- **Filter**: Land, Sortierung, Zustand (Neu/Gebraucht), Preisbereich
- **Doppelklick** auf ein Ergebnis öffnet die Händlerseite im Browser
- **Dark Mode** UI mit modernem Design
- **Als .exe ausführbar** (Windows) oder als Python-Script

## Installation & Start

### Option 1: Python direkt starten

```bash
pip install -r requirements.txt
python main.py
```

### Option 2: Als .exe bauen (Windows)

```bash
build.bat
```

Die fertige `PreisHai.exe` liegt dann in `dist/`.

### Option 3: Auf Linux/Mac bauen

```bash
chmod +x build.sh
./build.sh
```

## Voraussetzungen

- Python 3.10+
- Internetverbindung

## Benutzung

1. Suchbegriff eingeben (z.B. "RTX 4090", "iPhone 15 Pro")
2. Optional: Filter setzen (Land, Preisbereich, Sortierung, Zustand)
3. Auf "Suchen" klicken
4. Ergebnisse werden in einer Tabelle angezeigt
5. Doppelklick auf eine Zeile öffnet den Shop im Browser

## Hinweise

- Das Tool durchsucht Google Shopping und extrahiert Preise von großen und kleinen Händlern
- Alle Preise sind in Euro (€)
- Bei zu vielen Anfragen kann Google temporär blockieren — einfach kurz warten
