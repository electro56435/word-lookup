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
import os
import re
import shutil
import sys
import time
from datetime import datetime
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
ANTHROPIC_API  = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VER  = "2023-06-01"
# Recherche-Log: Definition auf 6–8 Zeilen (Anthropic); siehe ANTHROPIC_API_KEY in README.
# Weit verbreitet; bei Bedarf WORD_LOOKUP_SUMMARY_MODEL setzen (z. B. claude-haiku-4-5).
_DEFAULT_SUMMARY_MODEL = "claude-3-5-haiku-20241022"
_SUMMARY_MAX_IN      = 4000  # Zeichen Roh-Definition an das Modell
_SUMMARY_MAX_LINES     = 8
_PROJECT_ROOT  = Path(__file__).resolve().parent.parent
HISTORY_FILE   = str(_PROJECT_ROOT / "recherche_verlauf.md")
# Jeder Logeintrag endet mit denselben vier Feldern; die letzten beiden ersetzt der Kinderbuch-Evaluator.
_HISTORY_PENDING_ERSATZ = "*noch ausstehend: 2–3 Ersatzwörter (Kinderbuch-Evaluator)*"
_HISTORY_PENDING_ERKLAERUNG = "*noch ausstehend (Kinderbuch-Evaluator)*"

STATIC_SOURCES = ["wiktionary", "dwds", "fwb", "openthesaurus"]
WBNETZ_SOURCE_KEYS = [f"wbnetz_{s.lower()}" for s in WBNETZ_SIGLES]
ALL_SOURCES = STATIC_SOURCES + WBNETZ_SOURCE_KEYS

# Lesbare einzeilige Bezeichnungen für `recherche_verlauf.md` (keine technischen Keys).
_SOURCE_DESCRIPTION_DE: Dict[str, str] = {
    "wbnetz_dwb": "Deutsches Wörterbuch (Grimm, DWB) im Wörterbuchnetz — historischer Artikel",
    "wbnetz_adelung": "Adelung (Wörterbuchnetz) — 18. Jh.",
    "wbnetz_awb": "Althochdeutsches Wörterbuch (Wörterbuchnetz) — 8.–11. Jh.",
    "wbnetz_lexer": "Lexer, Mittelhochdeutsch (Wörterbuchnetz) — 12.–15. Jh.",
    "wbnetz_bmz": "Benecke-Müller-Zarncke, Mittelhochdeutsch (Wörterbuchnetz) — 12.–15. Jh.",
    "fwb": "Frühneuhochdeutsches Wörterbuch (FWB-online) — 14.–17. Jh.",
    "dwds": "DWDS (Digitales Wörterbuch der deutschen Sprache) — modern und historisch",
    "wiktionary": "Wiktionary Deutsch — freies Onlinelexikon, Bedeutungen und Etymologie",
    "openthesaurus": "OpenThesaurus — moderne Synonym- und Begriffslisten",
    "none": "kein Treffer",
    "unbekannt": "unbekannte Quelle",
}

_cache: Dict[str, Any] = {}


def source_description_de(key: str) -> str:
    """Kurzbeschreibung der Quelle auf Deutsch (für Logs); Fallback mit Key."""
    k = (key or "").strip()
    if k in _SOURCE_DESCRIPTION_DE:
        return _SOURCE_DESCRIPTION_DE[k]
    return f"Unbekannte Quelle (`{k}`)" if k else "Unbekannte Quelle"


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


# Ab dieser Länge: weiche Umbrüche im Recherche-Log (kein Inhaltsverlust).
_HISTORY_WRAP_MIN_LEN = 400


def _format_definition_for_history(text: str) -> str:
    """Fügt bei langen Definitionen Leselücken ein (; und Satzende vor Großbuchstaben)."""
    if len(text) <= _HISTORY_WRAP_MIN_LEN:
        return text
    t = text.replace("; ", ";\n\n")
    t = re.sub(r"\.\s+(?=[A-ZÄÖÜ])", ".\n\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _normalize_summary_lines(text: str) -> str:
    """Modell-Ausgabe: Codefences entfernen, auf max. Zeilen begrenzen."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\s*", "", t)
        t = re.sub(r"\s*```\s*$", "", t).strip()
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    return "\n".join(lines[:_SUMMARY_MAX_LINES])


_SKIP_HEURISTIC_SEGMENT = re.compile(
    r"^(vergleiche|vgl\.|s\.\s*(das|d\.|oben)|siehe\s+(das|d\.))",
    re.I,
)
_ETYMOLOGY_HINT = re.compile(
    r"mittelhochdeutsch|althochdeutsch|mittelniederländisch|mittelniederdeutsch|"
    r"niederländisch|gotisch|friesisch|altsächsisch|\ba[en]gs\.|lateinisch|"
    r"frühneuhochdeutsch|neuhochdeutsch",
    re.I,
)
_TRASH_SEGMENT_HINT = re.compile(
    r"\bEs\.\s*\d|Dief\.\s*gl|[Vv]oc\.\s*\d|\b[Gg]l\.\s*\d+",
    re.I,
)
_HEURISTIC_LINE_CAP = 220


def _trim_clause(clause: str, cap: int) -> str:
    s = clause.strip()
    if len(s) <= cap:
        return s
    cut = s.rfind(" ", 0, cap)
    return (s[: cut if cut > 40 else cap]).rstrip() + " …"


def _heuristic_comma_synonym_list(t: str) -> Optional[str]:
    """OpenThesaurus u. ä.: eine Flut von Kommas, keine Satzstruktur → mehrzeilige Kurzfassung."""
    if ";" in t or _ETYMOLOGY_HINT.search(t):
        return None
    if len(t) > 600:
        return None
    items = [x.strip() for x in t.split(",") if x.strip()]
    if len(items) < 3:
        return None
    if any(len(x.split()) > 8 for x in items):
        return None
    title = "Synonyme und verwandte Begriffe:"
    cap = _SUMMARY_MAX_LINES - 1
    if len(items) > cap:
        n_show = cap - 1
        more = len(items) - n_show
        bullets = [f"• {items[i]}" for i in range(n_show)]
        bullets.append(f"• (+{more} weitere in der Quelle)")
    else:
        bullets = [f"• {x}" for x in items]
    return title + "\n" + "\n".join(bullets)


def _heuristic_summarize_definition(word: str, dictionary_text: str) -> str:
    """Kompakte Lesefassung ohne API: Semikolon-Sätze filtern, Etymologie extra, max. 8 Zeilen."""
    del word  # reserviert für spätere Lemma-Kürzung
    t = re.sub(r"\s+", " ", (dictionary_text or "").strip())
    if not t:
        return ""
    syn = _heuristic_comma_synonym_list(t)
    if syn:
        return syn
    parts = [p.strip() for p in t.split(";") if p.strip()]
    if not parts:
        return _trim_clause(t, _HEURISTIC_LINE_CAP * 3)

    etym_line = ""
    kept: List[str] = []
    for pl in parts:
        if len(pl) < 22 and _TRASH_SEGMENT_HINT.search(pl):
            continue
        if _SKIP_HEURISTIC_SEGMENT.match(pl):
            continue
        dialect_blob = pl.count(",") > 10 and len(pl) > 120 and _ETYMOLOGY_HINT.search(pl)
        if dialect_blob:
            cand = _trim_clause(pl, _HEURISTIC_LINE_CAP + 80)
            if not etym_line or len(cand) > len(etym_line):
                etym_line = cand
            continue
        line = _trim_clause(pl, _HEURISTIC_LINE_CAP)
        if line and line not in kept:
            kept.append(line)

    max_sense = max(1, _SUMMARY_MAX_LINES - (1 if etym_line else 0))
    out = kept[:max_sense]
    if etym_line:
        et = etym_line if etym_line.lower().startswith("herkunft") else f"Herkunft: {etym_line}"
        et = _trim_clause(et, _HEURISTIC_LINE_CAP + 40)
        if et not in "\n".join(out):
            out.append(et)
    out = out[:_SUMMARY_MAX_LINES]
    if not out:
        return _trim_clause(t, min(600, len(t)))
    return "\n".join(out)


def _anthropic_summarize_definition(word: str, dictionary_text: str) -> Optional[str]:
    """Kompakte 6–8-Zeilen-Definition fürs Log (Anthropic Messages API)."""
    api_key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not api_key or not (dictionary_text or "").strip():
        return None
    model = (os.environ.get("WORD_LOOKUP_SUMMARY_MODEL") or _DEFAULT_SUMMARY_MODEL).strip()
    snippet = dictionary_text.strip()[:_SUMMARY_MAX_IN]
    system = (
        "Du bereitest einen kompakten deutschen Wörterbuch-Auszug für ein Recherche-Log. "
        "Ausgabe: nur normierter Klartext, 6 bis 8 kurze Zeilen, keine Überschrift, keine Codefences, keine Einleitung.\n"
        "Beibehalten: Hauptbedeutung(en), modern verständlich; mehrere Sinnen kurz nummerieren (1), 2), …).\n"
        "Genau eine kurze Zeile zur Herkunft (Etymologie), nur das Wichtigste (z. B. mittelhochdeutsch/althochdeutsch).\n"
        "Weglassen: reine Lemma-Grammatik ohne Sinninhalt, lange Fremd- und Dialektketten, Bibliographie und Sigeln, "
        "Verweise wie „siehe das.“ / „vergleiche“, bloße Fundstellen ohne inhaltlichen Zusatz.\n"
        "Formulierungen sachlich und präzise; Originalzitate nur wenn sie den Sinn klären (höchstens wenige Wörter)."
    )
    user_msg = f"Stichwort: {word}\n\nWörterbuchauszug (Roh):\n{snippet}\n"
    payload = {
        "model": model,
        "max_tokens": 900,
        "system": system,
        "messages": [{"role": "user", "content": user_msg}],
    }
    try:
        r = requests.post(
            ANTHROPIC_API,
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VER,
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Warnung: Definition-Zusammenfassung (LLM) fehlgeschlagen: {e}", file=sys.stderr)
        return None
    parts = data.get("content") or []
    raw = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    out = _normalize_summary_lines(raw)
    return out if out else None


def _format_timestamp_de(iso: str) -> str:
    """Wandelt YYYY-MM-DD … in Anzeige TT.MM, HH:MM (ohne Jahr, Recherche-Verlauf + JSON-Hilfsfeld)."""
    s = (iso or "").strip()
    if len(s) < 10:
        return s or "?"
    try:
        if len(s) >= 19:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        elif len(s) >= 16:
            dt = datetime.strptime(s[:16], "%Y-%m-%d %H:%M")
        else:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        return f"{dt.day:02d}.{dt.month:02d}, {dt.hour:02d}:{dt.minute:02d}"
    except ValueError:
        return s


def save_to_history(result: Dict[str, Any]) -> None:
    """Hängt das Recherche-Ergebnis formatiert an HISTORY_FILE an."""
    try:
        best = result.get("best_definition", {})
        definition = _expand_abbreviations(best.get("definition", "").strip())
        if not definition or best.get("score", 0) == 0:
            return
        source = best.get("source", "unbekannt")
        timestamp = _format_timestamp_de(result.get("timestamp", ""))
        word = result.get("word", "")
        result_summary = result.get("summary", "")
        count_match = re.search(r"(\d+) Quellen", result_summary)
        count = count_match.group(1) if count_match else "?"
        try:
            n = int(count)
            count_label = "1 Quelle" if n == 1 else f"{n} Quellen"
        except ValueError:
            count_label = f"{count} Quellen"
        def_summary = (best.get("definition_summary") or "").strip()
        definition = def_summary if def_summary else _format_definition_for_history(definition)
        quelle_text = source_description_de(source)
        entry = (
            f"## {word} — {timestamp}\n\n"
            f"**Definition:**\n\n{definition}\n\n"
            f"**Quelle:** {quelle_text} · {count_label}\n\n"
            f"**Ersatzwörter:** {_HISTORY_PENDING_ERSATZ}\n\n"
            f"**Erklärung:** {_HISTORY_PENDING_ERKLAERUNG}\n\n"
            f"---\n\n"
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
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        return {
            "word": word,
            "timestamp": ts,
            "timestamp_de": _format_timestamp_de(ts),
            "sources": {},
            "best_definition": {
                "source": "none",
                "definition": "",
                "definition_summary": "",
                "score": 0,
            },
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
    expanded = _expand_abbreviations((best.get("definition") or "").strip())
    if best.get("score", 0) and expanded:
        llm = _anthropic_summarize_definition(word, expanded)
        heur = _heuristic_summarize_definition(word, expanded)
        best["definition_summary"] = (llm or heur).strip()
    else:
        best["definition_summary"] = ""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    result = {
        "word": word,
        "timestamp": ts,
        "timestamp_de": _format_timestamp_de(ts),
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
