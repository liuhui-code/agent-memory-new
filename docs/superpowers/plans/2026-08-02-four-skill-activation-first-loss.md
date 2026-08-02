# Four-Skill Activation First-Loss Plan

## Objective

Locate the first evidence-backed loss in the normal four-Skill lifecycle before
changing retrieval, ranking, graph, or reflection behavior.

The intended decomposition is:

```text
install/discover -> activate -> retrieve -> use -> reflect -> reuse -> refresh
```

Each stage is tested only after the preceding stage passes. This keeps an Agent
outcome failure attributable and avoids spending model calls on a product path that
cannot start.

## Evidence Levels

- Official Codex documentation states that repository skills are scanned from
  `.agents/skills` and user skills from `$HOME/.agents/skills`.
- The repository installer wrote local skills to `.agent-skills` and user skills to
  `$HOME/.codex/skills`.
- A fresh-project development reproduction failed during `init`: the installer copied
  `tools/agent_memory.py` but omitted `tools/agent_memory_runtime`, producing
  `ModuleNotFoundError: No module named 'agent_memory_runtime'`.
- The existing wPlayer tracer proves an already-prepared four-Skill loop can retrieve
  and reuse reviewed experience. It does not prove installation or implicit activation.

These are development facts. They are not a holdout result or an Agent quality claim.

## Decision

The first stable loss is `install/discover`, before Context quality or Agent reasoning.
Stop the layered Agent experiment at this stage and repair only the installation
contract:

1. copy the complete runtime package beside the stable entry point;
2. install the same four skills under `.agents/skills` for repository scope;
3. install user-scoped skills under `$HOME/.agents/skills`;
4. preserve the single runtime entry, SQLite source of truth, and four-Skill surface;
5. verify a fresh project can run `init`, `doctor`, and discover exactly four skills.

Do not change Context serving, ranking, graph construction, reflection governance, or
stored project memory in this stage.

## Acceptance

- Fresh installation exits successfully without relying on this repository's Python
  import path.
- The installed runtime can run `doctor` from the target project.
- Exactly four skill directories exist under `.agents/skills`.
- No `.agent-skills` directory is created by a new installation.
- Existing focused tests, Python compilation, JSON validation, and the 500-line gate
  pass.

## Next Evidence Gap

After installation passes, test implicit activation with representative positive,
negative, and ambiguous prompts. Only then proceed to the layered ideal-memory,
Agent-authored-memory, and no-memory comparison. Do not infer activation success from
filesystem placement alone.

## Execution Outcome

The fresh-project reproduction failed exactly as predicted before the repair. After
copying the package and using the standard discovery roots, an isolated install ran
`init`, `doctor`, and `maintain-review` without relying on this repository's import
path. The target contained exactly four skills under `.agents/skills`.

A generated fixture with one two-line source file and one synthetic semantic fact was
then used for four natural-language Codex CLI calls. No user source or third-party
source was sent:

- Query implicitly loaded `agent-memory-query`, ran compact Context, and returned the
  stored `smoke-check-42` fact.
- Learn implicitly loaded `agent-memory-learn`, indexed only the requested file at
  depth zero, and completed the returned business-semantic follow-up.
- Reflect implicitly loaded `agent-memory-reflect` and stored a scoped correction
  experience. Its first write exposed that the Skill omitted Runtime-required
  `trigger_condition`; the Skill contract now states that requirement.
- Maintain implicitly loaded `agent-memory-maintain` and ran health and review paths.
  It exposed a public `maintain-review` `NameError` caused by a missed split-module
  import. A call-time import avoids the existing governance dependency cycle, and a
  fresh-install regression now executes the command.

The first Query run also showed that `python` is absent on the validation host. All
four Skill command examples now use the required `python3` interpreter, and the second
Query run succeeded without interpreter fallback.

An attempted wPlayer natural-activation call was rejected before execution because it
would transmit source context to an external model without source-specific approval.
No workaround was used. Existing local wPlayer learn/query/reflect/reuse evidence
remains a separate development observation.

This stage proves installation and representative four-Skill activation. It does not
prove real-task quality uplift, cross-project generalization, or amortized Token and
latency benefit. The ideal-memory versus Agent-authored-memory comparison remains the
next independent evidence stage.

Validation closed with 90 focused installation/governance tests, Python compilation,
JSON parsing, diff hygiene, exactly-four-Skill checks, and the 500-line gate passing.
The restricted complete run executed 815 tests: its one product-test failure was fixed
and rechecked, while its two loopback bind errors passed as a complete three-test module
when local socket permission was available.
