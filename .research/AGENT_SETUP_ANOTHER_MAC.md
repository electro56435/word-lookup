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

## 7. MCP-Server und OpenCode Desktop (macOS)

### 7.1 MCP-Server (Cursor, andere Clients)

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

**Tools des Servers:** `lookup_word`, `docx_to_markdown` — Beschreibung in `scripts/server.py`, Prompt-Texte in `scripts/AGENT_PROMPT.md` und in `AGENTS.md` (Kontext „Kinderbuch-Workflow“).

### 7.2 OpenCode Desktop — Projekt (im Repo, mitziehbar)

Aus der **Git-Wurzel von `word-lookup`** arbeiten (OpenCode lädt Config beim Start nach oben bis zur `.git`).

| Datei / Ordner | Zweck |
|----------------|--------|
| **`opencode.json`** (Wurzel) | `$schema`, `permission.bash` für `python3 scripts/…`, `permission.task`, optional `agent.build` / `agent.plan` mit denselben Task-Regeln |
| **`.opencode/agents/kinderbuch-evaluator.md`** | Subagent `kinderbuch-evaluator` (`mode: subagent`, Prompt per `{file:../../scripts/AGENT_PROMPT.md}`) |

Die genauen Inhalte sind im geklonten Repo gepflegt — **nicht** manuell duplizieren, außer du weißt, was du änderst.

### 7.3 OpenCode Desktop — **globale** macOS-Config (`~/.config/opencode/`)

OpenCode erwartet laut Doku u. a. **`~/.config/opencode/opencode.json`**. Auf manchen Installationen heißt die Datei nur **`config.json`** — beides kann vorkommen. **Empfehlung:** eine Datei als „Quelle der Wahrheit“ nutzen und die andere per Symlink verknüpfen:

```bash
cd ~/.config/opencode
cp config.json config.json.bak-$(date +%Y%m%d)   # vor Änderungen
# Wenn nur config.json existiert:
ln -sf config.json opencode.json
```

**Warum global etwas setzen?** Damit **`permission.task`** für **`kinderbuch-evaluator`** (und ggf. `general` / `explore`) auch dann greift, wenn die Projekt-Config allein nicht ausreicht oder globale Defaults Tasks blockieren. Anschließend **OpenCode komplett beenden und neu starten**.

**Minimal-Block zum Einfügen** (in die bestehende JSON einbauen, Struktur anpassen — kein zweites Root-`{}`):

```json
  "permission": {
    "task": {
      "*": "ask",
      "general": "allow",
      "explore": "allow",
      "kinderbuch-evaluator": "allow"
    }
  },
  "agent": {
    "build": {
      "permission": {
        "task": {
          "*": "ask",
          "general": "allow",
          "explore": "allow",
          "kinderbuch-evaluator": "allow"
        }
      }
    },
    "plan": {
      "permission": {
        "task": {
          "*": "ask",
          "general": "allow",
          "explore": "allow",
          "kinderbuch-evaluator": "allow"
        }
      }
    }
  }
```

- **`"*": "ask"` zuerst**, dann die **`allow`**-Einträge — letzte passende Regel gewinnt (siehe OpenCode-Doku zu Permissions).
- Eigene Plugins / MCP-Einträge in derselben Datei **beibehalten**; nur die neuen Keys ergänzen.

### 7.4 Wenn Task / Subagent mit Zod scheitert (`must start with "ses"` oder `"prt"`)

Das ist **keine** Bash-Permission, sondern **interne ID-Validierung** (Session- bzw. Message-IDs). Kurzablauf:

1. OpenCode **aktualisieren** (Stable).
2. **`opencode-supermemory`** (und ähnliche Plugins, die `chat.message` hooken): **deaktualisieren, entfernen oder auf Fix-Version** — siehe https://github.com/anomalyco/opencode/issues/18211 und https://github.com/supermemoryai/opencode-supermemory/issues/29  
3. **Plugins testweise leer** (`"plugin": []`), neu starten, Task erneut testen; bei Erfolg Plugins einzeln wieder zuschalten.
4. **`task_id`** beim Task-Tool **nur** setzen, wenn eine vorherige Subagent-Session **fortgesetzt** wird (exakte `ses…`-ID von OpenCode); sonst **weglassen**. Der Kinderbuch-**Handoff** gehört in **`prompt`**, nicht in ID-Felder.
5. Freie Modelle (z. B. Qwen über OpenCode Zen): können in Subagent-Kontexten **fehlerhafte IDs** erzeugen — zum **Isolieren** ein anderes Modell testen.
6. Immer noch blockiert: **`AGENTS.md`** — Pipeline-**Fallback** ohne Task (`scripts/AGENT_PROMPT.md` im gleichen Lauf auf den Handoff-Block anwenden).

Details und Checkliste: **`AGENTS.md`** (Abschnitt Kinderbuch + Zod). Task-Schema im Upstream: https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/tool/task.ts

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
8. [ ] (optional, OpenCode Desktop) Projekt aus **Git-Wurzel** öffnen; globale `~/.config/opencode/config.json` bzw. `opencode.json` um **`permission.task`** + **`agent.build`/`plan`** ergänzen (§7.3); bei Bedarf `ln -sf config.json opencode.json`; OpenCode **neu starten**
9. [ ] (optional) Kinderbuch-Pipeline: Task → `kinderbuch-evaluator` testen; bei Zod-Fehlern §7.4 befolgen

Wenn die Schritte 4–5 grün sind, ist die **gesamte Kern-Pipeline** auf dem neuen Mac einsatzbereit. Schritt 8–9 betreffen nur die **OpenCode-Kinderbuch-Integration**.

---

## 12. Verweise im Repo

- Nutzer-Doku: `README.md`
- Agent-Referenz inkl. Kinderbuch-Pipeline, Permissions, Zod-Fehler: `AGENTS.md`
- System-Prompt (Evaluator / MCP): `scripts/AGENT_PROMPT.md`
- OpenCode-Projektconfig: `opencode.json`, `.opencode/agents/kinderbuch-evaluator.md`

*Stand: für „anderen Mac“ und CI-ähnliche Reproduzierbarkeit gedacht; Pfade stets an die lokale Maschine anpassen.*
