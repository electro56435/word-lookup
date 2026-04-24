## Research Brief: OpenCode Task-Tool / Subagent — Zod „ses“-Validierung und stabile Custom-Subagents

> **Your role:** You are a researcher. Search the web and return findings. Do NOT execute, implement, write code, or produce a plan — the sections below are background context only. The only deliverable is answers to the questions in `### Open Questions`.

### Repo Relevance

Findings should be actionable for this repository:

- `opencode.json` (repo root) — `permission.task`, `agent.build` / `agent.plan` overrides
- `.opencode/agents/kinderbuch-evaluator.md` — custom subagent definition (`mode: subagent`, `prompt` file ref)
- `AGENTS.md` — Kinderbuch pipeline: Task-Tool vs. inline `AGENT_PROMPT`-Fallback

### Open Questions (primary ask)

1. What is the **root cause** of OpenCode **Zod** errors when invoking the **Task** tool, specifically messages like **`Invalid string: must start with "ses"`** (and related **`"prt"`** prefix errors)? How do these relate to **session IDs**, **message IDs**, and **task_id** / resume semantics?
2. Which **plugins** or **hooks** are **documented or reported** to break Task/subagent creation by mutating IDs? What is the **recommended workaround** (disable list, config order, OpenCode version)?
3. What is the **current official pattern** (as of 2025–2026 docs or upstream repo) for registering a **custom subagent**: `opencode.json` only vs **`.opencode/agents/*.md` only** vs **both** — and how does **config merge precedence** affect availability in the Task tool?
4. For the Task tool **parameters**: when must **`task_id`** be omitted vs set? What format must **`task_id`** have if resuming a subagent task?
5. Are there **closed PRs or issues** (OpenCode core) that **sanitize part/message IDs after plugin hooks** or fix subagent validation — and which **minimum version** includes them?

---

### Project Context

Python CLI project: multi-source German **word lookup** (dictionaries, DWDS, FWB, etc.), JSON output for agents. A **children’s-book modernization** workflow is documented: orchestrator gathers lookup + web snippets, emits a structured handoff block, then a **dedicated subagent** should produce child-friendly replacement + explanation using a separate prompt file. OpenCode project config lives in repo root plus `.opencode/agents/` for the subagent.

### Current Task

Stabilize the pipeline in **OpenCode Desktop**: the **Kinderbuch-Evaluator** subagent should run via **Task** after each handoff. Users still hit **permission denials**, **“subagent not available in session”** (model-side), and **Zod `invalid_format` / `starts_with` / prefix `ses`** when Task runs — need external verification of upstream causes and fixes.

### Observable Symptoms

- Task step shows **prohibited / error** state; UI labels reference **Kinderbuch-Evaluator** / children’s-book evaluation.
- JSON error shape includes **`code`: `invalid_format`**, **`format`: `starts_with`**, **`prefix`: `ses`**, message **must start with `"ses"`** (sometimes empty `path: []`).
- Separate reports in ecosystem: similar errors with **`prt`** prefix and **`path`: `["id"]`** on message creation.
- **Plugins enabled** in global OpenCode config is a suspected variable; exact plugin set unknown in brief.
- **Workaround in repo docs:** if Task fails, apply **`scripts/AGENT_PROMPT.md`** inline in the same turn (fallback).

### Relevant Code

`opencode.json` (abridged — repo root):

```json
{
  "permission": {
    "bash": { "python3*scripts/word_lookup*": "allow" },
    "task": {
      "*": "ask",
      "general": "allow",
      "explore": "allow",
      "kinderbuch-evaluator": "allow"
    }
  },
  "agent": {
    "build": {
      "permission": {
        "task": {
          "*": "ask",
          "general": "allow",
          "explore": "allow",
          "kinderbuch-evaluator": "allow"
        }
      }
    }
  }
}
```

Subagent: `.opencode/agents/kinderbuch-evaluator.md` — YAML frontmatter with `mode: subagent`, `prompt: "{file:../../scripts/AGENT_PROMPT.md}"`, restrictive `permission` (bash/edit/webfetch/task denied for nested tasks).

### Desired Output Format

- Direct answers to each numbered **Open Question**.
- **Bulleted workarounds** ordered by likelihood (config, plugins, version, Task parameter misuse).
- **Source list** per instructions below (URLs required).
- If sources **disagree**, state the disagreement explicitly.

### Temporal Scope

**2024–2026**, prefer **2025–2026** for OpenCode Desktop / CLI behavior; cite older threads only if still referenced in current docs or issues.

### Source Requirements

**Mode: `manual`**

- List only sources that contributed the most substance. **Aim for 3–5.**
- Support important claims with concrete sources.
- If a recommendation is based on anecdotal experience or forum consensus rather than primary documentation, label it as such.
- Include **direct URLs**, not just site names.
- If sources disagree, note the disagreement instead of flattening it into one answer.

**Both modes — required format for your reply:**

```
## Sources
1. [Title or description](URL) — one sentence: what specific information this source provided
2. ...
```

**GitHub:** prefer **anomalyco/opencode** issues/PRs and official **opencode.ai/docs** where applicable.

### How to use this research

Please provide findings that can be evaluated against this codebase — include caveats about **OpenCode version**, **global vs project config merge**, **plugin hooks**, and common **misuse of `task_id` vs `prompt`**.

---

## Sources

*(External researcher: fill when returning.)*

---

## Returned Research

*(Paste external findings here, or paste in chat for auto-eval.)*

---

## Evaluation

*(Filled after research return.)*
