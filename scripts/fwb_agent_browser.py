#!/usr/bin/env python3
"""
FWB-online: Lemma-Text per agent-browser (Chrome) laden — Fallback, wenn
HTTP-Scraping leer, kaputt oder JS-Boilerplate liefert.

Voraussetzung: `agent-browser` im PATH (`brew install agent-browser`, ggf. `agent-browser install`).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import uuid
import os
from typing import Any, Dict

def _clean_text(text: str, maxlen: int = 2000) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()[:maxlen]


SESSION_PREFIX = "fwb-fb-"


def _ab(
    session: str,
    *args: str,
    timeout: int = 90,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["agent-browser", "--session", session, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _parse_eval_output(stdout: str) -> str:
    """Liest die JSON-Ausgabe von agent-browser eval (nur Wertzeile)."""
    lines = [ln for ln in stdout.strip().splitlines() if ln.strip()]
    candidate = lines[-1] if lines else ""
    if not candidate:
        return ""
    s = candidate
    for _ in range(3):
        if not (s and s[0] in '"{[0123456789-'):
            break
        try:
            s = json.loads(s)
        except (json.JSONDecodeError, TypeError, ValueError):
            break
    if s is None or s == "null":
        return ""
    s = str(s).strip()
    if (s.startswith('"') and s.endswith('"')) and len(s) >= 2:
        s = s[1:-1]
    return s


def fetch_fwb_with_agent_browser(word: str) -> Dict[str, Any]:
    """
    Lädt FWB: Suche -> erster Lemma-Link -> Artikeltext (gerendertes DOM).
    Gibt das gleiche Shape zurück wie fetch_fwb() in word_lookup.
    """
    w = (word or "").strip()
    if not w:
        return {"source": "fwb", "success": False, "error": "Leeres Wort", "definitions": []}

    if not shutil.which("agent-browser"):
        return {
            "source": "fwb",
            "success": False,
            "error": "agent-browser nicht im PATH (Browser-Fallback nicht verfügbar).",
            "definitions": [],
        }

    from urllib.parse import quote

    q = quote(w.lower())
    search_url = f"https://fwb-online.de/search?q={q}&type=lemma"
    session = f"{SESSION_PREFIX}{os.getpid()}-{uuid.uuid4().hex[:10]}"

    # Nur Pfad (z. B. /lemma/haus.s.2n) — volle URL in Python bauen, kein doppeltes JSON-Quote-Chaos
    js_href = r"""JSON.stringify((() => {
      const a = document.querySelector('a[href^="/lemma/"]');
      if (!a) return null;
      return (a.getAttribute('href') || '').split('?')[0];
    })())"""

    js_text = r"""JSON.stringify((() => {
      const el = document.querySelector('.artikel') || document.querySelector('article') || document.querySelector('main');
      const t = el ? (el.innerText || '') : (document.body && document.body.innerText || '');
      return t;
    })())"""

    text_out = ""
    err_note = ""
    try:
        r0 = _ab(session, "open", search_url)
        if r0.returncode != 0:
            return {
                "source": "fwb",
                "success": False,
                "error": f"agent-browser Suche: {r0.stderr or r0.stdout}",
                "definitions": [],
            }

        w1 = _ab(session, "wait", "5000")
        if w1.returncode != 0:
            err_note = (w1.stderr or w1.stdout or "")[:200]

        r1 = _ab(session, "eval", js_href)
        if r1.returncode != 0:
            return {
                "source": "fwb",
                "success": False,
                "error": f"eval href: {r1.stderr or r1.stdout}"[:500],
                "definitions": [],
            }
        path_raw = _parse_eval_output(r1.stdout)
        if path_raw in ("", "null", "None"):
            return {
                "source": "fwb",
                "success": False,
                "error": f"Kein Lemma-Link in den Suchergebnissen.{(' ' + err_note) if err_note else ''}",
                "definitions": [],
            }
        if path_raw.startswith("http://") or path_raw.startswith("https://"):
            lemma_url = path_raw
        elif path_raw.startswith("/"):
            lemma_url = f"https://fwb-online.de{path_raw}"
        else:
            lemma_url = f"https://fwb-online.de/{path_raw.lstrip('/')}"

        r2 = _ab(session, "open", lemma_url)
        if r2.returncode != 0:
            return {
                "source": "fwb",
                "success": False,
                "error": f"Lemma-URL: {r2.stderr or r2.stdout}"[:500],
                "definitions": [],
            }
        w2 = _ab(session, "wait", "5000")
        r3 = _ab(session, "eval", js_text)
        if r3.returncode != 0:
            return {
                "source": "fwb",
                "success": False,
                "error": f"eval text: {r3.stderr or r3.stdout}"[:500],
                "definitions": [],
            }
        text_out = _parse_eval_output(r3.stdout)
    finally:
        _ab(session, "close", timeout=30)

    text_clean = _clean_text(text_out, maxlen=2500)
    if not text_clean or _looks_like_js_boilerplate(text_clean):
        return {
            "source": "fwb",
            "success": False,
            "error": "Kein brauchbarer Artikeltext (Browser) oder nur Platzhalter",
            "definitions": [],
        }

    return {
        "source": "fwb",
        "success": True,
        "definitions": [text_clean],
        "etymology": "",
        "error": None,
    }


_JS_BOILERPAT = re.compile(
    r"(javascript\s*(aktivier|einschalt|an)|bitte.*javascript|"
    r"enable\s*javascript|noscript|cookies?\s*aktivier)",
    re.I,
)


def _looks_like_js_boilerplate(text: str) -> bool:
    t = (text or "").strip()
    if not t or len(t) < 20:
        return True
    return bool(_JS_BOILERPAT.search(t))


if __name__ == "__main__":
    lemma = (sys.argv[1] if len(sys.argv) > 1 else "haus").strip()
    result = fetch_fwb_with_agent_browser(lemma)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    sys.exit(0 if result.get("success") else 1)
