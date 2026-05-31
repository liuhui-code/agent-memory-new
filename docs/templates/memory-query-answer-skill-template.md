# Memory Query Answer Skill Template

Copy the following content into a local Agent CLI skill, for example:

```text
memory-aware-answer/
  SKILL.md
```

This template uses the existing Agent Memory runtime. It does not add a new memory runtime command or a fifth Agent Memory skill.

~~~md
---
name: memory-aware-answer
description: Use when answering, diagnosing, planning, or explaining project-specific coding questions where local Agent Memory may contain relevant facts, reflections, code wiki entries, log statements, or network edges.
---

# Memory Aware Answer

Use Agent Memory as an investigation map before answering project-specific questions.

Memory is advisory. Current source files, current logs, test output, and explicit user instructions override stored memory.

## Runtime Commands

Primary query:

```bash
python tools/agent_memory.py context --project . --query "<query>" --json
```

Focused wiki search:

```bash
python tools/agent_memory.py wiki-search --project . --query "<file symbol route resource log>" --json
```

Use `--memory-home <path>` only when the user configured a custom memory home.

## Query Input Shape

Do not send vague questions. Compress the current task into searchable nouns and mechanisms.

General shape:

```text
<task intent> <domain/module> <file/function/page> <error/log/symbol> <suspected mechanism>
```

Bug or diagnosis shape:

```text
<observed error or log text> <page/file/function> <module> <suspected cause>
```

Design or change shape:

```text
<target feature/module> <intended behavior change> <risk/constraint> <affected symbol/file>
```

HarmonyOS ArkTS shape:

```text
<page/component> <route/resource/import/log text> <lifecycle/function> <suspected mechanism>
```

Good examples:

```text
Index page home_title Detail route ArkTS router.pushUrl resource
load account failed Index aboutToAppear hilog user profile request
pages/Index.ets routes_to pages/Detail.ets app.string.home_title
retrying job process_job logger warning queue backoff
```

## First Query

1. Build the first query from the user request, active file names, error text, logs, and suspected area.
2. Run `context --json`.
3. Parse these fields:

```text
semantic_facts   -> stable project rules, architecture constraints, user preferences
reflections      -> previous mistakes, diagnostic checks, future rules
episodes         -> recent related changes and risk history
wiki_matches     -> files, symbols, pages, route targets, resources to inspect
code_log_matches -> learned log/print/console/hilog statements
edge_matches     -> one-hop relations: contains, emits_log, imports, routes_to, uses_resource
evidence_chains  -> readable explanations for returned edges
network_limits   -> bounds; never ask for unbounded graph traversal
```

For `wiki_matches` and `code_log_matches`, inspect:

```text
search_terms    -> generated anchors and platform/problem terms used for retrieval
match_reasons   -> why the row matched, such as exact_file_path, exact_symbol, exact_log_message, or expanded_query:...
```

Prefer anchors with exact or log-related `match_reasons` for recursive follow-up queries.

## Log Query Rule

If the user provides a real log, error message, console output, hilog text, or stack trace:

1. Query the exact distinctive text first.
2. Inspect `code_log_matches`.
3. Use `function`, `file_path`, `message_template`, `logger`, and `level` to form the next query.
4. Inspect `edge_matches` for `emits_log`, `contains`, and ArkTS relations.

Example:

```bash
python tools/agent_memory.py context \
  --project . \
  --query "load account failed Index aboutToAppear hilog" \
  --json
```

If a log match returns `pages/Index.ets`, `aboutToAppear`, and `load account failed`, the next query should include those exact anchors:

```text
pages/Index.ets aboutToAppear load account failed imports routes_to resource
```

## Recursive Search Loop

Run at most 4 rounds.

For each round:

1. Compress current state into a sharper query.
2. Run `context --json`.
3. Keep only relevant high-signal results.
4. If `wiki_matches` or `edge_matches` identify a file/symbol/resource/log, run `wiki-search --json` for that specific anchor.
5. Read current source files or test output when needed.
6. Update the working state.

Working state:

```json
{
  "question": "",
  "current_frame": "",
  "known_facts": [],
  "memory_constraints": [],
  "log_anchors": [],
  "candidate_files": [],
  "candidate_symbols": [],
  "edge_hints": [],
  "open_questions": [],
  "queries_run": []
}
```

Stop when any condition is true:

- The answer is supported by current source/log/test evidence.
- The next query would repeat the previous query without new anchors.
- The last query returned no useful new results.
- 4 rounds have run.
- Missing user input, credentials, logs, or reproduction steps block progress.

## How To Use Returned Results

Use results in this order:

1. Current source/log/test evidence.
2. `semantic_facts` with high confidence and active status.
3. Relevant `reflections` with clear trigger and repair action.
4. `wiki_matches` and `code_log_matches` as inspection targets.
5. `edge_matches` and `evidence_chains` as relationship hints.
6. `episodes` as historical risk context.

Do not treat `wiki_matches` as proof. They say where to inspect.

Do not treat `edge_matches` as a full call graph. They are bounded one-hop hints.

Do not inject all results into the answer. Use only what changes the answer or next action.

## Final Answer Shape

The final answer must be a reasonable summarized output, not a raw dump of query results.

Before answering:

1. Merge duplicate or overlapping memory hits.
2. Separate confirmed evidence from memory hints.
3. Name uncertainty or missing evidence.
4. Collapse low-value details.
5. Produce a concise conclusion that directly answers the user.

When answering the user, include:

```text
Summary:
- One concise conclusion or recommended next step.

Evidence used:
- Current source/log/test evidence checked.
- Memory facts or reflections that mattered.
- Files, symbols, logs, routes, resources, or edges used.

Reasoning summary:
- Why this conclusion follows from the evidence.

Next action:
- Smallest useful file to inspect, command to run, or change to make.
```

Do not include every query result. Include only the results that explain the conclusion.

If evidence is weak, say so plainly and make the next action an investigation step instead of a confident answer.

For diagnosis, use:

```text
Current problem frame:
- ...

Most likely cause:
- ...

Memory/log evidence:
- ...

Files or symbols to inspect:
- ...

Next smallest check:
- ...
```

For change planning, use:

```text
Design goal:
- ...

Memory constraints:
- ...

Affected files/symbols/routes/resources:
- ...

Recommended approach:
- ...

Risks and verification:
- ...
```

## If Memory Misses

If `context`, `search`, or `wiki-search` returns no useful results:

- Say memory had no useful match.
- Continue with current source/log/test investigation.
- Do not invent keywords.
- The runtime records query misses automatically for later maintenance.

If later maintenance returns `semantic_gap_targets` or `learn_business_payload_template`, use those outputs to enrich the exact files, symbols, and logs that blocked retrieval instead of re-learning broad code scopes.
If `workflow_steps` is present, follow that checklist directly so query misses turn into targeted semantic enrichment instead of a broad re-index.
~~~
