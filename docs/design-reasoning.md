# Repository-Grounded Design Reasoning

The design runtime evaluates architecture proposals against current repository evidence. It does not generate designs, call an LLM, persist proposals, or learn project patterns as design authority.

## Stable Pipeline

```text
DesignContract v1
  -> current architecture slice
  -> DesignDelta v1 candidates
  -> built-in and project fitness rules
  -> DesignEvaluation v1
  -> candidate comparison
  -> implementation diff verification
```

The Agent creates contracts and candidates. The deterministic runtime checks them. Four public skills remain the user interface; all commands still enter through `tools/agent_memory.py`.

## Contracts

`design-contract/v1` contains the id, goal, hard constraints, and quality scenarios. Each scenario declares an attribute, stimulus, environment, artifact, response, measurable response, and priority.

`design-delta/v1` contains candidate and contract ids, current anchors, node/edge changes, assumptions, invariants, covered constraints/scenarios, tests, and observability. Legacy unversioned Delta Graph files remain accepted.

## Fitness Rules

Optional `design-rules/v1` files are explicit, version-controlled project input:

- `forbid_edge`: reject or warn on matching dependency directions
- `require_edge`: require matching nodes to have a relationship
- `single_owner`: restrict a relation target to one source

Rules can select source/target layer, kind, path prefix, and relation. Learned experience cannot install or promote a hard rule automatically.

## Commands

```bash
python tools/agent_memory.py design-check --project . \
  --proposal candidate.json --contract contract.json --rules design-rules.json --json

python tools/agent_memory.py design-compare --project . \
  --proposal candidate-a.json --proposal candidate-b.json \
  --contract contract.json --rules design-rules.json --json

python tools/agent_memory.py design-verify --project . \
  --proposal selected.json --contract contract.json --rules design-rules.json \
  --base HEAD~1 --executed-tests "python3 -m unittest tests.test_profile" --json

python tools/agent_memory.py eval-design --project . \
  --cases docs/eval/design-cases.json --json
```

`design-compare` applies hard gates before quality coverage, warnings, uncertainty, and change size. A scalar score never overrides a hard violation.

`design-verify` compares planned and actual files, reports missing and unexpected edits, checks declared tests, re-runs fitness checks, and compares structural Delta items with the current learned graph. Refresh the changed learned scope before treating a missing graph edge as implementation failure.

## Evidence Classes

- `exact`: compiler or symbol-index evidence
- `static`: deterministic source analysis
- `heuristic`: bounded naming or structural inference
- `inferred`: non-static legacy or advisory inference

Current ArkTS extraction is static or heuristic. The `LanguageEvidenceAdapter` protocol lets a future compiler-backed indexer emit exact relationships without changing the stable design schemas.

## Governance

- Current source and active graph facts outrank rules and experience.
- Missing graph coverage is uncertainty, not evidence that an impact does not exist.
- Proposals, raw diffs, generated reasoning, and chain-of-thought remain ephemeral.
- Evaluation cases run without network or LLM access.
- Evaluator outcomes cannot automatically become hard architecture rules.
