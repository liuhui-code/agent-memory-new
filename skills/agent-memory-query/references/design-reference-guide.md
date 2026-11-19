# Selecting Design References

These are authored summaries and reading pointers, reviewed on 2026-11-16.
They are advisory references, not new Runtime catalog entries or project
authority. Read the original material when a decision depends on it. Source
availability, approval, and applicability are different questions.

For concrete system precedents, consult [the mature case index](design-cases.md).
It separates documented mechanisms, team reports and a public incident; select
by problem features and inspect transfer limits rather than adopting a brand's architecture.

## Choose By The Decision

| Need | Read | Use it for | Do not use it for |
|---|---|---|---|
| Derive structure from competing requirements | ADD | Select and instantiate design concepts for explicit drivers | A mandatory ceremony for a local edit |
| Discover missing goals and quality scenarios | arc42 | Prefill the task brief and identify consequential gaps | Filling all template sections regardless of scope |
| Judge abstraction and complexity | Ousterhout; Google review guidance | Inspect information hiding, caller burden, and change propagation | Treating class length or personal style as quality proof |
| Find a suitable artifact or design activity | DPR | Select a responsibility card, quality scenario, or decision record | Treating every service/API artifact as relevant |
| Reason about message integration | EIP | Compare interaction mechanisms and their consequences | Adding messaging to a local synchronous design without need |
| Preserve an important decision | MADR | Capture drivers, alternatives, consequences, and confirmation | Assuming a well-written record proves a good decision |

## ADD: A Design Method

Origin: [SEI ADD 3.0](https://www.sei.cmu.edu/library/add-30-rethinking-drivers-and-decisions-in-the-design-process/).

Use when quality pressures or responsibilities create a real structural choice.
Identify the drivers, consider relevant tactics, patterns or reference
architectures, then allocate responsibilities and interfaces. Revisit the
drivers as details become known. The chosen concept needs a task-specific
rationale; a method name is not one. For a small fixed behavior, direct design
may be sufficient without recursive decomposition.

## arc42: Inputs And Quality Goals

Origin: [arc42 introduction and goals](https://docs.arc42.org/section-1/).

Use its goals, stakeholders, constraints and concrete quality scenarios to
expose missing input. Prioritize the qualities that can change this decision.
Avoid invented numerical targets and exhaustive questionnaires. Unknown load
or compatibility requirements should remain questions, not silently become
favorable assumptions.

## Ousterhout And Google: Review Design Consequences

Origins: [Ousterhout on complexity](https://web.stanford.edu/~ouster/cgi-bin/cs190-winter18/lecture.php?topic=complexity),
[Ousterhout on modular design](https://web.stanford.edu/~ouster/cgi-bin/cs190-spring15/lecture.php?topic=complexity),
[Google code review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html).

Inspect how much callers must understand and how widely a credible change
propagates. An interface earns its place by hiding a decision or simplifying
use. A tiny wrapper that exposes the same details may add burden; a direct
implementation that spreads a volatile detail may also be costly. Compare
both risks. Apply local size and compatibility rules independently; these
heuristics do not override them. Correct tests still need review: passing
tests cannot establish that an abstraction is useful.

## DPR: Reusable Design Activities And Artifacts

Origins: [Design Practice Repository](https://socadk.github.io/design-practice-repository/),
[artifact index](https://socadk.github.io/design-practice-repository/artifact-templates/).

Use when the missing aid is a quality scenario, responsibility/collaboration
description, API description, or decision rationale. Select the artifact that
answers the actual question. A template structures thought; it does not supply
project facts or approval. Keep project-specific examples with source revision,
constraints, rejected alternatives, observed outcomes, and transfer limits.

## EIP: A Domain-Specific Pattern Language

Origin: [Enterprise Integration Patterns introduction](https://www.enterpriseintegrationpatterns.com/patterns/messaging/Introduction.html).

Use for real communication and integration problems. Read a pattern's problem,
context, competing forces, consequences, and related patterns together. Check
delivery, identity, ordering, lifetime and failure assumptions in the current
system. A shared word such as "async" does not justify importing a broker or
distributed protocol into a process-local task.

## MADR: Durable Decision Rationale

Origin: [MADR decision template](https://adr.github.io/madr/decisions/adr-template.html).

Use for a choice whose rationale should survive the task. Preserve why an
alternative was rejected and the disadvantages accepted with the chosen one.
Separate planned confirmation from actual observations. Revisit a decision
when its drivers change; a historical success is not continuing authority.
The local [decision template](design-decision-template.md) is an adaptation,
not a new schema, approval workflow, or automatic evaluator.

## A Useful Case Must Carry Its Limits

Before reusing a project case, inspect its source/version, original goal and
constraints, actual mechanism, alternatives, outcome evidence and remaining
unknowns. Identify at least one condition under which its lesson would fail.
Retain counterevidence and supersession. Popularity, a familiar pattern name,
or a single passing experiment is insufficient to call it a best practice.
Use existing Memory retrieval for project history; these external references
need not be imported into SQLite to be useful.
