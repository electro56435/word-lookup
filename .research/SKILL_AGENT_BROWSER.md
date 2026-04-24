---
name: word-lookup agent-browser
description: |
  Gilt in diesem Repository auf macOS: agent-browser per Homebrew installieren und prüfen;
  FWB-online über scripts/fwb_agent_browser.py bzw. automatischen fetch_fwb-Fallback
  in scripts/word_lookup.py. Verweist auf .research/AGENT_SETUP_ANOTHER_MAC.md.
---

# agent-browser (nur word-lookup, macOS-Setup in diesem Repo)

Diese Anleitung ist **nicht** der allgemeine agent-browser-Referenz-Guide. Für die **vollständige CLI-Referenz** (snapshot, klick, record, iOS) zuerst ausführen:

```bash
agent-browser skills get agent-browser
```

Hier: **eine Maschine, dieses Repo** — Pfade, Abhängigkeiten und was `word-lookup` davon wirklich nutzt.

## Wann du diese Datei befolgen sollst

- Nutzer:innen arbeiten in **`word-lookup`**, macOS, und brauchen **FWB (Frühneuhochdeutsches Wörterbuch) online** per Browser.
- `scripts/word_lookup.py` soll den **Browser-Fallback** nutzen, wenn FWB-HTTP-Scraping leer, kurz oder JS-Platzhalter liefert → `fetched_via: "agent-browser"` in `sources.fwb` ist das Erfolgskriterium.
- Manuell testen: **`scripts/fwb_agent_browser.py`**.

Für reines Durchsuchen, andere Sites oder allgemeine Web-Automation: vollständige Anweisung per `agent-browser skills get agent-browser` (siehe oben).

## Voraussetzungen (in dieser Reihenfolge)

1. **Repository-Wurzel** kennen (alle `python3 scripts/...`-Befehle gehen **von der Wurzel**, nicht `cd scripts`, außer du passt Pfade an). Siehe `README.md` und `.research/AGENT_SETUP_ANOTHER_MAC.md`.
2. **Python-venv** (`.venv`) und `pip install requests beautifulsoup4 mcp mammoth` — FWB-Code läuft in derselben Session wie dein `python3`. Unbedingt **dieselbe Umgebung** nutzen, die auch `word_lookup` nutzt; für MCP siehe Pfade in `AGENT_SETUP_ANOTHER_MAC.md`.
3. **Homebrew** ist auf dem Mac installiert (typisch: `/opt/homebrew/bin/brew` auf Apple Silicon).

## Installation auf dem Mac (einmalig)

```bash
brew install agent-browser
agent-browser install
```

`agent-browser install` holt/aktualisiert die **eigene** „Chrome for Testing“-Nutzung der CLI — getrennt von deinem alltäglichen Google Chrome.

## Prüfen, ob es für dieses Repo reicht

```bash
which agent-browser
agent-browser --version
```

Erwartung: Pfad sichtbar (z. B. `/opt/homebrew/bin/agent-browser`) und Version ausgegeben. **`shutil.which("agent-browser")`** in `word_lookup.py` muss das Binary finden — dafür muss derselbe `PATH` gelten, den du in der Shell/IDE nutzt, in der du `python3` startest. Fehlt es nur in der GUI-App: in OpenCode/Terminal-Profil `PATH` so setzen, dass `brew`/`agent-browser` drin ist, oder in der MCP-Config `env` setzen, falls euer Client das unterstützt.

## Dieses Repository: FWB-Integration

| Mechanismus | Datei / Ort | Kurz |
|-------------|-------------|------|
| Automatisch | `scripts/word_lookup.py` → `fetch_fwb` | Nach HTTP-Scrape, wenn nötig: Import von `fwb_agent_browser.fetch_fwb_with_agent_browser` |
| Manuell / Diagnose | `scripts/fwb_agent_browser.py` | `python3 scripts/fwb_agent_browser.py <lemma>` von der Wurzel |
| Sitzungen | in `fwb_agent_browser.py` | Ephemeral `agent-browser --session` mit Präfix `fwb-fb-` (kein fester globaler State nötig) |

**Rauchtest (von der Wurzel, ~10–30 s):**

```bash
python3 scripts/fwb_agent_browser.py haus
```

Erwartung: JSON, `"success": true` und sinnvoller FWB-Text. Exit-Code 0.

**Ohne** installierten `agent-browser` lautet der Fehlertext u. a. *agent-browser nicht im PATH* — dann Installation oben wiederholen.

## Chrome, Speicher, andere Tools (Kurz)

- agent-browser startet **eigene** Browser-Instanz. Wenn parallel ein zweiter Chrome auf **Port 9222** für DevTools lief, können zwei Instanzen Speicher fressen — siehe allgemeine agent-browser-Regeln in `agent-browser skills get agent-browser` (Sektion zu Port 9222). Für reine FWB-Skripte in diesem Repo in der Regel unkritisch; bei knappem RAM lieber zuerst unnötigen Debug-Chrome beenden.
- **Nicht** mit chrome-devtools-Skills verwechseln: FWB-Lookups in diesem Projekt laufen **über** `subprocess` + `agent-browser` in `fwb_agent_browser.py`, nicht über den chrome-devtools-MCP, es sei denn, du ersetzt den Workflow absichtlich.

## Verknüpfte Doku in diesem Repo

- Komplett-Setup (inkl. venv, MCP, optional agent-browser): **`.research/AGENT_SETUP_ANOTHER_MAC.md`**
- FWB-Fallback und Rate-Limits: **`AGENTS.md`**, Abschnitt HTML/FWB/AWB
- Allgemeine Nutzer-Doku: **`README.md`**

---

*Diese Datei bewusst in `.research/`, damit sie mit dem restlichen Recherche-/Setup-Material in einem Ordner bleibt und nicht die globale `~/.claude/skills/` ersetzen muss. Zum Befolgen: als Skill-Inhalt in den Kontext ziehen oder in Agent-Rules verlinken, wenn in diesem Repository gearbeitet wird.*
