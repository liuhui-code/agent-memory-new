# Code Understanding Protocol

Use this protocol to understand current files, symbols, routes, resources, configuration, code logs, or business semantics.

## Workflow

1. Run coordinated evidence for the user's goal.
2. Inspect the strongest current-code anchors and active graph edges.
3. Narrow with `wiki-search` when exact files or symbols are known.
4. Follow at most one bounded recursive query at a time using exact returned anchors.
5. Report missing learned coverage explicitly.

```bash
python tools/agent_memory.py context --project . --query "<question>" --json
python tools/agent_memory.py wiki-search --project . --query "<file, symbol, route, or resource>" --json
```

Use `match_reasons`, `search_terms`, `suggested_followup_terms`, and `followup_focus` to sharpen the next query. Prefer route targets for navigation questions, resource keys for display questions, log templates for error questions, and config/permission anchors for configuration questions.

Code and graph evidence describe learned current structure, not a complete call graph. Verify decisive claims against source. Treat business summaries as semantic navigation aids, not source-code replacements.

## Output

Return the relevant entry point, responsibility, dependency direction, state/resource/config relationships, observability anchors, and remaining evidence gaps. Keep historical experience out unless it corrects a specific business meaning or known misconception.
