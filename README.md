# word-lookup

CLI and MCP server for looking up historical and archaic German words from multiple sources in parallel.

## What it does

Queries three sources simultaneously and combines the results:

| Source | What it returns |
|---|---|
| **DWDS** (`dwds.de`) | Modern and historical definitions, word class, etymology |
| **Wiktionary DE** | Archaic senses, full etymology chain |
| **Wörterbuchnetz Meta** | Links to 18+ historical dictionaries (Grimm, Adelung, Campe, etc.) |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 mcp
```

## Usage

### Word lookup CLI

```bash
python word_lookup.py Waldhorn
python word_lookup.py Waldhorn --json
```

### DOCX to Markdown converter

```bash
python docx_to_md.py document.docx
python docx_to_md.py document.docx --output out.md
```

### MCP server

```bash
python server.py
```

Exposes two MCP tools:
- `lookup_word` — looks up a word, returns combined results from all sources
- `docx_to_markdown` — converts a DOCX file path to Markdown text

## MCP registration (OpenCode / opencode config)

Add to your `config.json` under `mcp`:

```json
"word-dict": {
  "type": "local",
  "command": ["/absolute/path/to/.venv/bin/python", "/absolute/path/to/server.py"],
  "enabled": true
}
```

## Sources

| Source | URL pattern | Method |
|---|---|---|
| DWDS | `https://www.dwds.de/wb/{wort}` | HTML scrape, `.dwdswb-definition` |
| Wiktionary | `https://de.wiktionary.org/w/api.php` | MediaWiki API |
| Wörterbuchnetz | `https://api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/{wort}/0/tei-xml` | XML API (discovery only) |

## Known limitations

- Wörterbuchnetz returns links to dictionaries, not definitions directly. Most linked dictionaries (Krünitz, Campe etc.) require JS rendering and are not directly fetchable.
- DWDS has no public definition API — only a snippets endpoint that returns metadata without definitions.
- Zeno.org has no stable per-word URL schema.
