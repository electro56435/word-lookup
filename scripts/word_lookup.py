#!/usr/bin/env python3
"""
Wort-Lookup Pipeline - Robust für KI-Modelle / Agents
======================================================

Quellen (parallel):
1. Wiktionary DE  — MediaWiki API, strukturierte Bedeutungen + Etymologie
2. DWDS           — HTML-Scraping, moderne + historische Definitionen
3. Wörterbuchnetz — Meta-API → DWB, Adelung, AWB, Lexer, BMZ (parallel)
4. FWB-online     — Frühneuhochdeutsch (slug-basiert, best-effort)

Output: sauberes JSON-Dict — konsistent für jeden Agent/Modell.
"""

import argparse
import html
import json
import re
import shutil
import sys
import time
from pathlib import Path
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# ── Einstellungen ──────────────────────────────────────────────────────────────
TIMEOUT        = 8
MAX_RETRIES    = 2
SLEEP_BETWEEN  = 0.4
HEADERS        = {"User-Agent": "Mozilla/5.0 (compatible; WortLookupBot/1.0)"}
TEI_NS         = "https://www.tei-c.org/ns/1.0"
WBNETZ_SIGLES  = ("DWB", "Adelung", "AWB", "Lexer", "BMZ")
WBNETZ_METHODS = {"BMZ": "definition"}  # Lexer uses fulltext (definition returns only compounds)
WBNETZ_API     = "https://api.woerterbuchnetz.de/open-api/dictionaries"
WBNETZ_HDRS    = {"Accept": "application/json", "User-Agent": "Mozilla/5.0 (compatible; WortLookupBot/1.0)"}
KWIC_MAX       = 15  # max KWIC windows fetched per entry
_PROJECT_ROOT  = Path(__file__).resolve().parent.parent
HISTORY_FILE   = str(_PROJECT_ROOT / "recherche_verlauf.md")

STATIC_SOURCES = ["wiktionary", "dwds", "fwb", "openthesaurus"]
WBNETZ_SOURCE_KEYS = [f"wbnetz_{s.lower()}" for s in WBNETZ_SIGLES]
ALL_SOURCES = STATIC_SOURCES + WBNETZ_SOURCE_KEYS

_cache: Dict[str, Any] = {}


# ── Robuster HTTP-Helfer ───────────────────────────────────────────────────────

def _cache_key(url: str, params: Optional[Dict] = None) -> str:
    """Stable key including query string so different params are not conflated."""
    prep = requests.Request("GET", url, params=params or {}).prepare()
    return prep.url or url


def safe_get(url: str, params: Optional[Dict] = None, is_json: bool = False) -> Dict[str, Any]:
    """Holt eine Seite oder JSON mit Wiederholungen und Fehlerschutz."""
    key = _cache_key(url, params)
    if key in _cache:
        return _cache[key]
    for attempt in range(MAX_RETRIES):
        try:
            time.sleep(SLEEP_BETWEEN)
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            result = {"success": True, "data": r.json() if is_json else r.text, "error": None}
            _cache[key] = result
            return result
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                return {"success": False, "data": None, "error": str(e)}
            time.sleep(0.5 * (attempt + 1))
    return {"success": False, "data": None, "error": "Unbekannter Fehler"}


def clean_text(text: str, maxlen: int = 2000) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()[:maxlen]


def _strip_invisible_html(soup: BeautifulSoup) -> None:
    """Entfernt script/noscript/style, damit get_text() keinen JS-Boilerplate inkl. «JavaScript aktivieren» liefert."""
    for tag in soup.find_all(["script", "noscript", "style"]):
        tag.decompose()


# ── Wiktionary ────────────────────────────────────────────────────────────────

def fetch_wiktionary(word: str) -> Dict[str, Any]:
    """Wiktionary DE — strukturierte Bedeutungen + Etymologie aus Wikitext."""
    r = safe_get(
        "https://de.wiktionary.org/w/api.php",
        params={
            "action": "query", "titles": word,
            "prop": "revisions", "rvprop": "content", "rvslots": "main",
            "format": "json", "formatversion": 2,
        },
        is_json=True,
    )
    if not r["success"]:
        return {"source": "wiktionary", "success": False, "error": r["error"]}

    try:
        pages = r["data"].get("query", {}).get("pages", [])
        if not pages or "missing" in pages[0]:
            return {"source": "wiktionary", "success": False, "error": "Wort nicht gefunden"}

        wikitext = pages[0]["revisions"][0]["slots"]["main"]["content"]

        def clean_wiki(text: str) -> str:
            text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
            text = re.sub(r"<ref\b.*", "", text, flags=re.S)
            text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
            text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
            text = re.sub(r"\{\{[^}]+\}\}", "", text)
            text = re.sub(r"'{2,}", "", text)
            return re.sub(r"\s+", " ", text).strip()

        definitions: List[str] = []
        m = re.search(r"\{\{Bedeutungen\}\}\s*(.*?)(?=\{\{|\Z)", wikitext, re.S)
        if m:
            definitions = [
                d for d in (
                    re.sub(r":\[\d+[a-z]?\]\s*", "", clean_wiki(line)).strip()
                    for line in m.group(1).splitlines()
                    if re.match(r":\[\d", line.strip())
                ) if d
            ]

        etymology = ""
        em = re.search(r"\{\{Herkunft\}\}\s*(.*?)(?=\{\{|\Z)", wikitext, re.S)
        if em:
            etymology = clean_wiki(em.group(1)).split("\n")[0].strip(":").strip()

        return {
            "source": "wiktionary",
            "success": bool(definitions),
            "definitions": definitions,
            "etymology": etymology,
            "error": None if definitions else "Keine Bedeutungen gefunden",
        }
    except Exception as e:
        return {"source": "wiktionary", "success": False, "error": str(e)}


# ── DWDS ──────────────────────────────────────────────────────────────────────

def fetch_dwds(word: str) -> Dict[str, Any]:
    """DWDS — moderne + historische Definitionen via HTML-Scraping."""
    r = safe_get(f"https://www.dwds.de/wb/{requests.utils.quote(word)}")
    if not r["success"]:
        return {"source": "dwds", "success": False, "error": r["error"]}

    try:
        soup = BeautifulSoup(r["data"], "html.parser")
        _strip_invisible_html(soup)
        definitions = [
            clean_text(el.get_text(" ", strip=True))
            for el in soup.select(".dwdswb-definition")
            if el.get_text(strip=True)
        ]
        wortart_el = soup.select_one(".dwdswb-ft-block .dwdswb-gram")
        etym_el    = soup.select_one(".dwdswb-ft-block .dwdswb-etym")
        return {
            "source": "dwds",
            "success": bool(definitions),
            "definitions": definitions,
            "word_class": wortart_el.get_text(strip=True) if wortart_el else "",
            "etymology": clean_text(etym_el.get_text(" ", strip=True)) if etym_el else "",
            "error": None if definitions else "Keine Definitionen gefunden",
        }
    except Exception as e:
        return {"source": "dwds", "success": False, "error": str(e)}


# ── Wörterbuchnetz ────────────────────────────────────────────────────────────

def fetch_woerterbuchnetz_meta(word: str) -> List[Dict[str, str]]:
    """Meta-API: liefert lemid + URL für jeden gefundenen Sigle-Eintrag."""
    r = safe_get(
        f"https://api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/"
        f"{requests.utils.quote(word)}/0/tei-xml"
    )
    if not r["success"] or not r["data"]:
        return []

    try:
        root = ET.fromstring(r["data"])
    except ET.ParseError:
        return []

    ns = {"tei": TEI_NS}
    entries = []
    for item in root.findall(".//tei:item", ns):
        sigle_el = item.find(".//tei:abbr[@type='wbnetz-sigle']", ns)
        ptr_el   = item.find(".//tei:ptr[@type='wbnetz-url']", ns)
        if sigle_el is None or ptr_el is None:
            continue
        sigle = (sigle_el.text or "").strip()
        url   = (ptr_el.text or "").strip().replace("&amp;", "&")
        if sigle in WBNETZ_SIGLES and url:
            m = re.search(r"lemid=([A-Z0-9]+)", url)
            lemid = m.group(1) if m else ""
            entries.append({"sigle": sigle, "lemid": lemid, "url": url})
    return entries


def fetch_woerterbuchnetz_entry(sigle: str, word: str) -> Dict[str, Any]:
    """Holt einen Wörterbuchnetz-Eintrag via open-api + KWIC-Reconstruction.

    Verwendet 'definition' für Lexer/BMZ, 'fulltext' für alle anderen.
    Filtert auf exakte Lemma-Treffer und rekonstruiert den Artikeltext
    aus bis zu KWIC_MAX parallelen KWIC-Fenstern (sortiert nach textid).
    """
    source_key = f"wbnetz_{sigle.lower()}"
    method = WBNETZ_METHODS.get(sigle, "fulltext")

    url = f"{WBNETZ_API}/{sigle}/{method}/{requests.utils.quote(word)}"
    data = None
    for attempt in range(2):
        try:
            r = requests.get(url, headers=WBNETZ_HDRS, timeout=TIMEOUT)
            if r.status_code >= 500 and attempt == 0:
                time.sleep(1.0)
                continue
            r.raise_for_status()
            data = r.json()
            break
        except Exception as e:
            if attempt == 1:
                return {"source": source_key, "success": False, "error": str(e)}
            time.sleep(1.0)
    if data is None:
        return {"source": source_key, "success": False, "error": "Keine Antwort vom Server"}

    rs = data.get("result_set", [])
    exact = [x for x in rs if x.get("lemma", "").lower() == word.lower()]
    if not exact:
        return {"source": source_key, "success": False, "error": "Kein passender Lemma-Eintrag"}

    # Fetch KWIC windows for earliest textids (article start = most definition-dense)
    windows = sorted(exact, key=lambda x: int(x.get("textid", 0)))[:KWIC_MAX]

    def _fetch_kwic(kwic_url: str) -> List[Dict]:
        try:
            rk = requests.get(kwic_url, headers=WBNETZ_HDRS, timeout=TIMEOUT)
            rk.raise_for_status()
            return rk.json().get("result_set", [])
        except Exception:
            return []

    token_map: Dict[int, str] = {}
    with ThreadPoolExecutor(max_workers=min(len(windows), 6)) as ex:
        futs = [ex.submit(_fetch_kwic, w["wbnetzkwiclink"]) for w in windows]
        for fut in as_completed(futs):
            for tok in fut.result():
                tid = int(tok.get("textid", 0))
                token_map[tid] = html.unescape(tok.get("word", ""))

    text = clean_text(
        " ".join(w for _, w in sorted(token_map.items()) if w.strip()),
        maxlen=3000,
    )
    return {
        "source": source_key,
        "success": bool(text),
        "definitions": [text] if text else [],
        "etymology": "",
        "error": None if text else "Kein Artikeltext gefunden",
    }


# ── FWB-online ────────────────────────────────────────────────────────────────


_FWB_BEDEUTUNGSINDEX = re.compile(r"Bedeutungsindex\s*»([^«]+)«", re.IGNORECASE)


def _fwb_index_lemma_mismatches_query(word: str, text: str) -> bool:
    """
    True, wenn der Artikel offenbar zu einem anderen Lemma gehört (z. B. Verweis »rümpfen« bei Suche »Rümpf«).
    Kein Treffer im Snippet → False (nicht ablehnen).
    """
    if not word or not text:
        return False
    m = _FWB_BEDEUTUNGSINDEX.search(text[:500])
    if not m:
        return False
    indexed = m.group(1).strip().casefold()
    q = word.strip().casefold()
    return indexed != q


def _sanitize_fwb_if_wrong_lemma(word: str, r: Dict[str, Any]) -> Dict[str, Any]:
    """Markiert FWB-Ergebnis als fehlgeschlagen, wenn Bedeutungsindex nicht zum Suchwort passt."""
    if not r.get("success"):
        return r
    defs = r.get("definitions") or []
    t = defs[0] if defs else ""
    if not _fwb_index_lemma_mismatches_query(word, t):
        return r
    out = {**r}
    out["success"] = False
    out["definitions"] = []
    out["error"] = (
        f"FWB-Artikel passt nicht zum Lemma „{word}“ (Bedeutungsindex weicht ab — vermutlich anderer Eintrag)."
    )
    out["fwb_lemma_mismatch"] = True
    return out


def _fwb_needs_agent_browser(r: Dict[str, Any]) -> bool:
    """True, wenn HTTP-Scrape fehlgeschlagen ist oder offenbar kein echter Artikel (JS-Hülle)."""
    if not r.get("success"):
        return True
    t = (r.get("definitions") or [""])[0].strip()
    if len(t) < 50:
        return True
    low = t.lower()
    if "javascript" in low and any(
        s in low for s in ("aktivier", "einschalt", "bitte", "enable", "turn on")
    ):
        return True
    return False


def _fetch_fwb_http(word: str) -> Dict[str, Any]:
    """FWB-online — Frühneuhochdeutsch. Slug via Search-HTML, dann Lemma-Seite scrapen (nur requests)."""
    search = safe_get(
        "https://fwb-online.de/search",
        params={"q": word.lower(), "type": "lemma"},
    )
    if not search["success"]:
        return {"source": "fwb", "success": False, "error": "Suche fehlgeschlagen"}

    try:
        soup = BeautifulSoup(search["data"], "html.parser")
        _strip_invisible_html(soup)
        prefix = f"/lemma/{word.lower()}."
        link = next(
            (a["href"] for a in soup.find_all("a", href=True) if a["href"].startswith(prefix)),
            None,
        )
        if not link:
            return {"source": "fwb", "success": False, "error": "Kein Lemma gefunden"}

        slug_path = link.split("?")[0]
        r = safe_get(f"https://fwb-online.de{slug_path}")
        if not r["success"]:
            return {"source": "fwb", "success": False, "error": "Lemma-Seite nicht erreichbar"}

        page = BeautifulSoup(r["data"], "html.parser")
        _strip_invisible_html(page)
        article = page.find(class_="artikel") or page.find("article") or page.find("main")
        text = clean_text(article.get_text(" ", strip=True) if article else page.get_text(), maxlen=2500)
        return _sanitize_fwb_if_wrong_lemma(
            word,
            {
                "source": "fwb",
                "success": bool(text),
                "definitions": [text] if text else [],
                "etymology": "",
                "error": None if text else "Kein Artikeltext gefunden",
            },
        )
    except Exception as e:
        return {"source": "fwb", "success": False, "error": str(e)}


def fetch_fwb(word: str) -> Dict[str, Any]:
    """FWB: zuerst HTTP; bei Fehler/JS-Hülle optional `agent-browser`-Fallback (wenn im PATH)."""
    r = _fetch_fwb_http(word)
    if not _fwb_needs_agent_browser(r):
        return r
    if not shutil.which("agent-browser"):
        out = {**r}
        out["fwb_browser_unavailable"] = "agent-browser nicht im PATH"
        return out
    try:
        from fwb_agent_browser import fetch_fwb_with_agent_browser

        br = fetch_fwb_with_agent_browser(word)
        if br.get("success"):
            br["fetched_via"] = "agent-browser"
            return _sanitize_fwb_if_wrong_lemma(word, br)
        return {**r, "fwb_browser_fallback": br}
    except Exception as e:
        return {**r, "fwb_browser_error": str(e)}


# ── OpenThesaurus ─────────────────────────────────────────────────────────────

def fetch_openthesaurus(word: str) -> Dict[str, Any]:
    """OpenThesaurus — Synonyme für moderne deutsche Wörter."""
    r = safe_get(
        "https://www.openthesaurus.de/synonyme/search",
        params={"q": word, "format": "application/json"},
        is_json=True,
    )
    if not r["success"]:
        return {"source": "openthesaurus", "success": False, "error": r["error"]}
    try:
        synsets = r["data"].get("synsets", [])
        synonyms: List[str] = []
        for s in synsets[:3]:
            synonyms.extend(t["term"] for t in s.get("terms", []))
        synonyms = list(dict.fromkeys(synonyms))[:8]
        return {
            "source": "openthesaurus",
            "success": bool(synonyms),
            "definitions": [", ".join(synonyms)] if synonyms else [],
            "etymology": "",
            "error": None if synonyms else "Keine Synonyme gefunden",
        }
    except Exception as e:
        return {"source": "openthesaurus", "success": False, "error": str(e)}


# ── Hauptfunktion ─────────────────────────────────────────────────────────────

def _best_definition(sources: Dict[str, Any]) -> Dict[str, Any]:
    """Wählt die längste/reichste Definition aus — Wörterbuchnetz-Quellen erhalten 1.5x Bonus."""
    best: Optional[Dict] = None
    best_score = 0
    for key, data in sources.items():
        if not data.get("success"):
            continue
        defs = data.get("definitions", [])
        text = defs[0] if defs else ""
        score = len(text) * (1.5 if "wbnetz" in key else 1.2 if "wiktionary" in key else 1.0)
        if score > best_score:
            best_score = score
            best = {"source": data.get("source", key), "definition": text[:1500], "score": round(score, 1)}
    return best or {"source": "none", "definition": "", "score": 0}


_ABBREV_MAP = [
    (re.compile(r'\bahd\.'),  'althochdeutsch'),
    (re.compile(r'\bmhd\.'),  'mittelhochdeutsch'),
    (re.compile(r'\bnhd\.'),  'neuhochdeutsch'),
    (re.compile(r'\balts\.'), 'altsächsisch'),
    (re.compile(r'\bmnd\.'),  'mittelniederdeutsch'),
    (re.compile(r'\bmnl\.'),  'mittelniederländisch'),
    (re.compile(r'\bfries\.'),'friesisch'),
    (re.compile(r'\bgot\.'),  'gotisch'),
    (re.compile(r'\blat\.'),  'lateinisch'),
    (re.compile(r'\bgr\.'),   'griechisch'),
    (re.compile(r'\bndl\.'),  'niederländisch'),
    (re.compile(r'\bengl\.'), 'englisch'),
    (re.compile(r'\bfrz\.'),  'französisch'),
    (re.compile(r'\bvgl\.'),  'vergleiche'),
    (re.compile(r'\bvb\.\s*'),'Verb '),
    (re.compile(r'\badj\.\s*'),'Adjektiv '),
    (re.compile(r'\badv\.\s*'),'Adverb '),
    # grammatische Markierungen (stf., swm. etc.) entfernen
    (re.compile(r'\bst[fmn]\.\s*'), ''),
    (re.compile(r'\bsw[fmn]\.\s*'), ''),
]


def _expand_abbreviations(text: str) -> str:
    for pattern, replacement in _ABBREV_MAP:
        text = pattern.sub(replacement, text)
    return text


def save_to_history(result: Dict[str, Any]) -> None:
    """Hängt das Recherche-Ergebnis formatiert an HISTORY_FILE an."""
    try:
        best = result.get("best_definition", {})
        definition = _expand_abbreviations(best.get("definition", "").strip())
        if not definition or best.get("score", 0) == 0:
            return
        source = best.get("source", "unbekannt")
        timestamp = result.get("timestamp", "")[:16]  # "2026-04-24 16:35"
        word = result.get("word", "")
        summary = result.get("summary", "")
        count_match = re.search(r"(\d+) Quellen", summary)
        count = count_match.group(1) if count_match else "?"
        if len(definition) > 280:
            cutoff = definition.rfind(" ", 0, 280)
            definition = definition[:cutoff if cutoff > 0 else 280] + " …"
        entry = (
            f"## {word} — {timestamp}\n\n"
            f"**Definition:** {definition}\n\n"
            f"**Quelle:** {source} · {count} Quellen\n\n"
        )
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception as e:
        print(f"Warnung: Verlauf konnte nicht gespeichert werden: {e}", file=sys.stderr)


def lookup_word(word: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
    """Schlägt ein Wort in allen Quellen parallel nach.

    sources: optionale Liste von Quell-Keys (z.B. ["wiktionary", "wbnetz_dwb"]).
             None = alle Quellen.
    """
    src_filter = set(sources) if sources else None

    # Meta-API zuerst (synchron) — Voraussetzung für Wörterbuchnetz-Fetches
    wbnetz_entries = fetch_woerterbuchnetz_meta(word)

    tasks: Dict[str, Any] = {}
    for key, fn in {
        "wiktionary":    lambda: fetch_wiktionary(word),
        "dwds":          lambda: fetch_dwds(word),
        "fwb":           lambda: fetch_fwb(word),
        "openthesaurus": lambda: fetch_openthesaurus(word),
    }.items():
        if src_filter is None or key in src_filter:
            tasks[key] = fn

    seen_sigles: set = set()
    for entry in wbnetz_entries:
        if entry["sigle"] in seen_sigles:
            continue
        seen_sigles.add(entry["sigle"])
        key = f"wbnetz_{entry['sigle'].lower()}"
        if src_filter is None or key in src_filter:
            tasks[key] = lambda e=entry: fetch_woerterbuchnetz_entry(e["sigle"], word)

    if not tasks:
        return {
            "word": word,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "sources": {},
            "best_definition": {"source": "none", "definition": "", "score": 0},
            "summary": "Keine Quellen gefunden.",
        }

    result_sources: Dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=min(len(tasks), 8)) as ex:
        futures = {ex.submit(fn): key for key, fn in tasks.items()}
        for future in as_completed(futures):
            key = futures[future]
            try:
                result_sources[key] = future.result()
            except Exception as e:
                result_sources[key] = {"source": key, "success": False, "error": str(e)}

    successful = [k for k, v in result_sources.items() if v.get("success")]
    best = _best_definition(result_sources)
    result = {
        "word": word,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sources": result_sources,
        "best_definition": best,
        "summary": f"Gefunden in {len(successful)} Quellen. Beste Quelle: {best['source']}",
    }
    save_to_history(result)
    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Wort-Lookup Pipeline — historische und archaische deutsche Wörter",
        epilog=(
            "Beispiele:\n"
            "  python3 scripts/word_lookup.py Waldhorn\n"
            "  python3 scripts/word_lookup.py grollen --json\n"
            "  python3 scripts/word_lookup.py minne --output out.json\n"
            "  python3 scripts/word_lookup.py Haus --sources wiktionary,wbnetz_dwb\n"
            "  python3 scripts/word_lookup.py --list-sources"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("word", nargs="?", help="Das nachzuschlagende Wort")
    parser.add_argument("--json", action="store_true", help="Ausgabe als JSON (für Agents/Scripts)")
    parser.add_argument("--output", metavar="FILE", help="Ergebnis in Datei speichern (JSON)")
    parser.add_argument("--sources", metavar="SRC1,SRC2",
                        help="Nur bestimmte Quellen abfragen (kommagetrennt)")
    parser.add_argument("--list-sources", action="store_true",
                        help="Verfügbare Quellen auflisten und beenden")
    args = parser.parse_args()

    if args.list_sources:
        print("Verfügbare Quellen:")
        for src in ALL_SOURCES:
            print(f"  {src}")
        sys.exit(0)

    if not args.word:
        parser.error("Wort erforderlich (oder --list-sources)")

    selected: Optional[List[str]] = None
    if args.sources:
        selected = [s.strip() for s in args.sources.split(",") if s.strip()]
        invalid = [s for s in selected if s not in ALL_SOURCES]
        if invalid:
            print(f"Unbekannte Quellen: {', '.join(invalid)}", file=sys.stderr)
            print(f"Bekannte Quellen: {', '.join(ALL_SOURCES)}", file=sys.stderr)
            sys.exit(1)

    result = lookup_word(args.word, selected)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Gespeichert: {args.output}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))
