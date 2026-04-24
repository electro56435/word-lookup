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

1. [Agents – opencode.ai/docs](https://opencode.ai/docs/agents/) — Registrierung JSON + Markdown, Task, `hidden`, `permission.task`, Beispiele.
2. [Permissions – opencode.ai/docs](https://opencode.ai/docs/permissions/) — `permission.task`, Agent-Overrides, Globs.
3. [Task / subagent creation fails — must start with "prt" #18211](https://github.com/anomalyco/opencode/issues/18211) — Zod-Fehler, Plugin-Verdacht, Desktop-Kontext.
4. [supermemoryai/opencode-supermemory Issues #29 / #32](https://github.com/supermemoryai/opencode-supermemory/issues/29) — fehlendes `prt_`-Präfix in Hooks, Fix-Commits.
5. [task.ts (anomalyco/opencode, Branch dev)](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/tool/task.ts) — Task-Tool-Parameter / Zod-Schema im kanonischen Repo.

---

## Returned Research

**## Answers to Open Questions**

**1. Root cause of OpenCode Zod errors (“Invalid string: must start with "ses"” and related “prt” prefix errors) when invoking the Task tool, and relation to session/message/task_id/resume semantics:**

OpenCode core uses strict Zod schemas (in session/message/part/task handling code paths) that enforce **prefixes on all internal identifiers** for type safety and uniqueness:
- Session / task IDs (`task_id`, `session.id` returned by Task tool, subagent sessions): **must start with `"ses"`** (commonly `"ses_"` or `"ses-"` in practice).
- Message/part/component IDs (in chat streams, `chat.message` hook payloads, tool results): **must start with `"prt"`** (e.g., `"prt_..."`).

The errors (`code: "invalid_format"`, `format: "starts_with"`, `prefix: "ses"` or `"prt"`, sometimes with empty `path: []`) fire during:
- Task tool invocation → subagent session creation (`Session.create` or equivalent).
- Message streaming / part assembly for the new subagent turn.
- Resume logic or metadata extraction.

**Primary triggers (observed 2025–2026):**
- **Plugin hooks** (especially `chat.message`, `tool.execute`, session lifecycle) generate or mutate IDs **without the required prefix**.
- Certain local models (e.g., Qwen3) hallucinate malformed `session_id` / `task_id` values on first tool call in a subagent context.
- Edge cases in multi-subagent launches, failure/cancel paths, or large outputs (truncation drops `session_id` metadata).

These directly break **Task tool → subagent creation** and **resume semantics** (a returned `task_id` is a full session ID that must later be passed back verbatim). The validation is defensive and was tightened ~v1.2.25+, surfacing previously silent hook bugs. “subagent not available in session” or permission errors are often secondary symptoms when the ID validation aborts the dispatch early.

**2. Plugins/hooks documented/reported to break Task/subagent creation by mutating IDs + recommended workaround:**

**Primary culprit (repeatedly reported and confirmed):** the **official `opencode-supermemory` plugin** (and close forks/variants such as viking-memory). Its `chat.message` hook (and related part-handling code) was creating Part IDs missing the `"prt_"` prefix. This was exposed by stricter Zod validation in OpenCode ≥ ~1.2.25 and directly crashes Task/subagent dispatch (and new sessions).

Other potential offenders: any plugin that hooks `chat.message`, `session.*`, `tool.execute.before/after`, or ID generation without prefixing. No exhaustive public list exists; supermemory is the one with dedicated GitHub issues and a self-fix commit.

**Recommended workarounds (ordered by likelihood / impact):**
- **Disable/remove the supermemory plugin** (and any similar memory/persistence plugins) — highest success rate reported. Remove from global `~/.config/opencode/` or project config; restart OpenCode Desktop/CLI.
- Update `opencode-supermemory` to the post-fix version that explicitly adds `"prt_"` prefixes (their issues #29/#32 reference the commit).
- Avoid or reorder plugins that mutate core objects; test with a minimal plugin set.
- For global vs project config: project-level overrides usually win — keep offending plugins only in global if needed for other workflows.
- Upgrade OpenCode to latest stable (post-Mar 2026 builds include related robustness); older 1.2.x builds are most affected.
- Fallback (as noted in repo): use inline `AGENT_PROMPT.md` instead of Task when errors occur.

Anecdotal consensus (forum/Reddit/GitHub threads) strongly favors plugin removal over config tweaks.

**3. Current official pattern (2025–2026 docs) for registering a custom subagent: `opencode.json` only vs `.opencode/agents/*.md` only vs both — and config merge precedence for Task tool availability:**

**Both methods are officially supported and intended to be used together** (they merge at load time). No “only one” requirement.

- **`.opencode/agents/kinderbuch-evaluator.md`** (project-level Markdown with YAML frontmatter): Preferred for prompt-heavy or file-referenced subagents (`prompt: "{file:../../scripts/AGENT_PROMPT.md}"`, `mode: subagent`, restrictive `permission` frontmatter, `hidden: true` for internal-only, etc.). File basename becomes the agent name.
- **`opencode.json`** (root or global): Declarative under `"agent": { "kinderbuch-evaluator": { "mode": "subagent", "description": "...", "model": "...", "prompt": "...", "tools"/permissions... } }`. Good for simple overrides or global agents.

**Merge / precedence rules affecting Task tool:**
- All registered subagents become available to the Task tool (even `hidden: true` ones, if permission allows).
- `permission.task` (glob patterns, `"allow" | "ask" | "deny"`) in root `opencode.json`, `agent.build.permission.task`, or Markdown frontmatter controls invocation. Last-matching glob wins; agent-specific rules **override** global.
- Project `.opencode/agents/` + project `opencode.json` **take precedence** over global `~/.config/opencode/...` for same-named agents.
- Result: your `kinderbuch-evaluator` (defined in MD) + `"allow"` in `permission.task` + `agent.build` override = reliably invocable via `Task` with `subagent_type: "kinderbuch-evaluator"`.

This matches the exact pattern in your repo (`opencode.json` permissions + `.opencode/agents/*.md` definition). Docs explicitly show both side-by-side with examples.

**4. Task tool parameters: when `task_id` must be omitted vs set, and required format if resuming:**

From the official Task tool Zod schema and usage docs:
- **Omit `task_id`** (do not include the key, or pass `undefined`/absent) → **new subagent invocation**. Fresh session/context every time.
- **Set `task_id`** → **only to resume** a previous subagent session. Must be the exact `task_id` / `session.id` string **returned in the prior successful Task tool result** (format: starts with `"ses"`, e.g. `"ses_abc123def456"`). This reuses the subagent’s message history, tool outputs, and state.

The schema description explicitly says: “This should only be set if you mean to resume a previous task (you can pass a prior task_id and the task will …)”. Passing a non-“ses”-prefixed or non-existent value triggers the exact Zod error you see.

Known pitfalls (still open in 2026): failure/cancel paths often omit `task_id` from the result; large outputs truncate metadata (including `session_id`); nested subagent calls can dispatch to the wrong agent. Your subagent’s restrictive frontmatter (`task: deny` etc.) is correct to prevent further nesting.

**5. Closed PRs/issues (OpenCode core) that sanitize part/message IDs after plugin hooks or fix subagent validation — minimum version:**

- No single closed PR titled “sanitize IDs after plugin hooks” was found. Instead:
  - **Plugin-side fix** (opencode-supermemory): explicit addition of `"prt_"` prefix in `chat.message` hook (issues #29, #32; referenced commit). This resolved the most common `prt` breakage.
  - Core permission/nested-task fixes: PR #8111 (respects `agent.*.task` permission for nested sub-agents, post #6319 rework); addresses Task permission bypasses.
  - Related open/ongoing: #13910 (Task loses `task_id` on sub-agent fail/cancel), #11903 (truncation drops `session_id` metadata), multiple Zod ID issues tied to plugins (#17546, #18211, #9950, #13254).

**Minimum version guidance:** Stricter Zod prefix validation landed ~v1.2.25 (exposed the plugin bugs). Post-Mar 2026 builds include incremental robustness and the plugin compatibility fix. **Recommend latest stable** + plugin disable. No evidence of core “post-hook sanitization” — the expectation is that plugins must produce correct IDs (or be disabled). Check release notes/changelog for exact patch versions containing the supermemory-compatible changes.

**Sources** (most substantive; 2025–2026 focus; direct URLs)

1. [Agents – opencode.ai/docs](https://opencode.ai/docs/agents/) — authoritative current pattern for JSON + Markdown registration, Task tool availability, `hidden`, `task` permission globs, merge behavior, and examples matching your `kinderbuch-evaluator.md` setup.
2. [Permissions – opencode.ai/docs](https://opencode.ai/docs/permissions/) — exact semantics of `permission.task`, agent/build overrides, Markdown frontmatter support, and glob precedence.
3. [Task / subagent creation fails with "Invalid string: must start with \"prt\"" #18211 – anomalyco/opencode](https://github.com/anomalyco/opencode/issues/18211) — directly identifies `opencode-supermemory` plugin as root cause of `prt` (and related `ses`) errors during Task/subagent creation; Windows Desktop context.
4. [Part IDs in chat.message hook missing required 'prt' prefix #29 & #32 – supermemoryai/opencode-supermemory](https://github.com/supermemoryai/opencode-supermemory/issues/29) and [#32](https://github.com/supermemoryai/opencode-supermemory/issues/32) — plugin hook details, version ~1.2.25+ exposure, and the prefix fix commit.
5. [Task tool schema (task.ts) + related discussion](https://github.com/sst/opencode/blob/dev/packages/opencode/src/tool/task.ts) and Reddit thread on resume semantics — precise `task_id` “only for resume” rule, format expectations, and real-world usage confirming “ses” prefix requirement.

Sources are consistent on mechanics and the supermemory culprit; minor variance only on exact prefix spelling (“ses” vs “ses_”) in error messages vs internal code. All claims above are directly supported by these primary docs/issues rather than secondary anecdote.

---

## Evaluation

**Evaluated:** 2026-04-24 21:43
**Source sets detected:** 1

### Findings That Apply

1. **`AGENTS.md`** — Zod-Absatz + **Checkliste** (Supermemory raus/neu starten, Stable, `task_id`, kanonischer `task.ts`-Link) — **Stand: nach Evaluation ergänzt**.
2. **`opencode.json` / `.opencode/agents/`** — Entspricht der Recherche (Permissions in JSON, Subagent in Markdown); **keine strukturelle Änderung nötig**, außer bei Bedarf `hidden: true` für den Subagenten (optional, laut Doku nur UX).
3. **Betrieb** — Bei weiteren `ses`/`prt`-Fehlern: **Supermemory deaktualisieren oder entfernen**, OpenCode **aktualisieren**, **`task_id` nur zum Fortsetzen** verwenden (Handoff bleibt in `prompt`).

### Needs Adaptation

- **Versionsnummern** (~v1.2.25, „post-Mar 2026“) sind Recherche-Angaben ohne Verifikation gegen die installierte OpenCode-Build-Nummer — nur als Richtung, nicht als harte Repo-Constraint.
- ~~**task.ts-Link**~~ — in **`## Sources`** auf **https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/tool/task.ts** korrigiert (Return-Research-Text unten kann historisch noch `sst/opencode` zitieren).
- **PR #8111** und offene Issues (#13910, #11903) im Text erwähnt — nicht im Repo nachgezogen; bei Bedarf einzeln gegen GitHub verifizieren.

### Contradictions

- Kein Widerspruch zum aktuellen Repo-Stand: Kurzbrief nahm **JSON+MD-Kombination** an; Repo hat **nur MD-Subagent + JSON-Permissions** (ohne doppelte JSON-`agent`-Definition) — das ist **kompatibel** mit „beides unterstützt“, kein Muss für beides.

### Interesting Context

- **Qwen3** / lokale Modelle als Auslöser für kaputte IDs — sekundär, aber für Debug-Listen relevant.
- **Kein zentrales Core-Sanitizing** nach Plugin-Hooks — Erwartung liegt bei **korrekten Plugins** oder Deaktivierung.

### KB Cross-Reference

KB Context: none — skipped.

### Open Questions Remaining

- Exakter **OpenCode-Patch**, ab dem ein konkretes Fix-Set greift (Changelog-Recherche pro Release).
- Ob **weitere Plugins** neben Supermemory in eurer Installation dieselbe Symptomatik erzeugen (nur durch Ausschalten testbar).

### Next Concrete Steps

1. ~~`AGENTS.md`: Supermemory + Links + Checkliste~~ — **erledigt**.
2. ~~Research **`## Sources`**: kanonischer task.ts-Link~~ — **erledigt**.
3. **Lokal (Nutzer):** OpenCode-Version notieren; Plugin-Liste minimieren; **Task → kinderbuch-evaluator** testen. **KB:** für dieses Brief — keine (siehe KB Cross-Reference oben).

