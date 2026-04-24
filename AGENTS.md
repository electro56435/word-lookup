# word-lookup — Agent Reference

CLI und MCP-Server zum Nachschlagen deutscher Wörter aus bis zu neun Quellen parallel.

**Layout:** Quellcode und Hilfsskripte liegen in **`scripts/`** (z. B. `word_lookup.py`, `server.py`, `AGENT_PROMPT.md`). **OpenCode:** `opencode.json` in der **Repository-Wurzel** plus Subagent **`/.opencode/agents/kinderbuch-evaluator.md`** (wird nach der JSON-Config geladen). In der Wurzel u. a. `README.md`, `AGENTS.md`, `CLAUDE.md`, `recherche_verlauf.md`.

---

## 1. Technische Referenz

### CLI-Nutzung

```bash
python3 scripts/word_lookup.py <wort> --json
python3 scripts/word_lookup.py --list-sources
python3 scripts/word_lookup.py minne --sources wbnetz_lexer,wbnetz_bmz --json
```

### Python-Aufruf

```python
import subprocess, json

def lookup_word(word: str, sources: list[str] | None = None) -> dict:
    cmd = ["python3", "scripts/word_lookup.py", word, "--json"]
    if sources:
        cmd += ["--sources", ",".join(sources)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if result.returncode == 0:
        return json.loads(result.stdout)
    return {"error": result.stderr}
```

### Output-Felder

| Feld | Inhalt | Empfehlung |
|------|--------|------------|
| `best_definition.definition` | Reichste Definition aus allen Quellen | **Zuerst verwenden** |
| `best_definition.source` | Quell-Key (z.B. `wbnetz_dwb`) | In Zitaten angeben |
| `best_definition.score` | Qualitätsscore (Länge × Quell-Bonus) | Konfidenzschätzung |
| `summary` | Lesbare Trefferzusammenfassung | Schnell-Plausibilität |
| `sources.<key>.definitions` | Rohdefinitionen je Quelle | Tiefenanalyse |
| `sources.openthesaurus.definitions` | Kommagetrennte Synonyme | Synonymsuche |

Wörterbuchnetz-Quellen erhalten einen **1,5×-Qualitätsbonus** und liefern rekonstruierte Vollartikel aus historischen Wörterbüchern. Wiktionary: 1,2×. Alle anderen: 1,0×.

### Verfügbare Quellen

| Key | Wörterbuch | Epoche |
|-----|-----------|--------|
| `wbnetz_dwb` | Deutsches Wörterbuch (Grimm) | 16.–19. Jh. |
| `wbnetz_adelung` | Adelung | 18. Jh. |
| `wbnetz_awb` | Althochdeutsches Wörterbuch | 8.–11. Jh. |
| `wbnetz_lexer` | Lexer (Mittelhochdeutsch) | 12.–15. Jh. |
| `wbnetz_bmz` | Benecke-Müller-Zarncke (Mittelhochdeutsch) | 12.–15. Jh. |
| `fwb` | Frühneuhochdeutsches Wörterbuch | 14.–17. Jh. |
| `dwds` | DWDS | Modern + historisch |
| `wiktionary` | Wiktionary DE | Alle Epochen, Etymologie |
| `openthesaurus` | OpenThesaurus | Synonyme (modern) |

Wörterbuchnetz-Quellen (`wbnetz_*`) erscheinen nur im Ergebnis, wenn die Meta-API einen Eintrag für das Wort kennt. `--sources wbnetz_*` hat keinen Effekt, wenn das Wort nicht indexiert ist.

### Fehlerbehandlung

```python
data = lookup_word("grollen")
best = data.get("best_definition", {})

if not best.get("definition"):
    # Kein Treffer — score ist 0, source ist "none"
    print("Kein Ergebnis gefunden.")
else:
    print(best["definition"])
    print(f"Quelle: {best['source']} (Score: {best['score']})")
```

### HTML-Scraping vs. strukturierte APIs

**DWDS** und **FWB-online** parsen statisches HTML. Vor der Textextraktion entfernt `scripts/word_lookup.py` `script`-, `noscript`- und `style`-Tags, damit typische Meldungen wie „JavaScript aktivieren“ nicht in `definitions` landen (früher: musste ein Modell das ignorieren). **Wiktionary** (MediaWiki-API), **OpenThesaurus** (JSON) und **Wörterbuchnetz** (JSON + KWIC) liefern keinen solchen Browser-Boilerplate.

**FWB Browser-Fallback:** Schlägt die HTTP-Suche/Lemma-Seite fehl, ist der Inhalt leer/kurz oder sieht aus wie ein JS-Platzhalter, versucht `fetch_fwb` automatisch `scripts/fwb_agent_browser.py` (CLI `agent-browser`, muss im PATH liegen: `brew install agent-browser`, ggf. `agent-browser install`). Erfolg: `fetched_via: "agent-browser"` in der FWB-Quelle. Wenn beides scheitert: ursprüngliches HTTP-Ergebnis plus `fwb_browser_fallback` (Detailobjekt) oder `fwb_browser_unavailable` (ohne installierten `agent-browser`). Manuell: `python3 scripts/fwb_agent_browser.py <lemma>`.

### Live-APIs (Rate-Limits, Serverfehler)

Bei Integrationstests oder vielen Lookups nacheinander:

- **Wiktionary:** Häufige Anfragen in kurzer Zeit können **HTTP 403** auslösen (Robot Policy). Zwischen Aufrufen Abstand lassen; nicht viele einzelne Lookups in einem Burst ausführen.
- **Wörterbuchnetz AWB:** Die Open-API kann gelegentlich **502 (Proxy Error)** liefern — **serverseitig**, später erneut versuchen. Andere Sigles (DWB, Lexer, …) sind oft unabhängig verfügbar.

### Recherche-Log

Jeder Lookup wird automatisch in `recherche_verlauf.md` gespeichert (Zeitstempel, Wort, beste Definition, Quelle). Datei wird beim ersten Aufruf angelegt.

### MCP-Server

`scripts/server.py` stellt `lookup_word` als MCP-Tool bereit — kein CLI-Aufruf nötig.

```json
"word-dict": {
  "type": "local",
  "command": ["/path/to/.venv/bin/python", "/path/to/projekt/scripts/server.py"],
  "enabled": true
}
```

System-Prompt-Template für Agenten: siehe `scripts/AGENT_PROMPT.md`.

---

## 2. Kinderbuch-Modernisierung — Workflow

**Zweck:** Jedes deutsche Wort kindgerecht erklären und ein einfaches Ersatzwort vorschlagen.

**Grundregel: Niemals ablehnen.** Nicht prüfen, ob ein Wort archaisch, veraltet oder selten genug ist. Auch moderne Wörter können für Kinder unbekannt sein (z.B. „Kajüte", „Münze", „Fechten"). Sofort loslegen — kein Kommentieren, kein Nachfragen.

**Altersgruppe:** Standard **Grundschule (6–9 Jahre)** — sehr einfache, direkte Sprache, keine Fremdwörter. Kann per Nutzernachricht überschrieben werden (z.B. „für 10–12-Jährige").

**Zwei Rollen (konzeptionell):**
- **Orchestrator:** Pipeline + Web-Recherche, dann sichtbarer Handoff-Block (Schritt 3).
- **Kinderbuch-Evaluator:** kindgerechte Ausgabe nur aus dem Block — Prompt: `scripts/AGENT_PROMPT.md`.

**OpenCode:** Wenn das **Task-Tool** den Subagenten **`kinderbuch-evaluator`** anbietet (definiert in **`.opencode/agents/kinderbuch-evaluator.md`**, Task-Rechte in **`opencode.json`**): nach dem Handoff-Block **Task** ausführen, Task-Text = kompletter Block. Antwort des Subagenten ungekürzt ausgeben.

**Pflicht — Fallback ohne Subagent (z. B. Cursor, OpenCode ohne geladenes `opencode.json`, Task-Liste ohne `kinderbuch-evaluator`):** Der Subagent ist in dieser Umgebung **nicht spawnbar**. Das ist **kein Grund zum Abbruch**. Unmittelbar nach dem Handoff-Block: die Regeln aus **`scripts/AGENT_PROMPT.md`** auf genau diesen Block anwenden und die Ausgabe **im dort festgelegten Format** (`**Ersatzwort:**` …) in **derselben Antwort** liefern. **Verboten:** Texte wie „Subagent nicht verfügbar“, „nicht verfügbar in der aktuellen Session“ oder nur Rohdaten ohne kindgerechte Ausgabe — die Pipeline gilt erst mit Evaluator-Format als fertig.

**OpenCode — dauerhaft 🚫 / Permission auf Task:** (1) Arbeitsverzeichnis = **Git-Root dieses Repos** (OpenCode lädt Config beim Start nach oben bis zur `.git`). (2) **App komplett neu starten** nach Änderungen an `opencode.json` / `.opencode/`. (3) In **`~/.config/opencode/opencode.json`** kann `permission.task` mit z. B. nur `general` / `explore` freigeben — dann fehlt **`kinderbuch-evaluator`**. Ergänzen, **nach** einer eventuellen `*`-Regel, z. B. `"kinderbuch-evaluator": "allow"` (letzte passende Regel gewinnt). (4) **MDM-/Managed-Config** (`/Library/Application Support/opencode/` etc.) kann Projekt-Settings überschreiben — dann nur IT oder lokale Managed-Datei anpassen. (5) Bei „Task erlauben?“: **Zulassen** oder „immer für diesen Subagenten“. (6) Geht es weiterhin nicht: **Fallback** wie oben (`AGENT_PROMPT` im selben Lauf).

**OpenCode — Zod: „must start with ses“ (oder „prt“):** Das ist **keine** Permission, sondern **interne ID-Validierung** (Session-/Message-Präfixe). Häufig: **Plugin** verändert Nachrichten-IDs (bekannt z. B. bei Integrationen, die den Chat-Stream hooken) oder **veraltete OpenCode-Version**. Vorgehen: OpenCode **aktualisieren**; in der globalen Config **`plugin` testweise leer** setzen und Task erneut testen; **`task_id` beim Task-Tool nur setzen**, wenn ihr wirklich eine vorherige Subagent-Aufgabe **fortsetzt** (sonst weglassen — kein freier Text wie „Fehde“). Der **Handoff-Block** gehört immer in **`prompt`**, nicht in ID-Felder. Wenn der Fehler bleibt: **Fallback** (`AGENT_PROMPT` im gleichen Lauf ohne Task).

---

### Modus A — Einzelnes Wort

Auslöser: Nutzer gibt ein einzelnes Wort, z.B. „modernisiere: Minne", „was bedeutet Kajüte für Kinder?", „Fehde kindgerecht erklären".

#### Schritt 1 — Rohdaten sammeln [PFLICHT — beides ausführen, Output prüfen bevor weiter]

**1a — Python-Pipeline [PFLICHT]:**
```bash
python3 scripts/word_lookup.py <wort> --json
```
Aus dem JSON extrahieren:
- `best_definition.definition`
- `best_definition.score` (0 = kein Treffer)
- `best_definition.source`
- `sources.openthesaurus.definitions`

**1b — Web-Recherche [PFLICHT — gleichzeitig mit 1a, NIEMALS überspringen]:**

MUSS ausgeführt werden — auch wenn die Pipeline einen Treffer liefert. Zwei Suchanfragen:
1. `<wort> Bedeutung einfach erklärt`
2. `<wort> Synonym einfaches Deutsch`

Ergebnisse als Freitext festhalten. Ohne diese Ergebnisse darf nicht zu Schritt 3 weitergegangen werden.

#### Schritt 2 — Fallback bei Nulltreffer (score == 0)

Wenn Pipeline nichts liefert:

1. **Wort-Varianten** nochmal durch die Pipeline:
   - Grundform / Infinitiv
   - Singular ↔ Plural
   - Alternative Schreibweise (ü → ue, ß → ss)

2. **Fuzzy-Websuche** (wenn Varianten auch leer):
   - `<wort> was bedeutet`
   - `<wort> Definition Deutsch`
   - `<wort> ähnliches Wort Kinder`

Alle Ergebnisse für den Handoff sammeln — nicht selbst auswerten.

#### Schritt 3 — Handoff an Kinderbuch-Evaluator [PFLICHT — Output prüfen bevor weiter]

**STOPP: Nicht selbst formulieren. Kein Ersatzwort, keine Erklärung, keine eigene Ausgabe produzieren.**

Den folgenden Datenblock vollständig ausgeben (als Text sichtbar machen), BEVOR der Evaluator aufgerufen wird:

```
WORT: <wort>
ALTERSGRUPPE: <altersgruppe>

WÖRTERBUCH:
  definition: <best_definition.definition oder leer>
  score: <best_definition.score>
  quelle: <best_definition.source>

SYNONYME (OpenThesaurus):
  <sources.openthesaurus.definitions oder leer>

WEB-ERGEBNISSE:
  suchanfrage_1: <ergebnis aus "Bedeutung einfach erklärt">
  suchanfrage_2: <ergebnis aus "Synonym einfaches Deutsch">
  fuzzy: <ergebnisse aus Fuzzy-Suche oder leer>
```

Erst nach Ausgabe dieses Blocks: **OpenCode:** Task-Tool → `kinderbuch-evaluator` mit exakt diesem Block. **Sonst:** Evaluator-Ausgabe wie in `scripts/AGENT_PROMPT.md` im selben Lauf erzeugen (kein Abbruch wegen fehlendem Subagenten).

#### Schritt 4 — Recherche-Log aktualisieren

`scripts/word_lookup.py` hat bereits Wort + Definition in `recherche_verlauf.md` geschrieben. Die Evaluator-Ausgabe direkt dahinter anhängen:

```bash
cat >> recherche_verlauf.md << 'EOF'

**Ersatzwort:** [modernes Wort]

**Erklärung:** [kindgerechte Erklärung, 1–2 Sätze]

---

EOF
```

Vollständiger Eintrag im Log:

```
## Minne — 2026-04-24 16:35

**Definition:** minne stf. liebe, zuneigung; insbes. die höfische frauenliebe …

**Quelle:** wbnetz_bmz · 3 Quellen

**Ersatzwort:** Liebe

**Erklärung:** Das alte Wort für das warme Gefühl, das man für jemanden hat, den man sehr mag.

---
```

Kein umgeschriebener Satz, wenn kein Satzkontext gegeben wurde.

---

### Modus B — Satz oder Absatz

Auslöser: Nutzer gibt einen Satz oder längeren Text, z.B. „Erkläre diesen Satz für Kinder: ‚Er trug Minne im Herzen, als die Fehde begann.'"

#### Schritt 1 — Schwierige Wörter identifizieren (Orchestrator)

Alle Wörter im Text markieren, die Kinder (6–9 Jahre) wahrscheinlich nicht kennen: archaische, veraltete, seltene oder fachsprachliche Wörter. Intern eine Liste erstellen.

#### Schritt 2 — Rohdaten für jedes Wort sammeln

Für jedes Wort: Modus A, Schritte 1–2 ausführen (Pipeline + Web parallel, Fallback wenn nötig). Alle Rohdaten-Blöcke sammeln.

#### Schritt 3 — Handoff an Kinderbuch-Evaluator [PFLICHT — nicht selbst formulieren]

**STOPP: Kein Ersatzwort, keine Erklärung, keine eigene Ausgabe produzieren.**

Alle Datenblöcke vollständig ausgeben (als Text sichtbar machen), BEVOR der Evaluator aufgerufen wird. Format wie Modus A, Schritt 3, die Blöcke nacheinander:

```
WORT: minne
...

WORT: fehde
...
```

Erst nach Ausgabe aller Blöcke: **OpenCode:** Task → `kinderbuch-evaluator` mit allen Blöcken. **Sonst:** `scripts/AGENT_PROMPT.md` auf alle Blöcke anwenden — für jedes Wort Ersatzwort + Erklärung im vorgegebenen Format.

#### Schritt 4 — Ausgabe zusammenbauen

```
**Originaltext:** [Text]

**Erklärt für Kinder:**

| Wort | Ersatz | Erklärung |
|------|--------|-----------|
| Minne | Liebe | Das alte Wort für das warme Gefühl, das man für jemanden hat, den man sehr mag. |
| Fehde | Streit | Ein langer, heftiger Streit zwischen zwei Gruppen oder Familien. |

**Umgeschriebener Satz:** [Text mit Ersatzwörtern, kindgerecht formuliert]
```

Für jedes Wort auch den Recherche-Log-Eintrag anhängen (wie Modus A, Schritt 4).

---

### Modus C — Buch-Datei direkt bearbeiten

Auslöser: Nutzer hat eine `.docx`-Datei und möchte Wörter direkt im Buchtext ersetzen.

#### Schritt 0 — Einmalige Vorbereitung (einmal pro Buchprojekt)

Wenn noch keine `.md`-Version des Buchs existiert:
```bash
python3 scripts/docx_to_md.py <pfad/zum/buch.docx> -o <buchname>.md
```
Die erzeugte `<buchname>.md` ist die Arbeitsdatei für alle weiteren Schritte.

#### Schritt 1 — Wort nachschlagen (Modus A, Schritte 1–3)

Für das gewünschte Wort vollständig Modus A durchlaufen. Dabei `BUCHDATEI = <buchname>.md` im Arbeitskontext merken.

#### Schritt 2 — Bestätigung einholen

Nach der Ausgabe (Ersatzwort + Erklärung) immer fragen:

> **Soll ich „[Originalwort]" direkt in deiner Buchdatei durch „[Ersatzwort]" ersetzen?**

Erst nach explizitem Ja weitermachen. Kein implizites Annehmen.

#### Schritt 3 — Ersetzung mit Vorschau

Vorschau zuerst:
```bash
python3 scripts/replace_in_book.py <buchname>.md "[Originalwort]" "[Ersatzwort]" --dry-run
```

Wenn Vorschau korrekt aussieht, Ersetzung durchführen:
```bash
python3 scripts/replace_in_book.py <buchname>.md "[Originalwort]" "[Ersatzwort]"
```

Bei mehreren Vorkommen (z.B. „Minne" kommt 12× vor): User fragen, ob alle ersetzt werden sollen (`--all`), oder nur erstes, oder bestimmte Stellen.

#### Optionen für `scripts/replace_in_book.py`

| Flag | Bedeutung |
|------|-----------|
| `--dry-run` | Zeigt betroffene Zeilen mit Kontext, ändert nichts |
| `--all` | Ersetzt alle Vorkommen (Standard: nur erstes) |

---

### Allgemeine Regeln

- **Niemals ablehnen** — jedes Wort sofort verarbeiten, egal ob archaisch oder modern.
- **Pipeline MUSS ausgeführt werden** — `scripts/word_lookup.py` ist Pflicht, kein optionaler Schritt.
- **Web-Recherche MUSS ausgeführt werden** — parallel zur Pipeline, immer, nicht nur als Fallback. Ohne Web-Ergebnisse ist Schritt 3 gesperrt.
- **Fuzzy-Fallback bei Nulltreffer** — Varianten + Websuche vor eigenem Vorschlag.
- **Orchestrator ohne Evaluator-Rolle:** Solange der Handoff-Block noch nicht da ist, kein Ersatzwort und keine kindgerechte Erklärung ausgeben. **Nach** dem Block: **entweder** Task → `kinderbuch-evaluator` **oder** (wenn Subagent nicht verfügbar) dieselbe Ausgabe wie der Evaluator laut `scripts/AGENT_PROMPT.md` — nie mit „Subagent fehlt“ enden.
- **Task-Tool** in OpenCode bevorzugen; fehlt es, zählt der **AGENT_PROMPT-Fallback** als vollständige Pipeline.
- **Handoff-Block ist Pflicht** — der Datenblock aus Schritt 3 muss sichtbar ausgegeben werden, bevor der Task-Aufruf erfolgt. Ein Handoff, der intern bleibt, gilt als nicht durchgeführt.
- **Keine Abkürzungen** im Log — „althochdeutsch" statt „ahd.", „mittelhochdeutsch" statt „mhd." — oder weglassen wenn für Kinder irrelevant.
- **Ton im Evaluator:** warm und ermutigend, nicht akademisch.
- **Format:** keine langen Einleitungen, keine Verabschiedungen.
