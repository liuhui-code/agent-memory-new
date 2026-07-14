# Repository-Grounded Design Control Loop

The design runtime coordinates current repository evidence, candidate evaluation, change planning, implementation verification, and compact calibration. It does not generate hidden reasoning, call an LLM, persist proposals or diffs, or treat learned experience as architecture authority.

## Stable Pipeline

```text
DesignIntent v1
  -> RepositorySnapshot / RepositoryModel v2
  -> candidate-independent baseline ArchitectureView
  -> DesignContract v1 or v2
  -> DesignDelta v1 or v2 candidates
  -> DesignEvaluation v1 or v2
  -> DesignDecision v1 + ChangePlan v1
  -> DesignVerification v1 or v2
  -> explicit compact DesignOutcome v1
```

The Agent authors intent, contracts, and materially different candidates. The deterministic runtime validates schemas, retrieves current facts, checks evidence, compares candidates, builds a bounded edit DAG, and verifies implementation evidence. The four public Skills and `tools/agent_memory.py` remain the interface.

## Repository Model

`repository-model/v2` is a read-only view over normalized SQLite code files, symbols, logs, and active edges. Its `repository-snapshot/v2` binds every result to the current graph revision, counts, freshness, truncation, and evidence gaps.

The model exposes bounded topology, ownership, behavior, data, failure, runtime, and change views. Goal-derived baseline anchors are discovered independently of candidate paths; explicit intent/proposal paths broaden scope but cannot hide goal-discovered consumers. Design context, impact scope, checks, comparisons, and verification consume this model while retaining their compatibility fields.

## Intent, Contracts, and Coverage

`design-intent/v1` contains the goal, scope, exclusions, acceptance criteria, constraints, and open questions. It is optional and caller-owned.

`design-contract/v2` adds an intent id and scenario evidence requirements. `design-contract/v1` remains accepted. A scenario retains attribute, stimulus, environment, artifact, response, measure, and priority.

`design-delta/v2` adds `coverage_evidence` references. Coverage is classified as:

- `uncovered`: no claim
- `claimed`: an id is listed but evidence is absent or invalid
- `supported`: valid Delta and current repository references support the claim
- `verified`: structured successful verification satisfies a declared obligation

Legacy string coverage remains `claimed`; it cannot outrank supported evidence.

## Preparation

`design-prepare` runs before candidate authoring. Given `design-intent/v1`, an optional contract, and optional fitness rules, it builds one candidate-independent `design-workbench/v1` bound to the current graph revision. The workbench contains the bounded repository model, synthesis brief, valid anchor catalog, relation vocabulary, authoring gaps, and an unclaimed `design-delta/v2` template. Empty Delta and verification references are deliberate: the runtime supplies evidence but does not invent a design or claim coverage for the Agent. The template carries `baseline_revision`; later checks hard-fail if the learned graph changed while the candidate was being authored.

## Evaluation and Planning

Bounded evaluator providers report evidence coverage, compatibility, ownership, dependency direction, failure flow, testability, uncertainty, and change cost. Existing structural gates and explicit project fitness rules remain authoritative. A hard violation always blocks a candidate.

`design-compare` reuses one baseline across candidates and returns a `design-decision/v1`, decisive reasons, sensitivity points, tradeoff points, and the selected `change-plan/v1`. Ranking is hard-gated and lexicographic/Pareto-oriented; a scalar score never overrides a violation.

`change-plan/v1` topologically orders implementation, known-consumer review, tests, and observability obligations. Every step has a stable id, target, dependencies, expected Delta, and verification obligations. Plans are bounded to 200 steps and are not persisted.

`design-progress` reconstructs that plan during implementation from the current Git Delta and existing test evidence. Steps are `completed`, `ready`, `pending`, or `blocked`; only dependency-satisfied incomplete steps become next actions. Planned added files are detected in the working tree even before Git tracks them and are reported as an evidence gap. `--completed-step` is restricted to consumer-review and observability obligations that require explicit human acknowledgement; it cannot override implementation or failed-test evidence.

## Verification and Calibration

`design-verify` compares planned and actual files, symbols, exported API signatures, source relation Delta, learned-graph alignment, baseline/current revisions, test evidence, and scenario obligations. With `--base` or `--diff-file`, changed hunks are mapped to fresh ArkTS/TypeScript semantic spans automatically. Source relation Delta describes the current implementation change; learned-graph alignment separately checks the last indexed repository model.

`test-evidence/v1` records command, status, exit code, compact summary, and verified obligations. Repeatable `--test-report` inputs accept JUnit XML, generic `test-report/v1`, pytest-json-report, and Jest JSON. The runtime parses existing reports but never executes test commands. Failed evidence cannot satisfy an obligation. Legacy `--executed-tests` remains accepted as caller-reported execution.

Verification emits bounded replan triggers for missing/unplanned files, symbol drift, graph mismatch, revision drift, failed tests, and unmet v2 scenarios.

`design-outcome` is the only persistence path. It stores compact recall, unplanned-change ratio, scenario verification rate, failed-test count, replan count, and outcome. It never stores source, diffs, proposals, test logs, reasoning, or rules. At most 1,000 outcomes are retained per project, and `maintain-health` exposes calibration-only aggregates.

## Commands

```bash
python tools/agent_memory.py design-prepare --project . \
  --intent intent.json --contract contract.json --rules design-rules.json --json

python tools/agent_memory.py design-check --project . \
  --intent intent.json --proposal candidate.json --contract contract.json --rules design-rules.json --json

python tools/agent_memory.py design-compare --project . \
  --intent intent.json --proposal candidate-a.json --proposal candidate-b.json \
  --contract contract.json --rules design-rules.json --json

python tools/agent_memory.py design-progress --project . \
  --proposal selected.json --contract contract.json --base HEAD \
  --test-report build/test-results.xml --json

python tools/agent_memory.py design-verify --project . \
  --proposal selected.json --contract contract.json --base HEAD~1 \
  --test-report build/test-results.xml --test-report reports/pytest.json --json

python tools/agent_memory.py design-outcome --project . \
  --verification verification.json --outcome success --json

python tools/agent_memory.py eval-design --project . --cases docs/eval/design-cases.json --json
```

## Evidence and Governance

- `exact`: compiler or symbol-index evidence
- `static`: deterministic source analysis
- `heuristic`: bounded naming or structural inference
- `inferred`: non-static legacy or advisory inference

Current source and active exact/static facts outrank rules and experience. Missing coverage is uncertainty, not permission. Project rules remain explicit version-controlled input. Design outcomes may calibrate risk hints and confidence, but they cannot install hard rules or establish current architecture.
