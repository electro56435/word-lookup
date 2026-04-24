# Handoff — 2026-04-24 17:29

## Summary

`word-lookup` ist ein CLI-Tool für historische deutsche Wörterbuch-Lookups. In dieser Session wurde eine "Kinderbuch-Modernisierungs-Pipeline" konzipiert und konfiguriert: OpenCode (Desktop-App) soll als Agent archaische Wörter aus alten Kinderbüchern nachschlagen und kindgerechte Ersatzwörter generieren. Konfigurationsdateien wurden angelegt bzw. aktualisiert, aber die Pipeline wurde noch nicht in OpenCode getestet.

## Session Type
implementation

## Task

User hat gesagt:
- 'Die Pipeline wurde falsch verstanden. OpenCode ist der Agent, der lookup_word aufruft und dann selbst die Modernisierung generiert. Kein Python-LLM-Call. Kein MCP — nur CLI.' — Kontext: nach einer falschen Research-Brief-Auswertung, die Python + Anthropic SDK als Architektur vorgeschlagen hatte.
- 'die recherche dokument muss einfach und klar aufgebaut sein sehr verständlich' — Kontext: nach dem Anlegen von opencode.json und AGENTS.md
- 'sehr klar stuktier mit dem 1 dem wort das recherchiert wurde und die erklrung des wortes und dann der vorschlag für ein neues wort oder satz wie auch eigentlich im pipeline chat output definiert' — Kontext: beim Formatieren von `recherche_verlauf.md`

Ziel: OpenCode Desktop als Pipeline-Agent konfigurieren, der (1) `python word_lookup.py <wort> --json` aufruft, (2) Definition aus JSON liest, (3) modernes kindgerechtes Ersatzwort + Erklärung generiert und (4) Ergebnis in `recherche_verlauf.md` loggt.

## Status

- **Done:**
  - `AGENTS.md` — Workflow-Sektion "Kinderbuch-Modernisierung" hinzugefügt (Modus A: Einzelwort, Modus B: Textblock mit Auto-Erkennung, Log-Anweisung für OpenCode)
  - `opencode.json` — neu erstellt mit `"python word_lookup*": "allow"` für bash-Permissions
  - `word_lookup.py` — `save_to_history()` neu formatiert: schreibt `**Definition:**` + `**Quelle:**`, keine leeren Einträge, kein `---` am Ende (OpenCode hängt Ersatz + `---` an)
  - `recherche_verlauf.md` — neu geschrieben im sauberen Format, leere Test-Einträge entfernt
  - Research-Briefs: opencode-desktop-app (evaluiert), modernize-pipeline-structure (evaluiert, dann als irrelevant eingestuft da kein Python LLM)

- **In progress:** nichts aktiv — Session endet hier

## Git State

- Branch: `main`
- Uncommitted changes: `AGENTS.md`, `word_lookup.py`, `recherche_verlauf.md`
- Untracked: `opencode.json`, `.research/2026-04-24_16-43-54_opencode-desktop-app.md`, `.research/2026-04-24_16-31-17_modernize-pipeline-structure.md`, `.research/2026-04-24_16-28-00_fwb-api-and-awb-status.md`
- Commits this session: none

## Key Files

- `AGENTS.md` — Haupt-Agentenkonfiguration; enthält Kinderbuch-Workflow + Log-Anweisung
- `AGENT_PROMPT.md` — alter System-Prompt (MCP-orientiert, strikt faktenbasiert); noch nicht auf OpenCode-CLI-Workflow angepasst
- `word_lookup.py` — CLI + Python-Modul; `save_to_history()` ab Zeile 346 (aktualisiert)
- `opencode.json` — OpenCode-Konfiguration (bash-Permissions)
- `recherche_verlauf.md` — Recherche-Log; Format: Wort / Definition / Quelle (von Python) + Ersatzwort / Erklärung / `---` (von OpenCode)
- `server.py` — MCP-Server; in dieser Session nicht angefasst

## What Was Tried

- Research Brief für Python-Pipeline-Architektur erstellt → evaluiert → als falsch eingestuft (OpenCode ist Agent, kein Python LLM)
- Research Brief für OpenCode Desktop erstellt + evaluiert → Ergebnis: `AGENTS.md` + `bash`-Tool + `opencode.json`
- `AGENTS.md` um Kinderbuch-Workflow erweitert
- `opencode.json` erstellt
- `save_to_history()` in `word_lookup.py` neu formatiert (dreimal iteriert wegen User-Feedback zum Format)
- `recherche_verlauf.md` zweimal neu geschrieben (zweimal Format-Feedback vom User)

## Test / Build Status

- Tests: not run
- Build: nicht zutreffend (Python-Script, kein Build)
- Known failures: Pipeline noch nicht in OpenCode getestet

## What's Next

1. [USER] OpenCode Desktop öffnen, Projekt-Verzeichnis öffnen → prüfen ob `AGENTS.md` automatisch geladen wird
2. [BLOCKED: 1] Test: "modernisiere: Minne" eingeben → prüfen ob OpenCode `word_lookup.py` via bash aufruft
3. [BLOCKED: 2] Prüfen ob OpenCode `recherche_verlauf.md` korrekt mit `**Ersatzwort:**` + `**Erklärung:**` + `---` beschreibt
4. [AGENT] `AGENT_PROMPT.md` überarbeiten — aktuell noch MCP-orientiert und strikt faktenbasiert; für den neuen Kinderbuch-Use-Case nicht mehr passend (oder als separaten Prompt für MCP-only-Nutzung stehen lassen und in `AGENTS.md` klarstellen)
5. [AGENT] `git add` + commit für alle geänderten Dateien (AGENTS.md, word_lookup.py, recherche_verlauf.md, opencode.json)

## Resume

Read this file completely before taking any action.

**First action:** Item 4 (AGENT_PROMPT.md überprüfen und entscheiden ob anpassen oder stehen lassen) — dann User bitten, Items 1–3 in OpenCode zu testen.

Then paste this as your first message:

> "Continue from handoff: .handoff/2026-04-24-17-29-opencode-kinderbuch-pipeline.md"
