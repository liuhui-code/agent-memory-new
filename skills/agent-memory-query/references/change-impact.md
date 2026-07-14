# Change Impact Protocol

Use this protocol for a current diff, affected-file review, regression risk, test selection, or verification planning.

## Workflow

1. Run impact analysis from a Git base, explicit files, or a diff file.
2. Inspect direct changed anchors before reverse dependencies and historical evidence.
3. Treat one-hop graph output as bounded evidence, not complete reachability.
4. Report unlearned changed files as coverage gaps.
5. After tests, record compact feedback without raw diff or test output.

```bash
python tools/agent_memory.py impact-scope --project . --base HEAD~1 --query "<change intent>" --json
python tools/agent_memory.py impact-feedback --project . --outcome pass --executed-tests "<tests>" --json
```

Use `--files <path>` when no Git base is suitable. Read direct/supporting/advisory tiers, reverse dependents, outgoing dependencies, recommended tests, risk reasons, and evidence gaps.

Historical failed tests may raise a recommendation. Flaky history is a warning and cannot dominate. Verify public consumers, route/config/resource changes, runtime signals, and focused tests before broadening scope.
