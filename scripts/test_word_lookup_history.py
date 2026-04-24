#!/usr/bin/env python3
"""Tests: Recherche-Log enthält die volle Definition (keine 280-Zeichen-Kürzung)."""
import os
import re
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import word_lookup as wl  # noqa: E402


class TestFormatDefinitionForHistory(unittest.TestCase):
    def test_short_untouched(self):
        s = "kurz " * 8
        self.assertEqual(wl._format_definition_for_history(s.strip()), s.strip())

    def test_long_inserts_semicolon_breaks(self):
        part = "a" * 100
        s = "; ".join([part] * 5)
        self.assertGreater(len(s), wl._HISTORY_WRAP_MIN_LEN)
        out = wl._format_definition_for_history(s)
        self.assertIn(";\n\n", out)
        self.assertEqual(re.sub(r"\s+", "", out), re.sub(r"\s+", "", s))

    def test_sentence_break_before_uppercase_german(self):
        s = ("x" * 400) + ". Danach neuer Satz."
        self.assertGreater(len(s), wl._HISTORY_WRAP_MIN_LEN)
        out = wl._format_definition_for_history(s)
        self.assertIn(".\n\nDanach", out)


class TestSaveToHistory(unittest.TestCase):
    def test_writes_full_definition_beyond_280(self):
        long_def = ("Wort " * 120).strip()
        self.assertGreater(len(long_def), 280)
        with TemporaryDirectory() as td:
            hist = Path(td) / "recherche_verlauf.md"
            with patch.object(wl, "HISTORY_FILE", str(hist)):
                wl.save_to_history(
                    {
                        "best_definition": {
                            "definition": long_def,
                            "definition_summary": "",
                            "source": "dwds",
                            "score": 10.0,
                        },
                        "timestamp": "2026-04-24 12:00:00",
                        "word": "probe",
                        "summary": "2 Quellen mit Treffer",
                    }
                )
            body = hist.read_text(encoding="utf-8")
        self.assertIn(long_def, body)
        self.assertNotIn(long_def[:280] + " …", body)
        self.assertIn("**Definition:**\n\n", body)

    def test_prefers_definition_summary_in_log(self):
        long_def = ("Lang " * 100).strip()
        summary = "Zeile eins\nZweite Zeile"
        with TemporaryDirectory() as td:
            hist = Path(td) / "recherche_verlauf.md"
            with patch.object(wl, "HISTORY_FILE", str(hist)):
                wl.save_to_history(
                    {
                        "best_definition": {
                            "definition": long_def,
                            "definition_summary": summary,
                            "source": "dwds",
                            "score": 10.0,
                        },
                        "timestamp": "2026-04-24 12:00:00",
                        "word": "probe",
                        "summary": "1 Quellen mit Treffer",
                    }
                )
            body = hist.read_text(encoding="utf-8")
        self.assertIn("Zeile eins", body)
        self.assertIn("Zweite Zeile", body)
        self.assertNotIn("Lang Lang", body)


class TestNormalizeSummary(unittest.TestCase):
    def test_strips_fence_and_limits_lines(self):
        raw = "```\neins\nzwei\ndrei\nvier\nfünf\nsechs\nsieben\nacht\nneun\n```"
        out = wl._normalize_summary_lines(raw)
        self.assertEqual(len(out.splitlines()), wl._SUMMARY_MAX_LINES)
        self.assertNotIn("```", out)
        self.assertNotIn("neun", out)


class TestAnthropicSummary(unittest.TestCase):
    def test_returns_none_without_api_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            self.assertIsNone(
                wl._anthropic_summarize_definition("Test", "langer wörterbuch text " * 20)
            )


class TestHeuristicSummary(unittest.TestCase):
    def test_openthesaurus_comma_list_becomes_multiline(self):
        raw = "Arbeitskreis, Ausschuss, Beirat, Gremium, Junta, Komitee, Kommission, Rat"
        out = wl._heuristic_summarize_definition("gremium", raw)
        self.assertIn("Synonyme", out)
        self.assertIn("•", out)
        self.assertGreater(len(out.splitlines()), 2)
        self.assertLessEqual(len(out.splitlines()), wl._SUMMARY_MAX_LINES)

    def test_non_empty_and_bounded_lines(self):
        blob = (
            "fackel , f. fax; oft in bild und gleichnis; "
            "mittelhochdeutsch schœne aufgehe wie ein glanz; "
            "vergleiche unter splinter; "
            "ags. fäcele, niederländisch vakkel, dänisch fakkel"
        )
        out = wl._heuristic_summarize_definition("fackel", blob)
        self.assertTrue(out.strip())
        self.assertLessEqual(len(out.splitlines()), wl._SUMMARY_MAX_LINES)
        self.assertNotIn("vergleiche unter", out.lower())

    def test_lookup_prefers_heuristic_when_no_api_key(self):
        expanded = "a" * 100 + "; " + "b" * 100 + "; " + "c" * 100
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            llm = wl._anthropic_summarize_definition("x", expanded)
            heur = wl._heuristic_summarize_definition("x", expanded)
            combined = (llm or heur).strip()
        self.assertIsNone(llm)
        self.assertTrue(combined)


if __name__ == "__main__":
    unittest.main()
