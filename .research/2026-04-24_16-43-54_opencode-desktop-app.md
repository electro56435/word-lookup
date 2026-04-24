## Research Brief: OpenCode Desktop App — MCP Integration & Agent Prompt Config

> **Your role:** You are a researcher. Search the web and return findings. Do NOT execute, implement, write code, or produce a plan — the sections below are background context only. The only deliverable is answers to the questions in `### Open Questions`.

### Open Questions (primary ask)

1. What exactly is the OpenCode desktop app? What LLM(s) does it use (Claude, GPT-4o, configurable)? Where is the official repo or docs?
2. How does OpenCode load agent instructions / system prompts? Does it read `AGENTS.md`, a project-specific config file, or something else? What is the canonical way to give OpenCode persistent project-level instructions?
3. Can OpenCode run shell/CLI commands as part of its agentic loop? If so, how does it discover which commands are available — does the agent prompt simply instruct it to run a specific command, or is there an explicit tool registration step?
4. When OpenCode runs a CLI command that returns JSON on stdout, does it automatically parse and use that output in the next step, or does the user have to intervene?
5. Is there a way to define a repeatable workflow in OpenCode — e.g., "always run this CLI command first, then generate a response using the output"? Or must the agent prompt describe this behavior explicitly each time?

---

### Project Context

A Python CLI tool (`word_lookup.py`) queries historical German dictionaries and returns structured JSON on stdout. It is invoked as:
```
python word_lookup.py <word> --json
```
Output shape:
```json
{ "best_definition": { "definition": "...", "source": "wbnetz_dwb", "score": 142 }, ... }
```
The goal is to configure an AI agent (OpenCode desktop) to act as a "modernizer" for archaic German text from children's books: the agent runs the CLI command, reads the JSON output, and then generates a modern child-friendly replacement word and explanation. No MCP server — CLI only.

### Current Task

Understanding how OpenCode desktop reads agent instructions and runs CLI commands, so that:
- An `AGENTS.md` (or equivalent config file) can be written in the format OpenCode actually reads
- OpenCode knows it should run `python word_lookup.py <word> --json` when given an archaic word
- The two-step pipeline (CLI lookup → agent generates modernization) can be triggered by a simple user message like "modernize this word: Minne"

### Desired Output Format

- Concrete facts about file names, config formats, and config file locations
- If there is an official docs page or GitHub repo, link it directly
- One concrete example of how to instruct OpenCode to run a specific shell/CLI command as part of its workflow

### Temporal Scope

2025–2026 only. OpenCode is a recent tool; older results are likely irrelevant.

### Source Requirements

**Mode: `manual`**

Support important claims with concrete sources. If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such. Include direct URLs, not just site names. If sources disagree, note the disagreement instead of flattening it into one answer.

Aim for 3–5 sources. Include the official OpenCode GitHub repo or docs if they exist.

Required format:
```
## Sources
1. [Title](URL) — what specific information this source provided
```

### How to use this research

Findings will be used to write an `AGENTS.md` (or equivalent) that instructs OpenCode to run a specific CLI command and use its JSON output. Concrete file paths, config field names, and format examples are more useful than general descriptions.

---

## Sources

1. [OpenCode | The open source AI coding agent](https://opencode.ai/) — general overview, desktop beta, 75+ providers
2. [Intro | AI coding agent built for the terminal](https://opencode.ai/docs/) — `/init` command, AGENTS.md generation and purpose
3. [Agents](https://opencode.ai/docs/agents/) — agent config (JSON + Markdown), system prompt loading, tool permissions, subagents
4. [Tools](https://opencode.ai/docs/tools/) — built-in `bash` tool, permissions control, tool outputs fed back into context
5. [Agent Skills](https://opencode.ai/docs/skills/) — SKILL.md format, `.opencode/skills/` location, reusable workflows
6. [Config](https://opencode.ai/docs/config/) — `opencode.json` structure, `instructions` array, custom prompts
7. [GitHub - anomalyco/opencode](https://github.com/anomalyco/opencode) — active repo (other repos like opencode-ai/opencode are archived)

---

## Returned Research

**OpenCode** is an open-source AI coding agent available as a desktop app (beta) on macOS/Windows/Linux, plus terminal TUI and IDE extensions. Supports 75+ providers (Claude, GPT, Gemini, Ollama, etc.) configured per-agent or globally via `opencode.json`. Desktop app shares the same config/agent system as the TUI.

**Agent instructions**: OpenCode auto-discovers `AGENTS.md` in the project root and injects it into every session. Equivalent to CLAUDE.md or Cursor rules. `/init` generates/updates it. Also: `opencode.json` with `"instructions": ["path/to/extra.md"]` or per-agent `"prompt": "{file:./custom.txt}"`.

**Shell/CLI commands**: Built-in `bash` tool, pre-registered, enabled by default. No manual registration needed. Permissions in `opencode.json`:
```json
{ "bash": "allow" }
// or granular:
{ "bash": { "*": "ask", "python word_lookup*": "allow" } }
```
The agent prompt tells the model when/how to invoke bash.

**JSON stdout**: Stdout + stderr + exit code captured automatically and returned to LLM as tool observation. LLM parses JSON naturally in the next reasoning step. No user intervention needed unless bash is set to `"ask"`.

**Repeatable workflows**: Define once in AGENTS.md. Example snippet:
```markdown
## Word Modernization Workflow
When the user provides an archaic German word:
1. ALWAYS execute: `python word_lookup.py <word> --json`
2. Parse returned JSON (focus on "best_definition")
3. Generate: modern child-friendly replacement + short explanation (6-10 year old level)
Never skip the lookup step.
```

Skills (`.opencode/skills/<name>/SKILL.md`) offer modular reuse. Custom sub-agents in `opencode.json` under `"agent"` allow restricted tool sets + dedicated prompts.

---

## Evaluation

**Evaluated:** 2026-04-24 17:08
**Source sets detected:** 1

### Findings That Apply

1. **`AGENTS.md` already exists in this repo** — add the word modernization workflow directly there. OpenCode will pick it up automatically on every session. No new file needed.
2. **`bash` tool is pre-registered** — no `opencode.json` setup required to run `python word_lookup.py <word> --json`. The agent prompt alone is sufficient to instruct OpenCode to call it.
3. **Granular bash permissions** (optional) — if the user wants OpenCode to auto-approve this specific command without prompting: add `{ "bash": { "python word_lookup*": "allow" } }` to `opencode.json` in the project root.
4. **JSON output needs no special handling** — stdout from the CLI call goes directly into LLM context. The AGENTS.md workflow just needs to say "parse the JSON and use `best_definition`."
5. **Active GitHub repo** — `anomalyco/opencode`, not `opencode-ai/opencode` (archived). Worth noting for future updates.

### Needs Adaptation

- The example in the research uses `<word>` as a placeholder — the actual AGENTS.md instruction should make clear OpenCode must substitute the exact user-provided word, not the literal string.
- SKILL.md location for OpenCode is `.opencode/skills/<name>/SKILL.md` — different from `~/.agents/skills/`. Don't confuse the two if adding modular skills later.

### Contradictions

None.

### Interesting Context

- OpenCode supports sub-agents with restricted tool sets — relevant if a dedicated "modernizer" agent (separate from general coding use) is wanted later.
- The `opencode.json` `instructions` array lets you reference the existing `AGENT_PROMPT.md` file directly, without duplicating content into AGENTS.md: `"instructions": ["./AGENT_PROMPT.md"]`.

### KB Cross-Reference

KB Context: none — skipped.

### Open Questions Remaining

- Is `opencode.json` already present in this repo? If not, bash permissions default to `"ask"` — may need one click per lookup call unless the user adds the allow rule.

### Next Concrete Steps

1. `AGENTS.md` — append the word modernization workflow section (bash call → JSON parse → generate replacement + explanation). Two modes: single word, text block with auto-detection.
2. `opencode.json` (create if absent) — add `{ "bash": { "python word_lookup*": "allow" } }` to avoid permission prompts per lookup.
3. Optionally reference existing `AGENT_PROMPT.md` via `instructions` array in `opencode.json` instead of duplicating content.
