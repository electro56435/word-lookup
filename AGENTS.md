# word-lookup — Agent Reference

CLI and MCP server for looking up historical and archaic German words from up to nine sources in parallel. Returns structured JSON with an auto-selected `best_definition` field.

## Quick Start

```bash
python word_lookup.py <word> --json
```

## Calling from Python

```python
import subprocess, json

def lookup_word(word: str, sources: list[str] | None = None) -> dict:
    cmd = ["python", "word_lookup.py", word, "--json"]
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
python word_lookup.py --list-sources          # list all source keys
python word_lookup.py minne --sources wbnetz_lexer,wbnetz_bmz --json
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
