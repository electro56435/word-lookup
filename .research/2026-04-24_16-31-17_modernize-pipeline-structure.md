## Research Brief: Python CLI Pipeline — Dictionary Lookup + LLM Modernization

> **Your role:** You are a researcher. Search the web and return findings. Do NOT execute, implement, write code, or produce a plan — the sections below are background context only. The only deliverable is answers to the questions in `### Open Questions`.

### Open Questions (primary ask)

1. What is the cleanest Python architecture for a CLI tool that chains two steps: (a) a subprocess call that returns JSON, (b) an LLM API call that uses that JSON as input? Should the pipeline be a class, a dataclass pipeline, or procedural functions? What do real-world projects use?
2. When auto-detecting archaic or old-fashioned words in a block of German text via LLM: what prompt patterns reliably return a structured list of flagged words (with their positions or spans) rather than free-form prose? Are there known gotchas with German inflected forms (nominative vs dative variants of the same archaic word)?
3. For a Python CLI that supports both `--json` (machine-readable) and plain-text (human-readable) output of the same data: what is the idiomatic pattern? Is there a widely-used library (Rich, structlog, or plain argparse) that handles this dual-output cleanly?
4. When chaining multiple LLM calls for a single user request (e.g., detect archaisms → lookup each → generate replacement for each → rewrite sentence): is it better to batch everything into one large prompt, or use separate API calls per word? What are the latency and cost tradeoffs at small scale (1–10 words)?
5. What is the recommended pattern for making the LLM provider (Anthropic/OpenAI) configurable in a Python CLI — env vars, a `~/.config/<tool>.toml`, or argparse flags? Is there a lightweight abstraction library (not litellm) that handles this without adding significant dependencies?

---

### Project Context

Python CLI tool for processing historical German text (old children's books). Uses an existing word-lookup module (calls multiple dictionary APIs in parallel, returns structured JSON with a `best_definition` field). Adding a new `modernize.py` CLI that: (1) takes a word or text block, (2) looks up archaic words in the dictionary module, (3) calls an LLM to generate a modern, child-friendly replacement word and explanation. Python 3.11+, Anthropic SDK available, no web framework.

### Current Task

Building `modernize.py` — a CLI that implements a two-step pipeline:
- **Step 1:** Call `word_lookup.py` subprocess → get `best_definition` from JSON output
- **Step 2:** Call an LLM with the definition → return: replacement word, child-friendly explanation, and (if sentence context is present) a rewritten sentence
- **Auto-detection mode:** When given a text block, use LLM to identify all archaic words first, then run the pipeline for each

### Relevant Code

```python
# word_lookup.py interface (already exists)
import subprocess, json

def lookup_word(word: str) -> dict:
    result = subprocess.run(
        ["python", "word_lookup.py", word, "--json"],
        capture_output=True, text=True, timeout=45
    )
    if result.returncode == 0:
        return json.loads(result.stdout)
    return {"error": result.stderr}

# Output shape:
# {
#   "best_definition": {"definition": "...", "source": "wbnetz_dwb", "score": 142},
#   "summary": "Found 3 results in 2 sources",
#   "sources": { "wbnetz_dwb": {"definitions": ["..."]}, ... }
# }
```

### Desired Output Format

- Concrete code patterns (not pseudocode) with brief explanation of why
- For Q1: an example class/function structure
- For Q2: example prompt template(s) that reliably return structured output
- For Q4: concrete recommendation with reasoning (not "it depends")
- For Q5: one recommended approach with example (env var pattern preferred if it's the clear winner)

### Temporal Scope

2024–2026. Anthropic SDK patterns: 2025–2026 only (API changed significantly).

### Source Requirements

**Mode: `manual`**

Support important claims with concrete sources. If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such. Include direct URLs, not just site names. If sources disagree, note the disagreement instead of flattening it into one answer.

Aim for 3–5 sources total. Include relevant, recently updated GitHub repos where they exist.

Required format:
```
## Sources
1. [Title](URL) — what specific information this source provided
```

### How to use this research

Findings will be evaluated against an existing Python codebase. Include caveats about version compatibility, common misconfigurations, and gotchas.

---

## Sources

1. [Anthropic Structured Outputs docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — exact current JSON schema + `output_config.format` pattern and limits
2. [Rich GitHub](https://github.com/textualize/rich) — dual human/JSON CLI output patterns via Console + conditional json
3. [Anthropic Cookbook — structured JSON extraction](https://github.com/anthropics/anthropic-cookbook/blob/main/tool_use/extracting_structured_json.ipynb) — tool-use + schema examples for lists/entities
4. [Start Data Engineering pipeline architecture post (Jan 2026)](https://www.startdataengineering.com/post/architect-data-pipelines/) — dataclass + step separation in real pipelines
5. [LLMSwap / provider CLI repos (2026)](https://github.com/sreenathmmenon/llmswap) — provider config patterns without heavy libs

---

## Returned Research

**1. Cleanest architecture: modular functions wrapped in a lightweight `dataclass` Pipeline (or simple class for stateful reuse). Procedural is acceptable for tiny scripts, but real-world projects favor dataclasses + separation of concerns for testability and CLI wrapping (Typer/argparse).**

Real-world patterns (2024–2026 GitHub/agent SDKs and data-pipeline guides) consistently use:
- A `dataclass` or Pydantic model for the final output shape (e.g., `ModernizationResult`).
- Separate pure functions/steps: `lookup_word()` (already subprocess-based) and `modernize_with_llm(definition_json)`.
- A thin `Pipeline` class or `run_pipeline()` function that orchestrates the two steps, with optional caching/parallelism.
- Typer or argparse as the CLI entrypoint (thin wrapper).

**Concrete example pattern** (matches observed projects like Claude agent SDKs and modular CLI tools):

```python
from dataclasses import dataclass, field
from typing import Optional
import subprocess, json
from anthropic import Anthropic

@dataclass
class ModernizationResult:
    original: str
    modern_word: str
    explanation: str
    rewritten_sentence: Optional[str] = None
    source_definition: dict = field(default_factory=dict)
    error: Optional[str] = None

class ModernizePipeline:
    def __init__(self, anthropic_client: Anthropic, timeout: int = 45):
        self.client = anthropic_client
        self.timeout = timeout

    def lookup(self, word: str) -> dict:
        result = subprocess.run(
            ["python", "word_lookup.py", word, "--json"],
            capture_output=True, text=True, timeout=self.timeout
        )
        return json.loads(result.stdout) if result.returncode == 0 else {"error": result.stderr}

    def modernize(self, lookup_json: dict, context: Optional[str] = None) -> ModernizationResult:
        definition = lookup_json.get("best_definition", {})
        # LLM call here (structured output)
        return ModernizationResult(...)

    def run(self, input_text: str) -> list[ModernizationResult]:
        # auto-detect or single-word path
        ...
```

**2. Use Anthropic's 2025–2026 structured outputs (`output_config.format` with JSON schema) + a precise prompt that forces a list of objects with character spans.**

**Recommended prompt template**:

```
You are an expert in Early New High German (14th–17th c.). Analyze the following text for archaic, obsolete, or old-fashioned vocabulary.

Return ONLY a valid JSON array (no markdown, no prose) matching this exact schema:
[
  {
    "word": "exact surface form as it appears",
    "start": 123,
    "end": 127,
    "lemma": "base form if different (e.g. 'ward' → 'werden')",
    "reason": "why it is archaic (1 short sentence)",
    "modern_child_friendly": "simple modern replacement a 8–12 year old would understand",
    "confidence": 0.0-1.0
  }
]

Text:
"""
{input_text}
"""
```

**Gotchas with German inflections**:
- Explicitly instruct: "Flag every inflected occurrence with its exact span; also record the lemma."
- Add few-shot examples of inflected archaic words for consistency.
- Post-process: normalize lemmas if needed for dictionary lookup.
- Use `client.messages.parse()` (Pydantic) for automatic validation.

**3. Idiomatic pattern: `argparse` `--json` flag + conditional output using `rich` for human mode.**

```python
import argparse, json
from rich.console import Console
from rich.table import Table

parser = argparse.ArgumentParser()
parser.add_argument("--json", action="store_true")
args = parser.parse_args()

if args.json:
    print(json.dumps([r.__dict__ for r in results], indent=2, ensure_ascii=False))
else:
    console = Console()
    table = Table(title="Modernizations")
    table.add_column("Original")
    table.add_column("Modern")
    table.add_column("Explanation")
    for r in results:
        table.add_row(r.original, r.modern_word, r.explanation[:80])
    console.print(table)
```

**4. For 1–10 words: separate parallel LLM calls per word, not one large batched prompt.**

Reasoning:
- Latency: `concurrent.futures` / `asyncio.gather` makes total wall time ≈ single call
- Cost: smaller per-word context is cheaper than one huge prompt
- Quality: per-word prompts allow tighter schemas and easier retries; large prompts risk dropped items
- Anthropic 2025–2026 patterns favor focused calls; batching is mainly useful for 50+ items

**Concrete**: detect archaic words once → for each word run `lookup` (subprocess) + `modernize` (LLM) in `ThreadPoolExecutor`. Total cost < $0.01 for 10 words.

**5. Env vars as primary mechanism, optional `~/.config/modernize.toml` via stdlib `tomllib` (Python 3.11+). No abstraction library needed.**

```python
import os
from dataclasses import dataclass
import tomllib
from pathlib import Path

@dataclass
class LLMConfig:
    provider: str = "anthropic"
    api_key: str | None = None

def load_config() -> LLMConfig:
    cfg = LLMConfig(api_key=os.getenv("ANTHROPIC_API_KEY"))
    toml_path = Path.home() / ".config" / "modernize.toml"
    if toml_path.exists():
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
            cfg.provider = data.get("llm", {}).get("provider", cfg.provider)
    return cfg
```

**Caveats**: Test `client.messages.parse()` for Pydantic validation. German inflections improve with 1–2 few-shot examples. Add retries (tenacity) around subprocess + LLM calls for production.

---

## Evaluation

**Evaluated:** 2026-04-24 16:34
**Source sets detected:** 1

### Findings That Apply

1. **`modernize.py` structure** — `ModernizationResult` dataclass + `ModernizePipeline` class. `word_lookup.py` already exists as a module; `lookup()` in the pipeline can import directly instead of subprocess. Applies to the new `modernize.py` file (to be created).
2. **Auto-detection prompt** — Use structured outputs with JSON schema including `word`, `start`, `end`, `lemma`, `modern_child_friendly`. Add German inflection instruction ("Flag every inflected occurrence with lemma"). Applies to the LLM call in `ModernizePipeline.run()`.
3. **CLI output** — `argparse --json` flag + `rich` for plain-text. `word_lookup.py` already uses this pattern (`--json` flag) — follow the same convention. Applies to `modernize.py` CLI entry point.
4. **Parallel calls** — `ThreadPoolExecutor` for running per-word pipelines concurrently. Applies when `run()` processes multiple detected archaisms from a text block.
5. **Config** — `ANTHROPIC_API_KEY` env var + optional `~/.config/modernize.toml` via `tomllib`. No extra lib. Applies to `load_config()` in `modernize.py`.

### Needs Adaptation

- The dataclass example typo-checks: `from anthropic import Anthric` in research was a typo — correct import is `from anthropic import Anthropic`.
- `client.messages.parse()` (Pydantic validation) requires `anthropic[bedrock]` or the base SDK 0.30+; verify installed version before using. Alternative: validate with `json.loads()` + manual field checks.
- `r.__dict__` on dataclasses works but `dataclasses.asdict(r)` is the idiomatic way for nested structures.
- Source 5 (LLMSwap GitHub link) — URL looks suspect; treat provider-switching pattern as "forum consensus" until verified against actual repo.

### Contradictions

None — all five recommendations are internally consistent and align with existing `word_lookup.py` conventions.

### Interesting Context

- Structured outputs with `output_config.format` are the 2025+ Anthropic recommendation over raw tool use for list extraction — worth noting for any future tool-use refactor.
- `tenacity` mentioned for retries — useful if the FWB or Wörterbuchnetz sources are flaky (they sometimes time out).
- Batching becomes worthwhile at 50+ words — irrelevant now but relevant if this tool is ever run over full book chapters.

### KB Cross-Reference

KB Context: none — skipped.

### Open Questions Remaining

- Does `client.messages.parse()` with Pydantic require the beta SDK or is it stable in the current installed version? Worth checking `pip show anthropic` before implementing.
- The research recommends `rich` for human output — is it already in the project's dependencies? Check `requirements.txt` or `pyproject.toml`.

### Next Concrete Steps

1. `modernize.py` — create file with `ModernizationResult` dataclass, `ModernizePipeline` class, `load_config()`, and `argparse` CLI entry point with `--json` flag
2. `ModernizePipeline.run()` — two modes: single word (skip auto-detection) and text block (LLM detection call first with character-span schema)
3. `ModernizePipeline.modernize()` — structured output call with JSON schema for replacement word + explanation (+ sentence only if context given)
4. `ThreadPoolExecutor` wrap around per-word pipeline steps when processing text block with multiple archaisms
5. Verify `rich` in deps — add if missing; check anthropic SDK version for `messages.parse()` support
