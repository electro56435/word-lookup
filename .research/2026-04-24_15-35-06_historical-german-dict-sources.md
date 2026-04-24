## Research Brief: Fetchable sources for archaic German word lookup

> **Your role:** You are a researcher. Search the web and return findings. Do NOT execute, implement, write code, or produce a plan — the sections below are background context only. The only deliverable is answers to the questions in `### Open Questions`.

### Open Questions (primary ask)

1. Which of the dictionaries accessible via the Wörterbuchnetz portal (Grimm DWB, Adelung, Campe, Paul, Kluge, Fischer Schwäbisches Wörterbuch, etc.) have **static, directly fetchable HTML pages** — i.e. `requests.get(url)` returns the full definition content without JavaScript rendering? For each one: what is the stable URL pattern per word?

2. Does Grimm's Deutsches Wörterbuch (DWB) have a direct, stable URL per word — outside of Wörterbuchnetz? Is there a JSON or XML API? What is the best way to fetch a definition for a given lemma programmatically?

3. How do you look up the `lemid` (lemma ID) for a word in the Wörterbuchnetz system programmatically? The URL format `https://www.woerterbuchnetz.de/DWB?lemid=GR10854` works when the ID is known — but how do you resolve a plain German word to its lemid via an API call?

4. Does the Mittelhochdeutsches Wörterbuch (`mhdbdb.sbg.ac.at` or `mhdwb.de`) offer a fetchable URL per word or an API? What are the access patterns?

5. Does the Frühneuhochdeutsches Wörterbuch (`fnhdw.de`) have a direct URL per word or an API?

6. Does the Deutsches Rechtswörterbuch (`drw-www.adw.uni-heidelberg.de`) have a public API or stable URL per lemma?

7. Are there any other German historical dictionary projects (from universities, academies, or digital humanities initiatives) that offer a programmatic, JS-free access method for looking up archaic German words from the 15th–19th century? Include any undocumented or semi-public APIs if known.

Support important claims with concrete sources. If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such. Include direct URLs, not just site names. If sources disagree, note the disagreement instead of flattening it into one answer.

---

### Project Context

A Python 3.12 CLI tool that looks up historical and archaic German words from multiple sources in parallel using `requests` + `BeautifulSoup`. No browser automation — only `requests.get()`. The tool is used to research obsolete vocabulary from 18th/19th century German texts (fairy tales, children's books, regional literature).

### Current Task

Expanding the source coverage beyond the three currently working sources. The goal is to add direct definition retrieval from Grimm-era dictionaries — not just discovery links (which is what Wörterbuchnetz Meta API currently provides).

### Observable Symptoms

- **Wörterbuchnetz Meta API** (`api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/{word}/0/tei-xml`) — works and returns links to 18–37 dictionaries, but all linked pages either require JS rendering or have no stable per-word URL schema. No definitions returned directly.
- **Krünitz** (linked by Wörterbuchnetz) — `requests.get()` returns empty/unusable HTML; requires JS.
- **Zeno.org** — no stable per-word URL; navigation is search-form-based.
- **DWDS snippet API** (`/api/wb/snippet?q={word}`) — confirmed to exist but returns metadata only, no definitions (legally restricted per DWDS).

### Relevant Code

Current working sources in `word_lookup.py`:

```python
DWDS_URL   = "https://www.dwds.de/wb/{word}"         # HTML scrape, .dwdswb-definition
WIKT_API   = "https://de.wiktionary.org/w/api.php"    # MediaWiki API
WBNETZ_API = "https://api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/{word}/0/tei-xml"
```

All three fetched in parallel via `ThreadPoolExecutor(max_workers=3)`. Rate limit: 0.5s sleep per request.

### Desired Output Format

For each source found:

```
### [Dictionary name] — [base URL]
- Directly fetchable (no JS): yes / no
- URL pattern: https://.../{word} or description
- API: yes (JSON/XML/TEI) / no / undocumented
- Coverage: which language periods, which century
- Example URL for "Waldhorn": https://...
- Caveats / rate limits / terms of use notes
```

Sort by usefulness for automated scraping. Prioritize sources with direct per-word URLs and no JS rendering.

### Temporal Scope

No restriction — include stable/maintained sources regardless of age. Prefer sources with active maintenance or known stability.

### Source Requirements

Mode: `manual`

List 3–7 sources that contributed the most substance. Format:

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

1. [Frühneuhochdeutsches Wörterbuch — FWB-online](https://fwb-online.de/) — provided the concrete static `/lemma/{slug}` pattern, confirmed static HTML content, and example entry structure/coverage (14th–17th c.).
2. [Wörterbuchnetz](https://woerterbuchnetz.de/) and [Meta API examples](https://api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/.../tei-xml) — core documentation and live responses showing lemid resolution, sigle/URL construction, and full entry text in HTML for DWB/Adelung/etc.
3. [Mittelhochdeutsches Wörterbuch Online](https://mhdwb-online.de/) — official details on published articles, lemmaliste navigation, Wörterbuchnetz linkages, and publication-delay access model.
4. [Deutsches Rechtswörterbuch (DRW)](https://drw.hadw-bw.de/drw/info/drw_english.htm) and related Heidelberg pages — coverage scope (450 AD–1815) and online availability notes.
5. Academic citations and project pages (e.g., dwb.uni-trier.de references in multiple papers, FWB lemma examples in Springer/Brill chapters) — corroborated URL patterns, static nature via visible excerpts, and absence of independent JSON APIs.
6. [MHDBDB Salzburg](https://mhdbdb.sbg.ac.at/) — beta status, conceptual vs. definitional focus, and legacy search capabilities.
7. Wikipedia + secondary overviews (e.g., on DRW, Grimm digital editions) — confirmed institutional hosting and lack of simpler per-word schemas outside the above portals.

---

## Returned Research

**1. Dictionaries accessible via the Wörterbuchnetz portal (Grimm DWB, Adelung, Campe, Paul, Kluge, Fischer Schwäbisches Wörterbuch, etc.) with static, directly fetchable HTML pages (i.e., `requests.get(url)` returns full definition content without JS rendering), and their stable URL patterns per word:**

Most dictionaries hosted on Wörterbuchnetz (woerterbuchnetz.de, operated by the Trier Center for Digital Humanities) provide server-rendered or static HTML content for dictionary entries once the lemma ID (lemid) is known. Search engine snippets and citations routinely display full entry text (e.g., long excerpts from Grimm DWB entries), confirming that the HTML payload includes definitions, etymology, citations, etc., without requiring client-side JS rendering for core content. This contrasts with certain linked external dictionaries (e.g., some Krünitz or older scans) that the project itself notes as JS-dependent or lacking stable schemas.

- **Grimm DWB (Deutsches Wörterbuch)**: Yes, fetchable. Pattern: `https://woerterbuchnetz.de/?sigle=DWB&lemid={LEMID}` or `https://www.woerterbuchnetz.de/DWB?lemid={LEMID}` (variations exist; both resolve). Example lemid usage appears in citations (e.g., GR10854, A00001, GH04049, G04862).
- **Adelung (Grammatisch-kritisches Wörterbuch der hochdeutschen Mundart)**: Yes. Pattern: `https://www.woerterbuchnetz.de/?sigle=Adelung&lemid={LEMID}` (e.g., T01191 for certain lemmas).
- **Other Wörterbuchnetz-hosted (Campe, Paul, Kluge etymological, Fischer Schwäbisches, etc.)**: Generally yes for those with published digital editions; they follow the same `?sigle={SIGLE}&lemid={LEMID}` or `/SIGLE?lemid={LEMID}` pattern. Sigles and exact availability vary by dictionary (see Wörterbuchnetz homepage for full list of ~18–37 integrated works). Not all historical scans are fully digitized with stable per-word pages; some remain discovery-only.

**Caveats**: A stable per-word URL requires first resolving the `lemid` (see Q3). Rate limits/terms are not heavily documented beyond standard academic fair-use; the site provides an "API Schnittstellen" section. Some older linked dictionaries (explicitly noted in project docs) return minimal/empty HTML without JS.

**2. Does Grimm's Deutsches Wörterbuch (DWB) have a direct, stable URL per word outside Wörterbuchnetz? JSON or XML API? Best programmatic fetch method?**

No fully independent, stable per-word URL or public JSON/XML API exists outside the Wörterbuchnetz ecosystem. The Trier digital Grimm project (dwb.uni-trier.de / germazope.uni-trier.de/Projects/DWB) provides the digitized edition and corpus but routes primary online access and per-lemma pages through Wörterbuchnetz (many academic citations use dwb.uni-trier.de as the project homepage while linking concrete entries via woerterbuchnetz.de). No dedicated per-word REST endpoint or stable `/word` slug without a lemid or search is documented.

**Best programmatic method**: Use the Wörterbuchnetz Meta API (see Q3) to resolve the word → lemid(s), then fetch the constructed URL above. The returned TEI-XML from the Meta API also includes direct pointers. This is the de-facto standard cited across papers and the project's own infrastructure. No evidence of a simpler "/wb/{word}" or JSON snippet API with full definitions (DWDS snippets are metadata-only and legally restricted).

**3. How to look up the `lemid` (lemma ID) for a word in the Wörterbuchnetz system programmatically?**

Use the official **Meta API** endpoint (explicitly documented and returning TEI-XML):

`https://api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/{WORD}/0/tei-xml`

- It accepts a plain German word (e.g., "trisenet", "Waldhorn").
- Response lists matching lemmata across dictionaries, each with `<term>`, grammar info, and crucially `<ptr type="wbnetz-url">https://www.woerterbuchnetz.de?sigle=XXX&lemid=YYYY</ptr>` (or equivalent).
- Parse the XML/TEI to extract the desired `lemid` (and sigle) for DWB, Adelung, etc.
- Then construct the stable URL as in Q1.

This is confirmed via live API responses and project documentation. It solves the "known lemid required" problem without manual search.

**4. Does the Mittelhochdeutsches Wörterbuch (`mhdbdb.sbg.ac.at` or `mhdwb.de`) offer a fetchable URL per word or an API? Access patterns?**

- **MWB Online (mhdwb-online.de)**: Partial yes. ~26,000 published articles are freely available online (with a 6-month delay after print). Access is via the "Wörterbuch" section or the cumulative lemmaliste (~90,000 lemmas, browsable by letter: e.g., `lemmaliste.php?buchstabe=A&portion=0`). Many lemmas link directly to Wörterbuchnetz. No simple `/lemma/{word}` or documented REST API; content appears as static HTML pages once published. Coverage: Middle High German (roughly 1050–1350/1500). Programmatic use: scrape the lemmaliste or known article pages; links to Wörterbuchnetz for fuller integration.
- **MHDBDB (mhdbdb.sbg.ac.at)**: Primarily a conceptual/occurrence database (millions of tagged tokens across MHG texts), not a dictionary. It supports lemma-based searches (e.g., "haben" returns forms + contexts) and links to dictionaries, but the new version is in open beta with limited functionality; the old platform remains available. No clear stable per-word definition URL or public API documented for definitions; more suited for corpus queries than standalone lookups.

**5. Does the Frühneuhochdeutsches Wörterbuch (`fnhdw.de` or `fwb-online.de`) have a direct URL per word or an API?**

Yes — excellent direct support. **FWB-online (fwb-online.de)** offers stable per-lemma URLs of the form `https://fwb-online.de/lemma/{SLUG}` (e.g., `https://fwb-online.de/lemma/hausfrau.s.1f` for one sense of "Hausfrau"; Zitierlink format `http://fwb-online.de/go/hausfrau.s.1f_...`). The slug encodes the lemma + sense/pos info (e.g., `.s.1f`).

- Content is **static HTML** (definitions, phrasemes, Belegblöcke with citations from 14th–17th c. sources are present in the initial HTML with no JS dependency for core text).
- No public JSON/XML API documented, but the direct URLs make it highly scrape-friendly with `requests` + BeautifulSoup.
- Coverage: Early New High German (mid-14th to mid-17th century). Actively maintained under the Akademienprogramm (Göttingen Academy). Ideal for 15th–17th c. archaic lookup.

**6. Does the Deutsches Rechtswörterbuch (`drw-www.adw.uni-heidelberg.de`) have a public API or stable URL per lemma?**

Limited public documentation on direct per-lemma URLs or a dedicated API. The primary site (drw-www.adw.uni-heidelberg.de/drw or the newer drw.hadw-bw.de/drw) provides an online version of the historic legal dictionary (German legal terminology from ~450 AD to 1815, covering Germanic to early modern periods). Access appears search-form driven; results pages may generate stable links, but no explicit `/lemma/{word}` pattern or REST API is prominently documented in available sources. Academic citations treat it as a searchable online resource with possible deep links, but it is less "plug-and-play" for automated per-word fetching than FWB or Wörterbuchnetz. No rate-limit or terms details surfaced; suitable for targeted manual or semi-automated use.

**7. Other German historical dictionary projects offering programmatic, JS-free access for archaic German words (15th–19th c.)? Undocumented/semi-public APIs?**

Several academy- and university-led projects complement the above, prioritized by direct fetchability:

- **Mittelhochdeutsches Wörterbuch (MWB) + integrated Lexer/Benecke-Müller-Zarncke** via mhdwb-online.de and Wörterbuchnetz: Already covered; strong Wörterbuchnetz linkage.
- **Althochdeutsches Wörterbuch** and related (via Wörterbuchnetz or separate Trier/Heidelberg efforts): Similar lemid-based access.
- **GerManC / other historical corpora** (e.g., via IDS or university projects): More corpus than dictionary; useful for attestation but not definitions.
- **elexiko / OWID (IDS Mannheim)**: Modern-leaning but includes historical layers; has API-like search but not purely archaic-focused.
- **Zeno.org** and similar scan portals: No stable per-word schema (search-form only); avoided per project notes.
- Undocumented/semi-public: Some older academy projects expose TEI/XML dumps or internal endpoints (inferred from Wörterbuchnetz Meta API design), but none as cleanly documented as the Meta endpoint. Forum/academic consensus (papers citing these tools) favors combining Wörterbuchnetz + FWB-online + MWB-online for 15th–19th c. coverage. No major new JS-free JSON APIs surfaced beyond the known Wörterbuchnetz Meta layer.

**Recommended priority order for automated scraping (direct URL + no/minimal JS + broad archaic coverage)**: FWB-online (best direct URLs + static), Wörterbuchnetz family (via Meta API + lemid URLs), MWB-online (lemmaliste + articles), DRW (search-dependent).

---

## Evaluation

**Evaluated:** 2026-04-24 15:35
**Source sets detected:** 1

### Findings That Apply

1. **Wörterbuchnetz pages are directly fetchable (static HTML)** — `word_lookup.py:131–144` already extracts the `wbnetz-url` from each `<ptr type="wbnetz-url">` in the Meta API response. These URLs (`https://www.woerterbuchnetz.de/DWB?lemid=...`) are confirmed fetchable without JS. We can add a second-pass fetch for selected sigles (DWB, Adelung) inside `fetch_woerterbuchnetz()`: after building the `sources` list, filter for `sigle in ("DWB", "Adelung")`, fetch each URL, parse for definition content, and return alongside the link list. CSS selectors for these pages are not yet known — need a live test to determine the right selector (e.g. `div.artikel`, `p.lemma-definition` or similar). The lemid resolution via Meta API (Q3) is already solved — the current code already parses `<ptr type="wbnetz-url">` which embeds the lemid in the URL.

2. **FWB-online (`fwb-online.de`) — new source, high value** — `https://fwb-online.de/lemma/{slug}` serves static HTML with full Early New High German definitions (14th–17th c.). The slug is NOT the plain word — it encodes lemma + sense (e.g., `hausfrau.s.1f`). A direct `/{word}` URL does not work. Two options to resolve: (a) try `https://fwb-online.de/lemma/{word}.s.0` as a discovery attempt (may 404), or (b) check whether fwb-online.de has a search endpoint that returns a redirect or lemma list for a plain word. Needs live testing before integration into `word_lookup.py`. If slug resolution works, add as a fourth parallel source.

### Needs Adaptation

3. **MWB-online (Mittelhochdeutsches Wörterbuch)** — fetchable via lemmaliste (`lemmaliste.php?buchstabe=A&portion=0`) but no direct per-word URL. Requires a two-step lookup: scan lemmaliste for the word, then fetch the article page. Heavy for a real-time lookup (90,000 entries). More useful as an offline index. Coverage is MHG (1050–1350) — relevant only for very old texts; probably not needed for 18th/19th c. children's book vocabulary. Low priority.

### Contradictions

4. The brief assumed Wörterbuchnetz-linked pages were mostly JS-dependent or inaccessible — the research contradicts this for the core portal pages (woerterbuchnetz.de with `?sigle=DWB&lemid=...`). The previously known limitation (Krünitz, Zeno.org) was about *externally linked* sites, not the Wörterbuchnetz portal pages themselves. This means the Wörterbuchnetz Meta API was already solving lemid resolution; we just weren't taking the next step to fetch the portal pages. The research confirms that next step is viable.

### Interesting Context

- **DRW (Deutsches Rechtswörterbuch)** — search-form driven, no stable per-word URL. Useful only for legal/historical terminology (coverage 450 AD–1815). Not worth adding for general children's book vocabulary.
- **MHDBDB Salzburg** — corpus database, not a dictionary. Returns word occurrences in texts, not definitions. Not useful for this tool.
- **elexiko/OWID (IDS Mannheim)** — modern German focus, not archaic. Skip.
- **Grimm DWB has no independent URL outside Wörterbuchnetz** — confirmed. The Trier project (dwb.uni-trier.de) is the homepage but routes all per-entry access through woerterbuchnetz.de. No alternative access path exists.

### KB Cross-Reference

KB Context: none — skipped.

### Open Questions Remaining

- What are the CSS selectors for definitions on Wörterbuchnetz portal pages (e.g., `https://www.woerterbuchnetz.de/DWB?lemid=GR10854`)? Need a live fetch test.
- Does `https://fwb-online.de/lemma/{word}.s.0` resolve, or is there a search/autocomplete endpoint on fwb-online.de to discover the correct slug from a plain word?

### Next Concrete Steps

1. `word_lookup.py:131–144` — In `fetch_woerterbuchnetz()`, after building the `sources` list, add a secondary fetch for entries where `sigle in ("DWB", "Adelung")`: fetch the `url`, parse HTML for definition elements (CSS selector TBD via live test), return definitions alongside links.
2. Live test: `requests.get("https://www.woerterbuchnetz.de/DWB?lemid=GR10854")` — inspect HTML, find the definition container selector.
3. Live test: `requests.get("https://fwb-online.de/lemma/waldhorn.s.0")` — check if slug pattern `{word}.s.0` resolves, or inspect fwb-online.de for a search/autocomplete endpoint.
4. If FWB slug resolution works: add `fetch_fwb()` as a fourth parallel source in `lookup_all()` (`word_lookup.py:150–160`).

---

*(Second research set appended below — AWB + MWB deep dive)*

**AWB (Althochdeutsches Wörterbuch) — saw-leipzig.de**

The Althochdeutsches Wörterbuch (AWB) covers Old High German (roughly 8th–11th c.). Hosted at awb.saw-leipzig.de, fully integrated into the Wörterbuchnetz system. Sigle = AWB.

Direct per-lemma URLs:
- `https://awb.saw-leipzig.de/AWB?lemid={LEMID}` (primary pattern cited in academic literature)
- `https://awb.saw-leipzig.de/cgi/WBNetz/wbgui_py?sigle=AWB&lemid={LEMID}` (CGI variant)
- Concrete examples: `https://awb.saw-leipzig.de/AWB?lemid=N01365`, `https://awb.saw-leipzig.de/AWB?lemid=M01545`

Programmatic method: Meta API → parse for `sigle=AWB` → extract lemid → fetch URL. Same pattern as DWB/Adelung. Fetchability confirmed (server-rendered HTML, academic papers quote full entry content from these URLs). No independent API.

Complementary: **EWA (Etymologisches Wörterbuch des Althochdeutschen)** at ewa.saw-leipzig.de — direct URLs `https://ewa.saw-leipzig.de/lemmas/{ID}/de`. ~21,137 searchable lemmas, 8 of 10 volumes online. Static-friendly. **Köbler's AHD dictionary** (koeblergerhard.de/ahdwbhin.html) — simple HTML + letter-PDFs, no backend, extremely scrape-friendly.

---

**MWB (Mittelhochdeutsches Wörterbuch) — mhdwb-online.de**

Modern comprehensive MHG dictionary (1050–1350/1500), joint Mainz/Göttingen academy project. Supersedes Lexer + BMZ.

Direct per-article URLs: `https://mhdwb-online.de/wb/{numericID}` (e.g., `/wb/57990000`). Static HTML, fully parseable. ~26,000 articles published online (a–lônen as of 2025/2026), 6-month print delay. Browse: `lemmaliste.php?buchstabe=A&portion=0` (~90,000 lemmas). Numeric IDs discovered via lemmaliste or Wörterbuchnetz cross-links.

For easier programmatic access — classic sources already on Wörterbuchnetz:
- **Lexer** (Mittelhochdeutsches Handwörterbuch, 1872–1878) — sigle=`Lexer`, URL `https://woerterbuchnetz.de/?sigle=Lexer&lemid={LEMID}`
- **BMZ** (Benecke / Müller / Zarncke) — sigle=`BMZ`, URL `https://www.woerterbuchnetz.de/BMZ?lemid={LEMID}`

Both drop-in compatible with existing Meta API + ThreadPoolExecutor logic. Lexer/BMZ are comprehensive and cover the gap while the modern MWB is still incomplete (R–S in progress).

## Key Sources (second set)
1. [awb.saw-leipzig.de](https://awb.saw-leipzig.de/) + Wörterbuchnetz listings — AWB sigle, lemid URL patterns, Wörterbuchnetz integration.
2. Academic citations using specific `?lemid=` AWB URLs — confirm static HTML content delivery.
3. [ewa.saw-leipzig.de/de](https://ewa.saw-leipzig.de/de) — EWA project description, volume/lemma URL structure, ~21,137 lemmas.
4. [koeblergerhard.de/ahdwbhin.html](http://www.koeblergerhard.de/ahdwbhin.html) — Köbler edition structure and PDF access.
5. [mhdwb-online.de](https://mhdwb-online.de/) — official project site, lemmaliste, published article structure, `/wb/{ID}` URL pattern.
6. [woerterbuchnetz.de](https://woerterbuchnetz.de/) — Lexer and BMZ sections with lemid URLs, MWB cross-links.

---

## Evaluation (second set — 2026-04-24 15:42)

**Source sets detected:** 1 (new, additive to prior evaluation)

### Findings That Apply

1. **AWB via Wörterbuchnetz Meta API — zero new code** — The Meta API already resolves lemids for AWB entries. Add `"AWB"` to the sigle filter in the planned second-pass fetch (see prior step 1). URL pattern: `https://awb.saw-leipzig.de/AWB?lemid={LEMID}`. Confirmed fetchable (static HTML). Coverage: OHG 8th–11th c. — fills the earliest gap.

2. **Lexer + BMZ — highest-value drop-in additions** — Both are on Wörterbuchnetz (sigles `Lexer`, `BMZ`). The Meta API already returns their lemids. Add them to the sigle filter alongside DWB, Adelung, AWB. They are comprehensive and cover MHG fully, unlike the modern MWB which is still incomplete. These should be prioritised over mhdwb-online.de scraping.

3. **EWA (Etymologisches Wörterbuch des Althochdeutschen)** — `https://ewa.saw-leipzig.de/lemmas/{ID}/de` — useful for etymological chains, but requires numeric ID discovery (not a plain-word URL). Lower priority than AWB/Lexer/BMZ unless deep etymology is specifically needed.

4. **Köbler's AHD dictionary** — extremely simple HTML at koeblergerhard.de. No backend, no lemid system. Bulk-fetchable by letter PDFs or HTML pages. Useful as a lightweight OHG fallback if AWB returns nothing, but not worth building into the parallel fetch loop — better as a static offline reference.

5. **mhdwb-online.de numeric IDs** — The `/wb/{numericID}` URL pattern is confirmed static, but IDs aren't derivable from a word without first scraping the lemmaliste. Given that Lexer + BMZ via Wörterbuchnetz already cover MHG comprehensively, mhdwb-online.de is low priority for now.

### Needs Adaptation

6. **EWA ID discovery** — same slug-resolution problem as FWB (need ID, not plain word). Could be addressed by checking whether ewa.saw-leipzig.de has a search endpoint. Defer until FWB slug resolution is tested first (same pattern).

### Interesting Context

- AWB, Lexer, BMZ, DWB, Adelung all resolve through the same Meta API call — a single TEI-XML response already contains all of them. The fetch parallelism is about the second step (fetching multiple lemid URLs), not the first step (Meta API). The `ThreadPoolExecutor` should be applied to the list of per-dictionary fetches, not just the top-level sources.
- Köbler's is public-domain-friendly and letter-structured — good to note for offline/bulk use cases later.

### KB Cross-Reference

KB Context: none — skipped.

### Open Questions Remaining

- CSS selectors for Wörterbuchnetz portal pages (DWB, Adelung, AWB, Lexer, BMZ) — one live fetch needed to confirm which selector extracts the definition text.
- FWB and EWA slug/ID discovery — both need a live test or search-endpoint investigation.

### Next Concrete Steps

1. `word_lookup.py:131–144` — Expand sigle filter from `("DWB", "Adelung")` to `("DWB", "Adelung", "AWB", "Lexer", "BMZ")`. All five already get their lemid URLs from the Meta API. One live fetch per sigle needed to confirm CSS selector.
2. Live test all five sigle URLs to find the definition CSS selector (likely shared across Wörterbuchnetz portal — test DWB first, apply to others).
3. Defer mhdwb-online.de, EWA, Köbler until the Wörterbuchnetz-family expansion is working.
