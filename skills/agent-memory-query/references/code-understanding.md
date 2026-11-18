# Code Understanding Protocol

Use this protocol to understand current files, symbols, routes, resources, configuration, code logs, or business semantics.

## Workflow

1. Run coordinated evidence for the user's goal.
2. Inspect the strongest current-code anchors and active graph edges.
3. Narrow with `wiki-search` when exact files or symbols are known.
4. Follow at most one bounded recursive query at a time using exact returned anchors.
5. Report missing learned coverage explicitly.

```bash
python3 tools/agent_memory.py context --project . --query "<question>" --compact --json
python3 tools/agent_memory.py wiki-search --project . --query "<file, symbol, route, or resource>" --json
```

Use compact anchors, relation hints, evidence gaps, and next queries to sharpen the next query. Remove `--compact` only when full match reasons, search terms, or ranking audit are necessary. Prefer route targets for navigation questions, resource keys for display questions, log templates for error questions, and config/permission anchors for configuration questions.

Code and graph evidence describe learned current structure, not a complete call graph. Verify decisive claims against source. Treat business summaries as semantic navigation aids, not source-code replacements.

## Output

Return the relevant entry point, responsibility, dependency direction, state/resource/config relationships, observability anchors, and remaining evidence gaps. Keep historical experience out unless it corrects a specific business meaning or known misconception.

## Reading Targets and Supporting Evidence

`code_anchors.role=primary` is exploration priority assigned to the first bounded anchors, not a claim that each is the requested implementation or a causal owner. Apply the user's requested outcome while reading the existing primary set; do not create an extra query, reset a budget, or expand simply to classify every related file.

- For a source-reading request, inspect current source for the requested setting, operation, or callback. Use `source`, `record_type`, symbols and ranges as provenance clues, not ownership proof. Compact wiki anchors may omit `source`; `code_file` or `code_symbol` still identifies the record kind.
- `source=wrapped_log_caller` / `record_type=code_log_effect` means log-derived caller context. Preserve it as potentially relevant supporting evidence until source or runtime evidence establishes its requested role. It is not automatically irrelevant: for an explicit log phrase or call-path request, that caller may be the direct reading target.
- A wiki anchor may contain only a descriptive string, settings label, or manifest. Do not prefer it over executable source merely because it is wiki-derived or ranks higher. Conversely, do not infer business responsibility or runtime causality from an executable static relation.
- If the same file serves multiple roles, retain each proven role. If two implementations match or a relationship is unknown, report the competing candidates or the specific gap; do not silently discard one to manufacture a unique answer.
- Keep the original JSON and every candidate, log anchor, active graph edge, source excerpt and record identity intact. Make any target/support distinction in the Agent's explanation, not by moving or deleting Runtime fields. Both categories share the original source-exploration, file, search and round limits. Do not reread already supplied lines.

In the answer, identify the requested source with inspected file/symbol/lines and what it actually establishes, plus material uncertainty, incomplete excerpts, or a budget stop. Describe supporting callers and their provenance only when relevant to the requested answer; if the user asks for implementation only, retain unneeded support in the evidence trail instead of expanding the answer. A setting that disables access and a callback that returns a block predicate establish current static implementation, not proof that the reported runtime symptom occurred or was fixed. A filename, rank, or source type alone cannot establish relevance or irrelevance.

For a concrete retrieval problem, retain the original query, project/source revision, typed record IDs, inspected ranges, actual discrepancy and counter-evidence in the task's review evidence. `retrieval-feedback --type` currently accepts only `semantic` and `reflection`; never submit a code/log ID as one of those types, or invent an unsupported code-feedback command. Use the existing task-end system-review handoff when its observed-signal conditions apply. Merely being supporting evidence is not negative feedback, permission to delete, or authority to rewrite memory.

This consumer procedure does not alter default commands, output schema, scores, evaluator definitions, or Runtime budgets. Skill installation and content checks verify delivery of these instructions, not Agent behavioral compliance or original acceptance-gate improvement.
