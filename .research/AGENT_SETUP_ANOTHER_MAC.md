# word-lookup — Komplett-Setup auf einem neuen Mac (für KI-Agenten)

Dieses Dokument richtet sich an **automatisierte Agenten** und Menschen, die das Projekt **frisch klonen** und **ohne Rätselraten** installieren sollen. Alle Befehle von der **Repository-Wurzel** (`word-lookup/`) ausführen, sofern nicht anders vermerkt.

## 0. Was dieses Projekt braucht

| Komponente | Pflicht? | Zweck |
|------------|----------|--------|
| **Python 3** (3.10 oder neuer) | ja | `scripts/word_lookup.py`, MCP-Server, Hilfsskripte |
| **Virtuelle Umgebung** `.venv` | dringend empfohlen | isolierte Pakete |
| **pip-Pakete** (siehe unten) | ja | `requests`, `beautifulsoup4`, `mcp`, `mammoth` |
| **agent-browser** (Homebrew) | optional | FWB-**Browser-Fallback** und `scripts/fwb_agent_browser.py` |
| **API-Schlüssel** | nein | Alle Quellen sind öffentlich (HTTP/API), keine `.env` nötig |

**Layout:** In der Wurzel liegen u. a. `README.md`, `AGENTS.md`, `recherche_verlauf.md`. **Python-Code** liegt in **`scripts/`** (z. B. `word_lookup.py`, `server.py`).

---

## 1. Repository holen

```bash
git clone <REPO-URL> word-lookup
cd word-lookup
```

Optional: Branch wechseln, falls vereinbart (z. B. `main`).

---

## 2. Python prüfen

```bash
python3 --version
# Erwartet: 3.10.x oder höher
```

Auf dem Mac ist `python3` in der Regel über Xcode Command Line Tools, Homebrew oder python.org verfügbar. Fehlt `python3`, zuerst installieren, dann fortfahren.

---

## 3. Virtuelle Umgebung anlegen und aktivieren

```bash
cd /PFAD/zum/word-lookup
python3 -m venv .venv
source .venv/bin/activate
```

Aktivieren bei jedem neuen Terminal wiederholen (`source .venv/bin/activate`), oder in Befehlen **immer** den vollen Interpreter nutzen: `.venv/bin/python3` (dann muss `activate` nicht jeder Session).

---

## 4. Abhängigkeiten installieren

```bash
pip install --upgrade pip
pip install requests beautifulsoup4 mcp mammoth
```

**Warum:** `word_lookup` und `server` brauchen `requests` und `beautifulsoup4`. Der MCP-Server braucht `mcp`. `docx_to_md` / MCP-Tool `docx_to_markdown` braucht `mammoth`.

**Kontrolle (optional):**

```bash
python3 -c "import requests, bs4, mcp, mammoth; print('imports OK')"
```

---

## 5. Installation verifizieren (Smoke-Test)

Von der **Repository-Wurzel** (nicht in `cd scripts` nötig):

```bash
python3 scripts/word_lookup.py --list-sources
```

Erwartung: saubere Ausgabe, kein Traceback. Anschließend:

```bash
python3 scripts/word_lookup.py minne --json
```

Erwartung: JSON mit `best_definition` und `sources` (mindestens eine Quelle mit `success: true` — je nach Netz und Rate-Limits).

`recherche_verlauf.md` wird beim ersten sinnvollen Lookup **in der Wurzel** erzeugt bzw. angehängt.

---

## 6. Optional: agent-browser (FWB im echten Browser)

Detaillierte, **repo-lokale** Anweisung (macOS, Pfade, wann FWB, Konflikte): **`.research/SKILL_AGENT_BROWSER.md`**

Für `fetch_fwb` (FWB-online) **falls** der reine HTTP-Abrag fehlschlägt oder JS-Platzhalter liefert, und für den **manuellen** Aufruf:

```bash
brew install agent-browser
agent-browser install   # einmalig, installiert/aktualisiert die Browser-Engine
```

Test nur FWB per Browser-CLI (optional):

```bash
python3 scripts/fwb_agent_browser.py haus
```

Erwartung: JSON mit `"success": true` und Artikeltext-Fragment. Dauer typischerweise **10–30 Sekunden**.

Wenn `agent-browser` fehlt, funktionieren `word_lookup` und die übrigen Quellen **trotzdem**; nur FWB-Browser-Fallback entfällt (siehe `AGENTS.md`).

---

## 7. MCP-Server (Cursor, OpenCode, etc.)

**Start (stdio, blockierend):**

```bash
python3 scripts/server.py
```

**Konfiguration:** Zwei Pfade **absolut** setzen: Interpreter aus `.venv` **und** `server.py` unter `scripts/`.

```json
"word-dict": {
  "type": "local",
  "command": [
    "/ABSOLUTER/PFAD/zum/word-lookup/.venv/bin/python",
    "/ABSOLUTER/PFAD/zum/word-lookup/scripts/server.py"
  ],
  "enabled": true
}
```

**OpenCode / Bash-Permissions:** Beispiel liegt im Repo: `opencode.json` in der **Repository-Wurzel** (Schema `opencode.ai`, Subagent `kinderbuch-evaluator`). Pfade in der lokalen OpenCode-Config ggf. anpassen, nicht blind kopieren, wenn dein Config-Format abweicht.

**Tools des Servers:** `lookup_word`, `docx_to_markdown` — Beschreibung in `scripts/server.py`, Prompt-Texte in `scripts/AGENT_PROMPT.md` und in `AGENTS.md` (Kontext „Kinderbuch-Workflow“).

---

## 8. Nützliche Befehle (Kurzreferenz)

| Aktion | Befehl (von der Wurzel) |
|--------|-------------------------|
| Lookup mit JSON | `python3 scripts/word_lookup.py <Wort> --json` |
| Nur bestimmte Quellen | `python3 scripts/word_lookup.py <Wort> --sources wiktionary,wbnetz_dwb --json` |
| DOCX → Markdown | `python3 scripts/docx_to_md.py datei.docx` |
| MCP-Server | `python3 scripts/server.py` |
| FWB nur Browser | `python3 scripts/fwb_agent_browser.py <Lemma>` |

---

## 9. Netzwerk und Stabilität (Agenten: nicht als Bug werten)

- **Wiktionary:** Zu viele Anfragen in kurzer Zeit → gelegentlich **HTTP 403** (Rate/Robot). Pausen zwischen Lookups.
- **Wörterbuchnetz AWB:** Manchmal **502 Proxy Error** — **serverseitig**; später erneut versuchen, anderes Lemma testen.
- **OpenThesaurus:** Bei seltenen Wörtern: keine Synonyme → `success: false` — normal.

Keine harten Garantien „alle 9 Quellen grün pro Wort“.

---

## 10. Was **nicht** ins Repo gehört (Hinweis)

- **`.venv/`** — lokal neu anlegen; nicht einchecken (üblich: `.gitignore` enthält `.venv/`).
- **`__pycache__/`** — nicht einchecken.
- **Keine** `.env` für die Standard-Pipeline nötig (kein erzwungenes Geheimnis).

---

## 11. Checkliste für den Agenten (Copy-paste-Logik)

1. [ ] `cd` in die geklonte Wurzel `word-lookup/`
2. [ ] `python3 -m venv .venv` und `source .venv/bin/activate` **oder** `.venv/bin/python3` nutzen
3. [ ] `pip install requests beautifulsoup4 mcp mammoth`
4. [ ] `python3 scripts/word_lookup.py --list-sources` — ohne Fehler
5. [ ] `python3 scripts/word_lookup.py minne --json` — JSON mit `best_definition`
6. [ ] (optional) `brew install agent-browser && agent-browser install` dann `python3 scripts/fwb_agent_browser.py haus`
7. [ ] (optional) MCP-Config mit **absoluten** Pfaden zu `.venv/bin/python` und `scripts/server.py`

Wenn die Schritte 4–5 grün sind, ist die **gesamte Kern-Pipeline** auf dem neuen Mac einsatzbereit.

---

## 12. Verweise im Repo

- Nutzer-Doku: `README.md`
- Agent-Referenz inkl. Kinderbuch-Pipeline: `AGENTS.md`
- System-Prompt (MCP): `scripts/AGENT_PROMPT.md`

*Stand: für „anderen Mac“ und CI-ähnliche Reproduzierbarkeit gedacht; Pfade stets an die lokale Maschine anpassen.*
