#!/usr/bin/env python3
"""Ersetze ein Wort in der Kinderbuch-MD-Datei mit Kontext-Vorschau."""

import sys
import re
import argparse
from pathlib import Path


def find_occurrences(lines: list[str], word: str) -> list[int]:
    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    return [i for i, line in enumerate(lines) if pattern.search(line)]


def show_context(lines: list[str], line_no: int, ctx: int = 2) -> str:
    start = max(0, line_no - ctx)
    end = min(len(lines), line_no + ctx + 1)
    out = []
    for i in range(start, end):
        prefix = ">>>" if i == line_no else "   "
        out.append(f"{prefix} {i+1:4d}: {lines[i]}")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description="Wort im Kinderbuch ersetzen")
    parser.add_argument("datei", help="Pfad zur .md Datei")
    parser.add_argument("suche", help="Zu ersetzendes Wort")
    parser.add_argument("ersatz", help="Ersatzwort")
    parser.add_argument("--dry-run", action="store_true", help="Nur Vorschau, keine Änderung")
    parser.add_argument("--all", action="store_true", help="Alle Vorkommen ersetzen (Standard: nur erstes)")
    args = parser.parse_args()

    p = Path(args.datei)
    if not p.exists():
        print(f"Fehler: Datei nicht gefunden: {args.datei}", file=sys.stderr)
        sys.exit(1)

    text = p.read_text(encoding="utf-8")
    lines = text.split("\n")

    hits = find_occurrences(lines, args.suche)
    if not hits:
        print(f"'{args.suche}' nicht gefunden in {args.datei}")
        sys.exit(0)

    targets = hits if args.all else hits[:1]
    print(f"Gefunden: {len(hits)} Vorkommen von '{args.suche}' — ersetze {'alle' if args.all else 'erstes'}:")
    print()
    for line_no in targets:
        print(show_context(lines, line_no))
        print()

    if args.dry_run:
        print(f"[Vorschau] Keine Änderung vorgenommen. Ohne --dry-run wird ersetzt.")
        sys.exit(0)

    pattern = re.compile(r'\b' + re.escape(args.suche) + r'\b', re.IGNORECASE)
    count = 0
    for i in targets:
        new_line, n = pattern.subn(args.ersatz, lines[i])
        lines[i] = new_line
        count += n

    p.write_text("\n".join(lines), encoding="utf-8")
    print(f"Fertig: {count} Ersetzung(en) — '{args.suche}' → '{args.ersatz}' in {args.datei}")


if __name__ == "__main__":
    main()
