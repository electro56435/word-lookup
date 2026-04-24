# Wort-Lookup

CLI und MCP-Server zum Nachschlagen historischer und archaischer deutscher Wörter. Das Skript fragt bis zu neun Quellen gleichzeitig ab und wählt automatisch die beste Definition aus.

**Projektlayout:** In der Wurzel liegen u. a. diese Anleitung, `AGENTS.md`, `CLAUDE.md`, `recherche_verlauf.md`, **`opencode.json`** und **`.opencode/agents/`** (OpenCode-Subagent Kinderbuch-Evaluator). Der **Code** (Python, `AGENT_PROMPT.md`) liegt in **`scripts/`**.

## Was macht das Skript?

Du gibst ein Wort ein. Das Skript fragt alle verfügbaren Quellen parallel ab, bewertet die Ergebnisse nach Länge und Qualität — mit 1,5-fachem Bonus für historische Wörterbücher — und gibt die beste Definition zurück. Das Ergebnis wird außerdem automatisch in `recherche_verlauf.md` (Wurzelverzeichnis) gespeichert.

## Quellen

| Quelle | Inhalt | Epoche |
|--------|--------|--------|
| **DWB** (Grimm) | Vollartikel aus Grimms Deutschem Wörterbuch | 16.–19. Jh. |
| **Adelung** | Grammatisch-kritisches Wörterbuch | 18. Jh. |
| **AWB** | Althochdeutsches Wörterbuch | 8.–11. Jh. |
| **Lexer** | Mittelhochdeutsches Handwörterbuch | 12.–15. Jh. |
| **BMZ** | Benecke-Müller-Zarncke (Mittelhochdeutsch) | 12.–15. Jh. |
| **FWB** | Frühneuhochdeutsches Wörterbuch | 14.–17. Jh. |
| **DWDS** | Definitionen, Wortart, Etymologie | modern + historisch |
| **Wiktionary DE** | Bedeutungen, Etymologie | alle Epochen |
| **OpenThesaurus** | Synonyme | modern |

Die fünf historischen Wörterbücher (DWB, Adelung, AWB, Lexer, BMZ) werden über die Wörterbuchnetz-API abgefragt. Das Skript rekonstruiert den Artikeltext aus sogenannten KWIC-Fenstern — komplett ohne Browser und ohne Webscraping des JavaScript-Portals.

## Installation

Im Projektverzeichnis (Wurzel):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 mcp mammoth
```

## Benutzung

Alle Beispiele von der **Repository-Wurzel** aus (nicht im Ordner `scripts/` wechseln, außer du passt Pfade an).

### Einfacher Aufruf

```bash
python3 scripts/word_lookup.py Waldhorn
```

### JSON-Ausgabe (für Skripte und Agenten)

```bash
python3 scripts/word_lookup.py grollen --json
```

### Ergebnis in Datei speichern

```bash
python3 scripts/word_lookup.py minne --output ergebnis.json
```

### Nur bestimmte Quellen abfragen

```bash
python3 scripts/word_lookup.py Haus --sources wiktionary,wbnetz_dwb --json
```

### Alle verfügbaren Quellen anzeigen

```bash
python3 scripts/word_lookup.py --list-sources
```

## Ausgabe

Das Ergebnis ist ein JSON-Objekt. Das wichtigste Feld ist `best_definition.definition` — dort steht die längste, reichste Definition aus allen erfolgreichen Quellen.

```json
{
  "word": "Waldhorn",
  "timestamp": "2026-04-24 16:12:38",
  "best_definition": {
    "source": "wbnetz_dwb",
    "definition": "waldhorn , n. 1) das ursprünglich auf der jagd gebrauchte gewundene blasinstrument ...",
    "score": 1332.0
  },
  "summary": "Gefunden in 4 Quellen. Beste Quelle: wbnetz_dwb",
  "sources": {
    "wbnetz_dwb":    { "success": true,  "definitions": ["..."], "etymology": "" },
    "wbnetz_adelung": { "success": true,  "definitions": ["..."], "etymology": "" },
    "dwds":          { "success": true,  "definitions": ["..."], "word_class": "Substantiv" },
    "openthesaurus": { "success": false, "error": "Keine Synonyme gefunden" }
  }
}
```

## Recherche-Verlauf

Jede Suche wird automatisch in `recherche_verlauf.md` im **Repository-Wurzelverzeichnis** angehängt — mit Timestamp, Wort, bester Definition und Quelle. Die Datei entsteht beim ersten Aufruf automatisch.

## DOCX zu Markdown

```bash
python3 scripts/docx_to_md.py dokument.docx
python3 scripts/docx_to_md.py dokument.docx --output ausgabe.md
```

## MCP-Server

```bash
python3 scripts/server.py
```

Stellt zwei MCP-Tools bereit:

- `lookup_word` — Wort nachschlagen, gibt JSON zurück
- `docx_to_markdown` — Word-Datei in Markdown umwandeln

Eintrag in die MCP-Konfiguration (z. B. für OpenCode) — Pfade an deine Umgebung anpassen:

```json
"word-dict": {
  "type": "local",
  "command": ["/absoluter/pfad/.venv/bin/python", "/absoluter/pfad/zum/projekt/scripts/server.py"],
  "enabled": true
}
```

Den System-Prompt für Agenten, die dieses Tool verwenden, findest du in `scripts/AGENT_PROMPT.md`.
