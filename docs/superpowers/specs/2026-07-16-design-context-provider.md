# Design Context Provider

## Goal

Give a local Agent the smallest trustworthy set of repository facts, project
constraints, quality concerns, design knowledge, and historical warnings needed
to reason about a user's design request. The Runtime retrieves and composes
context. The Agent owns candidate generation, tradeoff analysis, selection,
implementation planning, and final judgment.

The fixed public Skill set remains unchanged. `agent-memory-query` invokes the
backend design-context facade through `tools/agent_memory.py`.

## Decision

Replace the Runtime-owned design decision loop with a context-provider model:

```text
user request
  -> Agent identifies an initial design intent
  -> design-context facade
       -> current code and graph facts
       -> accepted project constraints and semantic corrections
       -> quality-attribute prompts
       -> versioned principle and pattern references
       -> verified historical warnings
       -> evidence gaps, freshness, and provenance
  -> Agent inspects source, decomposes concerns, and optionally expands context
  -> Agent authors and compares designs
  -> Runtime may validate factual references and declared hard constraints
  -> Agent revises and presents the design
```

The Runtime must not select a pattern, recommend a candidate, rank alternatives,
create an implementation plan, or treat a clean structural check as proof that a
design is good.

## Industry Basis

### Quality Attribute Scenarios

SEI Quality Attribute Workshops identify architecture-critical qualities from
business goals before an architecture is selected. ATAM then evaluates
architectural approaches against scenarios and exposes risks, sensitivity
points, and tradeoff points. The project adopts the scenario and question model,
but leaves analysis to the Agent.

- https://www.sei.cmu.edu/library/quality-attribute-workshop-collection/
- https://www.sei.cmu.edu/library/architecture-tradeoff-analysis-method-collection/
- https://www.sei.cmu.edu/library/reasoning-about-software-quality-attributes/

ISO/IEC 25010:2023 supplies a stable product-quality vocabulary for requirements,
design objectives, test objectives, acceptance criteria, and measurement. It is
used as classification vocabulary, not as an automatic score.

- https://www.iso.org/standard/78176.html

### Decisions And Constraints

Architecture Decision Records preserve context, decision, status, and
consequences. Accepted and still-applicable ADRs are project authority;
superseded ADRs remain provenance but cannot constrain a new design.

- https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions

Architecture fitness tools such as ArchUnit check declared dependency, layer,
containment, inheritance, and cycle rules. They demonstrate the correct Runtime
boundary: deterministic checks of explicit constraints, not architecture choice.

- https://www.archunit.org/userguide/html/000_Index.html

### Language-Neutral Code Facts

SCIP models documents, definitions, occurrences, references, and symbols in a
language-neutral protocol. Agent Memory keeps its existing adapters and SQLite
graph, but evolves stable source identities and provenance in the same spirit.

- https://sourcegraph.com/docs/code-navigation/writing-an-indexer

AWS Well-Architected uses foundational questions to expose tradeoffs and treats
review as a constructive architecture conversation rather than an audit. The
project adopts question-oriented knowledge entries while keeping cloud-specific
guidance optional.

- https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html

## Authority Model

Every context item has a lane, authority, source reference, freshness, and a
statement of how the Agent may use it.

Authority is ordered as follows:

1. explicit user constraints for the current task;
2. current source, compiler output, and tests;
3. accepted project decisions and confirmed business-semantic corrections;
4. current code graph and derived repository views;
5. scoped but unverified semantic corrections as source-check guardrails;
6. verified project experience and failure warnings;
7. versioned general principles, tactics, and patterns;
8. pending or unverified historical observations.

A lower lane never overrides a higher lane. General knowledge is advisory even
when its retrieval relevance is high.

## Knowledge Separation

General design knowledge is shipped as a versioned repository artifact. It is
not learned from the target project and is not modified by task feedback.

Project-specific knowledge remains in SQLite:

- code files, symbols, logs, and graph edges;
- semantic facts and confirmed semantic corrections;
- verified experience and failures;
- project decisions when ADR ingestion is added;
- explicit architecture constraints and fitness rules.

Temporary user requirements and Agent reasoning are not persisted by default.

## Two-Pass Retrieval

### Pass 1: Orientation

The Agent sends the original user request. The Runtime performs bounded lexical
retrieval and returns current anchors, hard constraints, possible quality
concerns, relevant knowledge references, and unresolved evidence gaps.

Possible concerns are routing hints, not conclusions. Their purpose is to help
the Agent decide what to inspect and what to query next.

### Pass 2: Agent-Controlled Expansion

After inspecting the first context, the Agent supplies explicit concerns and
anchors. Examples include `modifiability`, `compatibility`, `performance`, a
repository file, or a symbol ID. Explicit concerns broaden knowledge retrieval;
explicit anchors focus repository traversal. They do not replace the original
request.

This prevents a keyword matcher from silently choosing the design frame.

## Design Knowledge Entry

Each principle, tactic, or pattern reference contains:

```json
{
  "id": "dependency_inversion",
  "kind": "principle",
  "title": "Dependency inversion",
  "quality_attributes": ["modifiability", "testability"],
  "terms": ["boundary", "adapter", "dependency"],
  "summary": "Keep stable policy independent of changing implementation details.",
  "applicability": ["High-level policy depends on volatile infrastructure."],
  "preconditions": ["A stable responsibility-facing contract can be named."],
  "contraindications": ["There is no demonstrated variation or boundary pressure."],
  "tradeoffs": ["Adds interfaces and indirection."],
  "questions": ["Which side owns the abstraction?"],
  "evidence_needed": ["dependency edges", "known consumers"],
  "source_refs": []
}
```

Retrieval returns why the entry matched. It never returns `recommended`,
`selected`, an applicability score, or a generated design.

## Facade Contract

The only new backend facade is:

```bash
python tools/agent_memory.py design-context \
  --project . \
  --query "<user request>" \
  [--concern modifiability] \
  [--anchor src/Feature.ets] \
  [--constraint "public API remains compatible"] \
  [--compact] \
  --json
```

`design-context/v1` returns:

- request and explicit task constraints;
- current repository snapshot and bounded views;
- source anchors, affected consumers, boundaries, state owners, behavior and
  failure relations;
- project constraints and semantic corrections;
- quality-attribute prompts;
- principle, tactic, and pattern references;
- verified historical warnings;
- evidence gaps, freshness, provenance, and expansion hints;
- an explicit Agent ownership policy.

It does not return candidate templates, design deltas, candidate scores,
recommended patterns, selected candidates, or change plans.

## Compatibility Policy

The existing `design-assist`, `design-prepare`, `design-check`,
`design-compare`, `design-progress`, and `design-verify` commands remain callable
during migration so existing automation does not break.

- Query Skill stops invoking them as the default design workflow.
- `design-context` becomes the only normal design retrieval entry.
- Legacy commands are marked compatibility-only in documentation.
- Later phases split objective proposal validation from Runtime-owned design
  scoring before removing decision-oriented commands.

## Governance And Evaluation

Feedback evaluates context supply, not whether the Runtime designed correctly.
Offline cases measure:

- anchor recall and current-source precision;
- hard-constraint recall;
- provenance completeness;
- relevant principle coverage without forced-pattern output;
- Agent citation/use of supplied evidence;
- design defect reduction in blind A/B cases;
- token cost and retrieval latency;
- unsupported conclusion rate in Agent output.

Task outcomes may improve project data and retrieval routing. They cannot mutate
the general knowledge catalog or Runtime algorithms automatically.

## Long-Term Phases

1. Introduce `design-context/v1`, a versioned knowledge catalog, two-pass query
   controls, authority labels, and explicit no-decision guarantees.
2. Ingest accepted/superseded ADRs and explicit architecture constraints with
   stable source references.
3. Split `design-check` into objective evidence validation and legacy policy
   evaluation; keep only objective validation in the normal flow.
4. Replace design scoring and comparison with Agent-authored decision records
   whose evidence references can be checked by the Runtime.
5. Add language-neutral symbol/reference providers while retaining ArkTS-first
   semantic enrichment.
6. Build real repository design cases and run Agent A/B evaluation before each
   retrieval-policy change.

## Acceptance Criteria For Phase 1

1. One natural-language command returns a bounded design context pack.
2. Explicit concerns and anchors refine a second query without losing the
   original request.
3. Every knowledge item exposes applicability, tradeoffs, questions, and source
   provenance.
4. The payload contains no recommendation, candidate selection, score, or change
   plan.
5. Current source and confirmed project constraints remain above experience and
   general knowledge.
6. Existing four Skills and old design commands remain compatible.
7. All Python source files remain below 500 lines.
