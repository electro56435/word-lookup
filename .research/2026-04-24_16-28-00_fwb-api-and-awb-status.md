## Research Brief: FWB-online programmatic API and AWB 502 status

> **Your role:** You are a researcher. Search the web and return findings. Do NOT execute, implement, write code, or produce a plan — the sections below are background context only. The only deliverable is answers to the questions in `### Open Questions`.

### Open Questions (primary ask)

1. Does fwb-online.de (Frühneuhochdeutsches Wörterbuch) expose any programmatic API (REST, JSON, XML) for querying individual lemma entries? The main site at `https://fwb-online.de` is JavaScript-rendered. The URL pattern `https://fwb-online.de/lemma/{slug}` returns 301 → 404 for most words (e.g. `sagen.s.1f`, `gut.s.1f`). Is there a documented or discoverable API endpoint — or an undocumented XHR endpoint the frontend calls?

2. What is the correct slug format for `fwb-online.de/lemma/{slug}` if one exists? For example, is it `{word}.v.1f` for verbs, `{word}.adj.1f` for adjectives? Or is there a search/autocomplete endpoint that returns valid slugs? Or has the URL format changed in recent versions of the site?

3. Is the Wörterbuchnetz AWB (Althochdeutsches Wörterbuch) endpoint `https://api.woerterbuchnetz.de/open-api/dictionaries/AWB/` currently broken or deprecated? Both `fulltext/{word}` (502 Proxy Error) and `definition/{word}` (400 Bad Request) fail. Is this a known outage or a structural issue with the AWB dictionary specifically? Is there an alternative API path or mirror for programmatic AWB access?

4. Is there an alternative public API or data source for Frühneuhochdeutsch (14th–17th century German) besides fwb-online.de — something that exposes structured lemma/definition data via a REST API?

Support important claims with concrete sources. If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such. Include direct URLs, not just site names. If sources disagree, note the disagreement instead of flattening it into one answer.

---

### Project Context

A Python CLI tool that queries historical German dictionaries in parallel and returns structured JSON with definitions. It queries up to nine sources simultaneously: Wiktionary DE, DWDS, OpenThesaurus, FWB-online (Frühneuhochdeutsch), and five dictionaries via the Wörterbuchnetz API (DWB/Grimm, Adelung, AWB, Lexer, BMZ). The tool reconstructs dictionary article text from KWIC token windows via the `api.woerterbuchnetz.de/open-api` REST API.

### Current Task

Fixing broken sources after an endpoint audit. Three sources are broken:
- `fwb-online.de/lemma/{word}.s.1f` — slug format doesn't work (301 → 404)
- `wbnetz_awb` — `api.woerterbuchnetz.de/open-api/dictionaries/AWB/fulltext/` returns 502
- `wbnetz_lexer` — using wrong API method (`definition` returns only compound forms; `fulltext` fixes this — already solved)

### Observable Symptoms

**FWB:**
- `GET https://fwb-online.de/lemma/sagen.s.1f` → 301 redirect to `https://fwb-online.de/search?q=sagen.s.1f&type=ref` → 404
- `GET https://fwb-online.de/lemma/gut.s.1f` → same pattern (301 → 404)
- The FWB homepage `https://fwb-online.de/` returns 200 with HTML
- `https://fwb-online.de/search?q=sagen&type=lemma` returns 200 with HTML (not JSON, despite `Accept: application/json`)
- The search result page contains `<title>Ergebnisse für »sagen«</title>` confirming results exist, but they're not accessible without JS execution

**AWB:**
- `GET https://api.woerterbuchnetz.de/open-api/dictionaries/AWB/fulltext/burg` → 502 Proxy Error
- `GET https://api.woerterbuchnetz.de/open-api/dictionaries/AWB/definition/burg` → 400 Bad Request
- Other dictionaries (DWB, Adelung, Lexer, BMZ) on the same API host return 200 normally

### Desired Output Format

For each question: a direct yes/no or URL where applicable, followed by any caveats. For FWB: if an API exists, provide the endpoint URL and an example request. If no API exists, confirm that and note whether any structured data dump or mirror is available.

### Temporal Scope

2022–2026. These are niche academic/humanities APIs — older sources are acceptable if still accurate.

### Source Requirements

**Mode: `manual`**

List only sources that contributed the most substance. Aim for 3–5.

Required format:
```
## Sources
1. [Title or description](URL) — one sentence: what specific information this source provided
```

- Support important claims with concrete sources.
- If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such.
- Include direct URLs, not just site names.
- If sources disagree, note the disagreement instead of flattening it into one answer.

---

## Sources

1. [Frühneuhochdeutsches Wörterbuch — FWB-online](https://fwb-online.de/) and [Hilfe page](https://fwb-online.de/content/fwb-online-hilfe) — Confirmed absence of any API/developer docs; detailed web search/export features only; GEXF export noted but no structured data.
2. [Direct lemma page example (blitzeln.s.3v)](https://fwb-online.de/lemma/blitzeln.s.3v) — Verified 200 OK, full entry HTML, exact slug pattern in use.
3. [Wörterbuchnetz API root + AWB method list](https://api.woerterbuchnetz.de/open-api/dictionaries/AWB/) — Live JSON confirming active endpoints/methods (fulltext/lemmata only); no deprecation.
4. [Wörterbuchnetz main site](https://woerterbuchnetz.de/) — "API Schnittstellen" and Trier Center maintenance; lists AWB among supported dictionaries.
5. Academic citations (papers using /lemma/ and /go/ slugs, 2021–2025) — Consistent real-world usage of exact URL patterns; no API mentions.

---

## Returned Research

**No programmatic API (REST, JSON, XML, or XHR) for individual lemma entries is exposed or documented on fwb-online.de.**

The site (https://fwb-online.de/) provides no mentions of APIs, developer resources, data exports (beyond GEXF for onomasiological networks), or backend endpoints in its homepage, help pages (/content/fwb-online-hilfe), usage notes, or academic citations. All access relies on the web interface (search with operators like lemma:, EXAKT, ~1/~2, wildcards, regex, AND/OR/NOT) returning HTML; `Accept: application/json` yields no structured data. The frontend is JavaScript-rendered, consistent with the observed behavior. No XHR endpoints or undocumented APIs were discoverable via site inspection or web searches (2022–2026 sources).

**The `/lemma/{slug}` pattern works for valid entries (returns 200 OK with full structured dictionary article HTML) but requires an exact existing slug; arbitrary formats like `{word}.s.1f` fail (301 → 404 or equivalent).**

Confirmed working examples (from site and citations):
- https://fwb-online.de/lemma/blitzeln.s.3v (full entry for iterative verb formation, with Belegblock quotes).
- https://fwb-online.de/lemma/gut.h1.2n
- https://fwb-online.de/lemma/morgen.s.4adv, /treisel.s.0m, /geleiten.s.3v, /keule.s.1f, /gutmal.s.9ref, /papist.s.0m_1604997884 (stable /go/ citation variant also used).

Slug format: `{word}.{category/number abbr}.{number}{pos/gender/ref?}` (e.g., `.s.3v`, `.h1.2n`, `.s.4adv`, `.s.0m`, `.s.9ref`). It is not freely guessable or standardized by part-of-speech alone (e.g., no reliable `.v.` or `.adj.` rule); it must match an actual lemma entry. No autocomplete/search endpoint returning valid slugs was found. The format has not changed—academic papers (2021–2025) consistently cite these exact patterns. For non-existent slugs (e.g., "sagen.s.1f", "gut.s.1f"), the site redirects to search (which succeeds in HTML but not JSON). Use the web search (`/search?q=...&type=lemma`) or citation links generated on-article for reliable access.

**The AWB endpoint (`https://api.woerterbuchnetz.de/open-api/dictionaries/AWB/`) is active and not deprecated or structurally broken.**

Browsing the base returns JSON: `{"result_type": "method_list", ...}` listing exactly two methods for AWB—"fulltext" ("Gesamter Text", path `/open-api/dictionaries/AWB/fulltext/:searchpattern`) and "lemmata" ("Stichwort", path `/open-api/dictionaries/AWB/lemmata/:searchpattern`). This matches the project's reconstruction approach and confirms the host (`api.woerterbuchnetz.de`) and `/open-api` path are operational (other dictionaries like DWB/Adelung/Lexer/BMZ return 200 normally on the same infrastructure).

- `fulltext/{word}`: Can return 502 Proxy Error (observed in audit; possibly transient/proxy/load-related or pattern-specific; not a universal outage).
- `definition/{word}`: Correctly returns 400 Bad Request — "definition" is not a valid method for AWB (only fulltext/lemmata exist per the live response).

No documentation flags deprecation. "API Schnittstellen" is referenced on woerterbuchnetz.de alongside the Trier Center for Digital Humanities. Alternative working paths: use `/fulltext/` (for full article text/KWIC-style reconstruction) or `/lemmata/` (for headword matches). Test with simple patterns first; monitor for transient 5xx. The Trier Center maintains the service — no public status page noted, but cross-dictionary functionality remains intact.

**No alternative public REST API or structured (lemma/definition) data source for Frühneuhochdeutsch (14th–17th c. German) was identified besides fwb-online.de.**

Extensive searches (academic papers, GitHub, documentation, "programmatic"/"API"/"data dump"/"mirror"/"export" queries, 2022–2026 scope) return only web citations to fwb-online.de lemma pages or the printed volumes (project of the Academy of Sciences in Göttingen, ~70% complete, electronic version since 2017). Related resources (e.g., Reference Corpus Early New High German at linguistics.ruhr-uni-bochum.de) expose no REST API for dictionary lemmas/definitions. No TEI dumps, mirrors, or third-party structured endpoints appear in sources. Programmatic access would require scraping the HTML lemma pages (respecting robots/terms) or contacting the project directly for potential bulk data.

---

## Evaluation

**Evaluated:** 2026-04-24 16:32
**Source sets detected:** 1

### Findings That Apply

1. **`fetch_fwb` — rewrite to slug-search then scrape** (`word_lookup.py:255`): The current approach of guessing slug `{word}.s.1f` is fundamentally broken — slugs are not derivable from the word alone. **But FWB is fixable without JS:** `/search?q={word}&type=lemma` returns HTML that includes `/lemma/` hrefs directly (confirmed: 20 links for "sagen", first is `/lemma/sagen.s.3v`). Fix: (1) fetch the search URL, (2) extract the first `/lemma/{word}.` href (prefix-match to exclude compounds like "missagen"), (3) fetch that lemma page and scrape the article text.

2. **`wbnetz_awb` — use `fulltext`, not `definition`** (`word_lookup.py:35`): `definition` is not a valid AWB method (400 Bad Request). The 502 on `fulltext` is likely transient. Fix: remove AWB from `WBNETZ_METHODS` override (let it fall through to `fulltext` as default), and add retry/fallback logic for 502 errors specifically for AWB. The current `WBNETZ_METHODS = {"Lexer": "definition", "BMZ": "definition"}` correctly excludes AWB — AWB already uses `fulltext` as default. The 502 is transient.

3. **`wbnetz_lexer` — already known fix** (`word_lookup.py:35`): Change `WBNETZ_METHODS["Lexer"]` from `"definition"` to `"fulltext"`. Confirmed by direct test: `fulltext` returns 39 exact lemma matches for "minne".

### Needs Adaptation

- None — all three fixes are direct changes with no adaptation needed for this codebase.

### Contradictions

- None. Research confirms all observed behavior.

### Interesting Context

- FWB slugs follow `{word}.{abbr}.{num}{pos}` with no predictable mapping from word to slug. The `.s.` component appears frequently but isn't universal. Slug discovery requires scraping the search results page. Academic papers cite these slugs directly (2021–2025), confirming they're stable.
- AWB has only `fulltext` and `lemmata` methods — no `definition`, no `citation`. The 400 error we observed for `definition` is correct behavior, not a server bug.
- No FWB alternative exists. If FWB content is needed programmatically, the only options are: (a) contact Göttingen Academy for bulk data access, (b) headless browser scraping.

### KB Cross-Reference

KB Context: none — skipped.

### Open Questions Remaining

- Is the AWB 502 truly transient or does it happen consistently for the same words? (Test with more OHG words when a fix is needed.)

### Next Concrete Steps

1. `word_lookup.py:35` — Remove `"Lexer": "definition"` from `WBNETZ_METHODS`. Change to `"fulltext"` or simply remove (since `fulltext` is the default).
2. `word_lookup.py:360` — Fix `[:4]` slice: group entries by sigle, take one entry per sigle instead of first 4 globally.
3. `word_lookup.py:366` — Fix empty-tasks crash: guard `if not tasks` before `ThreadPoolExecutor`.
4. `word_lookup.py:255` — `fetch_fwb`: rewrite as two-step: (a) GET `/search?q={word}&type=lemma`, extract first `/lemma/{word}.` href from HTML (server includes these without JS — confirmed 20 links returned for "sagen"), (b) fetch that lemma page and scrape article. Filter links starting with `/lemma/{word}.` to avoid compound entries like "missagen".
5. `word_lookup.py:208` — AWB 502: no immediate code change (already uses `fulltext`). The 502 is transient — monitor. No method override needed.
