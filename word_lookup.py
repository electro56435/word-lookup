#!/usr/bin/env python3
"""
Look up historical German words from multiple sources in parallel.

Sources:
  1. DWDS (dwds.de)       — HTML scrape, modern + historical definitions
  2. Wiktionary (de)      — MediaWiki API, archaic senses + etymology
  3. Wörterbuchnetz Meta  — XML API, discovery of 37+ historical dictionaries
"""

import re
import sys
import time
import argparse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup

DWDS_URL   = "https://www.dwds.de/wb/{word}"
WIKT_API   = "https://de.wiktionary.org/w/api.php"
WBNETZ_API = "https://api.woerterbuchnetz.de/dictionaries/Meta/lemmata/lemma/{word}/0/tei-xml"
TEI_NS     = "https://www.tei-c.org/ns/1.0"

HEADERS = {"User-Agent": "word-lookup/1.0 (personal research tool)"}

_cache: dict = {}


def _get(url: str, **kwargs) -> requests.Response | None:
    if url in _cache:
        return _cache[url]
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, **kwargs)
        r.raise_for_status()
        _cache[url] = r
        time.sleep(0.5)
        return r
    except requests.RequestException as e:
        print(f"[{url[:60]}] HTTP-Fehler: {e}", file=sys.stderr)
        return None


# ─── Source 1: DWDS ───────────────────────────────────────────────────────────

def fetch_dwds(word: str) -> dict | None:
    r = _get(DWDS_URL.format(word=requests.utils.quote(word)))
    if not r:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    definitions = [
        re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        for el in soup.select(".dwdswb-definition")
        if el.get_text(strip=True)
    ]
    if not definitions:
        return None
    wortart_el = soup.select_one(".dwdswb-ft-block .dwdswb-gram")
    etym_el    = soup.select_one(".dwdswb-ft-block .dwdswb-etym")
    return {
        "quelle":     "DWDS",
        "wortart":    wortart_el.get_text(strip=True) if wortart_el else "",
        "definitionen": definitions,
        "herkunft":   etym_el.get_text(" ", strip=True) if etym_el else "",
    }


# ─── Source 2: Wiktionary ─────────────────────────────────────────────────────

def fetch_wiktionary(word: str) -> dict | None:
    r = _get(WIKT_API, params={
        "action": "query", "titles": word,
        "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "format": "json", "formatversion": 2,
    })
    if not r:
        return None
    pages = r.json().get("query", {}).get("pages", [])
    if not pages or "missing" in pages[0]:
        return None
    wikitext = pages[0]["revisions"][0]["slots"]["main"]["content"]

    def clean(text: str) -> str:
        text = re.sub(r"<ref[^>]*>.*?</ref>", "", text, flags=re.S)
        text = re.sub(r"<ref\b.*", "", text, flags=re.S)
        text = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r"\2", text)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        text = re.sub(r"'{2,}", "", text)
        return re.sub(r"\s+", " ", text).strip()

    m = re.search(r"\{\{Bedeutungen\}\}\s*(.*?)(?=\{\{|\Z)", wikitext, re.S)
    if not m:
        return None
    definitions = [
        re.sub(r":\[\d+[a-z]?\]\s*", "", clean(line)).strip()
        for line in m.group(1).splitlines()
        if re.match(r":\[\d", line.strip()) and line.strip()
    ]
    if not definitions:
        return None

    etym = ""
    em = re.search(r"\{\{Herkunft\}\}\s*(.*?)(?=\{\{|\Z)", wikitext, re.S)
    if em:
        etym = clean(em.group(1)).split("\n")[0].strip(":").strip()

    return {
        "quelle":     "Wiktionary",
        "wortart":    "",
        "definitionen": definitions,
        "herkunft":   etym,
    }


# ─── Source 3: Wörterbuchnetz Meta (discovery) ────────────────────────────────

WBNETZ_EXCLUDE = {"BDO"}  # dialect/regional-only, skip

def fetch_woerterbuchnetz(word: str) -> dict | None:
    r = _get(WBNETZ_API.format(word=requests.utils.quote(word)))
    if not r:
        return None
    try:
        root = ET.fromstring(r.text)
    except ET.ParseError:
        return None

    ns = {"tei": TEI_NS}
    sources = []
    for item in root.findall(".//tei:item", ns):
        sigle_el = item.find(".//tei:abbr[@type='wbnetz-sigle']", ns)
        title_el = item.find(".//tei:title", ns)
        ptr_el   = item.find(".//tei:ptr[@type='wbnetz-url']", ns)
        sigle = sigle_el.text.strip() if sigle_el is not None else ""
        title = title_el.text.strip() if title_el is not None else ""
        url   = (ptr_el.text or "").strip().replace("&amp;", "&") if ptr_el is not None else ""
        if sigle and sigle not in WBNETZ_EXCLUDE:
            sources.append({"sigle": sigle, "titel": title, "url": url})

    if not sources:
        return None
    return {"quelle": "Wörterbuchnetz", "quellen": sources}


# ─── Combined lookup ──────────────────────────────────────────────────────────

def lookup_all(word: str) -> dict:
    fetchers = {
        "dwds":           lambda: fetch_dwds(word),
        "wiktionary":     lambda: fetch_wiktionary(word),
        "woerterbuchnetz": lambda: fetch_woerterbuchnetz(word),
    }
    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = {ex.submit(fn): name for name, fn in fetchers.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                print(f"[{name}] Fehler: {e}", file=sys.stderr)
                results[name] = None
    return results


def format_results(word: str, results: dict) -> str:
    lines = [f"# {word}\n"]

    for key in ("dwds", "wiktionary"):
        data = results.get(key)
        if not data:
            continue
        label = data["quelle"]
        if data.get("wortart"):
            lines.append(f"## {label} ({data['wortart']})")
        else:
            lines.append(f"## {label}")
        for i, d in enumerate(data["definitionen"], 1):
            lines.append(f"{i}. {d}")
        if data.get("herkunft"):
            lines.append(f"\n*Herkunft:* {data['herkunft']}")
        lines.append("")

    wbn = results.get("woerterbuchnetz")
    if wbn and wbn.get("quellen"):
        lines.append("## Weitere historische Quellen")
        for src in wbn["quellen"]:
            if src["url"]:
                lines.append(f"- **{src['sigle']}** — {src['titel']}")
                lines.append(f"  {src['url']}")
            else:
                lines.append(f"- **{src['sigle']}** — {src['titel']}")

    if not any(results.get(k) for k in ("dwds", "wiktionary", "woerterbuchnetz")):
        lines.append(f"Kein Eintrag für »{word}« gefunden.")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Historisches Deutsch nachschlagen (multi-source)")
    parser.add_argument("wort", help="Nachzuschlagendes Wort")
    parser.add_argument("--json", action="store_true", help="JSON-Ausgabe")
    args = parser.parse_args()

    results = lookup_all(args.wort)

    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_results(args.wort, results))


if __name__ == "__main__":
    main()
