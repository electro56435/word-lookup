## Research Brief: Wörterbuchnetz open-api — exact endpoints and response formats

> **Your role:** You are a researcher. Search the web and return findings. Do NOT execute, implement, write code, or produce a plan — the sections below are background context only. The only deliverable is answers to the questions in `### Open Questions`.

### Open Questions (primary ask)

1. What does `GET https://api.woerterbuchnetz.de/open-api/dictionaries/DWB/lemmata/:searchpattern` return? What is the exact response format (JSON/XML/TEI)? Does it return definition text or only lemma metadata (headword, lemid, links)? Provide a concrete example response for a simple German word (e.g. "grollen" or "Haus").

2. What does `GET https://api.woerterbuchnetz.de/open-api/dictionaries/DWB/fulltext/:searchpattern` return? Does it return the actual dictionary entry text (definitions, citations, etymology)? What is the response format? Provide a concrete example response.

3. Is there any other endpoint under `/open-api/dictionaries/DWB/` that returns the full definition/article text for a single lemma — given either a word string or a lemid? The known lemid format is e.g. `G28835` (for "grollen" in DWB).

4. Do the other dictionaries in the same API (Adelung, AWB, Lexer, BMZ) have the same `/open-api/dictionaries/{SIGLE}/lemmata/` and `/fulltext/` endpoints? Or do some use different method names? The sigles to check: `Adelung`, `AWB`, `Lexer`, `BMZ`.

5. Is there any publicly documented OpenAPI/Swagger spec or developer documentation for `api.woerterbuchnetz.de/open-api`? (GitHub repos, Trier university pages, academic papers describing the API, etc.)

6. The Meta API (`api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/{word}/0/tei-xml`) returns lemid and portal URL per dictionary entry — but the portal URLs are JS-rendered shells. Is there a way to fetch the actual entry content for a specific lemid without a browser? E.g. a `/tei-xml` or `/json` variant of the portal URL, or a separate content delivery endpoint?

Support important claims with concrete sources. If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such. Include direct URLs, not just site names. If sources disagree, note the disagreement instead of flattening it into one answer.

---

### Project Context

A Python 3.12 CLI tool that looks up historical and archaic German words from multiple sources in parallel using `requests` + `BeautifulSoup`. No browser automation — only `requests.get()`. Currently uses the Wörterbuchnetz Meta API to discover lemma IDs across DWB, Adelung, AWB, Lexer, and BMZ.

### Current Task

Adding actual definition text from DWB and related dictionaries. The Meta API gives lemid + portal URL per dictionary, but the portal pages (`woerterbuchnetz.de/?sigle=DWB&lemid=G28835`) are JavaScript-rendered shells — `requests.get()` returns only a 3 KB JS bootstrap, not the article content.

The `open-api` endpoint exists and returns a method list:

```
GET https://api.woerterbuchnetz.de/open-api/dictionaries/DWB
→ {"result_set": [
    {"methodid": "fulltext", "path": "/open-api/dictionaries/DWB/fulltext/:searchpattern"},
    {"methodid": "lemmata",  "path": "/open-api/dictionaries/DWB/lemmata/:searchpattern"}
  ]}
```

The next step is knowing exactly what these endpoints return.

### Observable Symptoms

- `GET https://www.woerterbuchnetz.de/DWB?lemid=G28835` → 200 OK, but only 3 KB of JS bootstrap (no article content in HTML)
- `GET https://api.woerterbuchnetz.de/open-api/dictionaries/DWB/entries/G28835` → 400: `"undefined method entries for dictionary DWB"`
- `GET https://api.woerterbuchnetz.de/open-api/dictionaries` → 200, lists 52 available dictionaries
- Meta API `https://api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/grollen/0/tei-xml` → works, returns TEI-XML with lemids and portal URLs

### Desired Output Format

For each working endpoint found:

```
Endpoint: GET https://api.woerterbuchnetz.de/open-api/dictionaries/DWB/lemmata/grollen
Response format: JSON / XML / TEI-XML
Contains definition text: yes / no
Example response (truncated):
  { ... }
```

### Temporal Scope

No restriction — include any documentation, papers, or examples regardless of date. Prefer the most recent if multiple versions exist.

### Source Requirements

Mode: `manual`

List 3–5 sources that contributed the most substance. Format:

```
## Sources
1. [Title or description](URL) — one sentence: what specific information this source provided
```

Additional requirements:
- Support important claims with concrete sources.
- If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such.
- Include direct URLs, not just site names.
- If sources disagree, note the disagreement instead of flattening it into one answer.

---

## Sources

1. [DWB fulltext endpoint (live)](https://api.woerterbuchnetz.de/open-api/dictionaries/DWB/fulltext/grollen) — confirmed JSON format, result_set with textid + wbnetzkwiclink per hit
2. [DWB kwic endpoint (live)](https://api.woerterbuchnetz.de/open-api/dictionaries/DWB/kwic/15643355) — confirmed kwic_text field + word-level token list for reconstruction
3. [Lexer definition endpoint (live)](https://api.woerterbuchnetz.de/open-api/dictionaries/Lexer/definition/haus) — 64 results, confirmed JSON format identical to fulltext
4. [Wörterbuchnetz method list (live)](https://api.woerterbuchnetz.de/open-api/dictionaries/DWB) — confirmed only 'fulltext' and 'lemmata' for DWB; Lexer/BMZ additionally have 'definition' and 'citation'

---

## Returned Research

### 1. lemmata endpoint

`GET /open-api/dictionaries/DWB/lemmata/Haus` with `Accept: application/json`:
```json
{"result_type":"lemmata_list","result_set":[
  {"sigle":"DWB","lemma":"haus","gram":"n.","wbnetzid":"H03949","bookref":"10,640,57",
   "wbnetzlink":"https://woerterbuchnetz.de/?sigle=DWB&lemid=H03949"}
],"result_count":3}
```
Contains: lemma metadata only. No definition text.

### 2. fulltext endpoint

`GET /open-api/dictionaries/DWB/fulltext/grollen` with `Accept: application/json`:
Returns 154 results — all DWB entries that contain the word anywhere in their text.
Each item: `{sigle, lemma, gram, wbnetzid, textid, match, wbnetzlink, wbnetzkwiclink}`.
No definition text inline. KWIC fetch required.

### 3. definition endpoint (Lexer/BMZ only)

`GET /open-api/dictionaries/Lexer/definition/haus` with `Accept: application/json`:
Same response format as fulltext (64 results). Only available for Lexer and BMZ.
DWB returns 400 `undefined method definition`.

### 4. kwic endpoint — key to text reconstruction

`GET /open-api/dictionaries/DWB/kwic/{textid}` with `Accept: application/json`:
```json
{"result_type":"word_list","kwic_text":"grollen , vb. I. form. zu beachten ist, dasz...","result_set":[
  {"sigle":"DWB","wbnetzid":"G28835","textid":15643355,"word":"grollen"},
  ...
],"result_count":22}
```
Returns ~22 word-level tokens centered on the matched textid, plus a `kwic_text` string.
By fetching multiple KWIC windows and unioning token maps (sorted by textid), the full
article can be reconstructed.

### 5. Other sigles

Method listing confirmed per sigle:
- DWB: `fulltext`, `lemmata`
- Adelung: `fulltext`, `lemmata`
- AWB: `fulltext`, `lemmata`
- Lexer: `fulltext`, `lemmata`, `definition`, `citation`
- BMZ: `fulltext`, `lemmata`, `definition`

### 6. NOTE: Accept header required

Without `Accept: application/json`, all endpoints return a non-JSON schema-documentation
string (unquoted keys, type names as values). The correct header is required for real data.

---

## Evaluation

**Implemented 2026-04-24.** KWIC reconstruction approach works:
- `fetch_woerterbuchnetz_entry(sigle, word)` in `word_lookup.py` now uses `fulltext` (or `definition` for Lexer/BMZ), filters to exact lemma matches, fetches up to 15 KWIC windows in parallel, reconstructs text from sorted token map.
- Tested: `grollen` → DWB + Adelung text; `minne` → BMZ + Adelung text; `Waldhorn` → DWB + Adelung text.
- The old portal HTML scraping approach (JS-rendered shells) is completely replaced.
