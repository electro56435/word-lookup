#!/usr/bin/env python3
"""Convert .docx/.doc files to Markdown for use with AI agents."""

import sys
import argparse
import re
from pathlib import Path

import mammoth


def convert_docx(path: str) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")
    if p.suffix.lower() not in (".docx", ".doc"):
        raise ValueError(f"Nicht unterstütztes Format: {p.suffix} (nur .docx/.doc)")

    with open(p, "rb") as f:
        result = mammoth.convert_to_markdown(f)

    md = result.value
    # Collapse excessive blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def main():
    parser = argparse.ArgumentParser(description="Word-Dokument zu Markdown konvertieren")
    parser.add_argument("datei", help="Pfad zur .docx oder .doc Datei")
    parser.add_argument("-o", "--output", help="Ausgabedatei (Standard: stdout)")
    args = parser.parse_args()

    try:
        md = convert_docx(args.datei)
    except (FileNotFoundError, ValueError) as e:
        print(f"Fehler: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Gespeichert: {args.output}")
    else:
        print(md)


if __name__ == "__main__":
    main()
