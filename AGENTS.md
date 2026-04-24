# word-lookup — Agent Reference

CLI and MCP server for looking up historical and archaic German words from up to nine sources in parallel. Returns structured JSON with an auto-selected `best_definition` field.

## Quick Start

```bash
python3 word_lookup.py <word> --json
```

## Calling from Python

```python
import subprocess, json

def lookup_word(word: str, sources: list[str] | None = None) -> dict:
    cmd = ["python3", "word_lookup.py", word, "--json"]
    if sources:
        cmd += ["--sources", ",".join(sources)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if result.returncode == 0:
        return json.loads(result.stdout)
    return {"error": result.stderr}
```

## Output Fields

| Field | Content | Recommendation |
|-------|---------|----------------|
| `best_definition.definition` | Richest definition across all sources | **Use this first** |
| `best_definition.source` | Source key (e.g. `wbnetz_dwb`) | Include in citations |
| `best_definition.score` | Quality score (length × source bonus) | Confidence estimate |
| `summary` | Human-readable result count | Quick sanity check |
| `sources.<key>.definitions` | Raw definitions per source | Deep analysis |
| `sources.openthesaurus.definitions` | Comma-separated synonyms | Synonym lookup |

Wörterbuchnetz sources receive a **1.5× quality bonus** and return reconstructed full articles from historical German dictionaries. All other sources receive either a 1.2× (Wiktionary) or 1.0× bonus.

## Available Sources

| Key | Dictionary | Period |
|-----|-----------|--------|
| `wbnetz_dwb` | Deutsches Wörterbuch (Grimm) | 16th–19th c. |
| `wbnetz_adelung` | Adelung | 18th c. |
| `wbnetz_awb` | Althochdeutsches Wörterbuch | 8th–11th c. |
| `wbnetz_lexer` | Lexer (Middle High German) | 12th–15th c. |
| `wbnetz_bmz` | Benecke-Müller-Zarncke (MHD) | 12th–15th c. |
| `fwb` | Frühneuhochdeutsches Wörterbuch | 14th–17th c. |
| `dwds` | DWDS | Modern + historical |
| `wiktionary` | Wiktionary DE | All periods, etymology |
| `openthesaurus` | OpenThesaurus | Synonyms (modern) |

Wörterbuchnetz sources (`wbnetz_*`) only appear in the result when the Meta API finds an entry for the queried word. Requesting them via `--sources` has no effect if the word is not indexed.

```bash
python3 word_lookup.py --list-sources          # list all source keys
python3 word_lookup.py minne --sources wbnetz_lexer,wbnetz_bmz --json
```

## Error Handling

```python
data = lookup_word("grollen")
best = data.get("best_definition", {})

if not best.get("definition"):
    # No usable result — score is 0, source is "none"
    print("No definition found.")
else:
    print(best["definition"])
    print(f"Source: {best['source']} (score: {best['score']})")
```

## Research Log

Every lookup is automatically appended to `recherche_verlauf.md` (timestamp, word, best definition, source). The file is created on first use.

## MCP Server

`server.py` exposes `lookup_word` as an MCP tool — no CLI invocation needed.

```json
"word-dict": {
  "type": "local",
  "command": ["/path/to/.venv/bin/python", "/path/to/server.py"],
  "enabled": true
}
```

System prompt template for agents consuming this tool: see `AGENT_PROMPT.md`.

---

## Kinderbuch-Modernisierung — OpenCode Workflow

Dieser Workflow wird ausgeführt, wenn der Nutzer ein archaisches oder veraltetes deutsches Wort aus einem alten Kinderbuch modernisieren möchte.

### Altersgruppe (Konfiguration)

Standard: **Grundschule (6–9 Jahre)** — sehr einfache, direkte Sprache, keine Fremdwörter.
Kann per Nutzernachricht überschrieben werden (z.B. „für 10–12-Jährige").

### Eingabe-Modus A — Einzelnes Wort

Auslöser: Nutzer gibt ein einzelnes Wort, z.B. „modernisiere: Minne" oder „was bedeutet Fehde für Kinder?"

**Schritt 1 — Nachschlagen (immer zuerst):**
```bash
python3 word_lookup.py <wort> --json
```
Das Ergebnis kommt als JSON auf stdout. Relevant: `best_definition.definition`, `best_definition.source`, `best_definition.score`.

**Schritt 2 — Nicht gefunden?**
- Wenn `best_definition.score == 0`: Versuche Varianten (Stamm, Singular/Plural, alternative Schreibweise).
- Wenn weiterhin nichts: Mache einen eigenen Vorschlag, **deutlich markiert** mit `⚠️ Kein Wörterbuch-Treffer — LLM-Vorschlag`.

**Schritt 3 — Ausgabe generieren:**

```
**[Originalwort]**

**Ersatzwort:** [modernes, kindgerechtes deutsches Wort]

**Erklärung:** [1–2 Sätze, die ein Kind im Grundschulalter versteht. Warm, klar, ohne Fremdwörter.]

**Quelle:** [best_definition.source — Klarnamen aus der Quelltabelle oben]
```

Kein umgeschriebener Satz, wenn kein Satzkontext gegeben wurde.

---

### Eingabe-Modus B — Satz oder Absatz

Auslöser: Nutzer gibt einen Satz oder längeren Text, z.B. „Erkläre diesen Satz für Kinder: ‚Er trug Minne im Herzen, als die Fehde begann.'"

**Schritt 1 — Archaische Wörter identifizieren:**
Analysiere den Text und identifiziere alle Wörter, die Kinder heute nicht kennen würden (archaisch, veraltet, mittelhochdeutsch, frühneuhochdeutsch). Gib intern eine Liste zurück.

**Schritt 2 — Nachschlagen (für jedes Wort):**
```bash
python3 word_lookup.py <wort> --json
```
Für jedes identifizierte Wort ausführen.

**Schritt 3 — Ausgabe generieren:**

```
**Originaltext:** [Text]

**Erklärt für Kinder:**

| Wort | Ersatz | Erklärung |
|------|--------|-----------|
| Minne | Liebe | Das alte Wort für das warme Gefühl, das man für jemanden hat, den man sehr mag. |
| Fehde | Streit | Ein langer, heftiger Streit zwischen zwei Gruppen oder Familien. |

**Umgeschriebener Satz:** [Text mit Ersatzwörtern, kindgerecht formuliert]
```

---

### Recherche-Log

Nach jeder Modernisierung wird `recherche_verlauf.md` vervollständigt. `word_lookup.py` schreibt automatisch Wort + Definition in die Datei. Danach hänge du (OpenCode) den Modernisierungs-Teil direkt dahinter an:

```bash
cat >> recherche_verlauf.md << 'EOF'

**Ersatzwort:** [modernes Wort]

**Erklärung:** [kindgerechte Erklärung, 1–2 Sätze]

---

EOF
```

Das ergibt pro Lookup einen vollständigen Eintrag:
```
## Minne — 2026-04-24 16:35

**Definition:** minne stf. liebe, zuneigung; insbes. die höfische frauenliebe …

**Quelle:** wbnetz_bmz · 3 Quellen

**Ersatzwort:** Liebe

**Erklärung:** Das alte Wort für das warme Gefühl, das man für jemanden hat, den man sehr mag.

---
```

---

### Allgemeine Regeln

- Den Lookup-Schritt **niemals überspringen** — immer erst `word_lookup.py` ausführen, bevor ein Ersatz generiert wird.
- Wenn ein LLM-Fallback verwendet wird: immer `⚠️ Kein Wörterbuch-Treffer` markieren.
- Ausgabe auf Deutsch, Ton warm und ermutigend — nicht akademisch.
- Keine langen Einleitungen, keine Verabschiedungen.
