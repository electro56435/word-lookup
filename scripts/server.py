#!/usr/bin/env python3
"""MCP server exposing word_lookup and docx_to_md as tools for AI agents."""

import sys
import json
from pathlib import Path

# Add project root to path so local modules resolve without install
sys.path.insert(0, str(Path(__file__).parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from word_lookup import lookup_word
from docx_to_md import convert_docx

app = Server("word-dict")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="lookup_word",
            description=(
                "Schlägt ein historisches oder archaisches deutsches Wort in mehreren Quellen nach: "
                "DWDS, Wiktionary, OpenThesaurus, FWB (Frühneuhochdeutsch), "
                "DWB (Grimm), Adelung, AWB, Lexer, BMZ. "
                "Gibt strukturiertes JSON zurück mit 'best_definition' (reichste Quelle) und allen Einzelquellen. "
                "Ideal für historische deutsche Texte, alte Kinderbücher, Mittelhochdeutsch."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "wort": {"type": "string", "description": "Das nachzuschlagende deutsche Wort"},
                },
                "required": ["wort"],
            },
        ),
        Tool(
            name="docx_to_markdown",
            description=(
                "Konvertiert eine Word-Datei (.docx oder .doc) zu Markdown-Text. "
                "Gibt den gesamten Textinhalt zurück, lesbar für Agents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "pfad": {"type": "string", "description": "Absoluter Pfad zur .docx/.doc Datei"},
                },
                "required": ["pfad"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "lookup_word":
        wort = arguments.get("wort", "").strip()
        if not wort:
            return [TextContent(type="text", text="Fehler: Kein Wort angegeben.")]
        result = lookup_word(wort)
        return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]

    if name == "docx_to_markdown":
        pfad = arguments.get("pfad", "").strip()
        if not pfad:
            return [TextContent(type="text", text="Fehler: Kein Pfad angegeben.")]
        try:
            md = convert_docx(pfad)
            return [TextContent(type="text", text=md)]
        except (FileNotFoundError, ValueError) as e:
            return [TextContent(type="text", text=f"Fehler: {e}")]

    return [TextContent(type="text", text=f"Unbekanntes Tool: {name}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
