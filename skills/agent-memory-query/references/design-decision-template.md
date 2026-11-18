# A Compact Design Decision

Adapt this MADR-inspired outline for an important decision. Omit sections that
do not help the reader. It is an authoring aid, not a Runtime input format.
Do not leave scaffold text in a saved decision or infer approval from this
template. Follow the project's document metadata and approval conventions.

## Context And Status

Describe the user-visible problem, task scope, decision owner, current status,
and source baseline. Distinguish a proposed design, an authorized
implementation, observed validation, and an accepted project contract.

## Drivers And Unknowns

State the intended outcome, hard constraints, non-goals and relevant quality
priorities. Label each material input by its basis: user requirement, reviewed
contract, current fact, assumption, or unknown. Give concrete quality scenarios
without inventing measurements. Name a credible next change if evolution is a
driver; explain why it is credible.

## Current Structure

Identify the entry point, responsibility boundaries, state owner, consumers,
and failure/lifetime behavior relevant to the decision. Reference current
files, symbols and tests. Keep derived graph hints separate from confirmed
source and intended contracts.

## References Considered

For material references, provide source/version, matching features, prerequisite
evidence, unknowns or contradictions, and transfer limits. Include rejected
references when they explain an important risk. No matching reference is a
valid result.

## Options And Consequences

Describe materially different mechanisms under the same drivers. Include the
current structure when it is a viable baseline. For each option explain:

- responsibilities, interfaces, state and failure handling;
- which driver it serves and which cost it introduces;
- what a credible next change would affect;
- missing evidence or a condition that would make the option unsuitable.

Do not manufacture candidates or total scores. Fewer files, layers or words
are not independently proof of quality.

## Decision

State the chosen mechanism and decisive reasons, the alternatives rejected,
and the disadvantages accepted. If a missing fact prevents selection, state
the unresolved decision and the bounded action needed to resolve it. Retaining
the current structure can be a completed design decision.

## Verification And Revisit

Distinguish planned checks from observed results and attach their evidence.
Describe compatibility, failure-path and migration/reversal checks that are
material to this task. Record what has not been tested. State the condition
that should trigger reconsideration. A passing test supports its checked
behavior, not a general claim of architectural superiority.

## Reusable Feedback

After the attempt, record the conditional lesson and its source evidence via
the existing Reflect workflow when useful. Note whether Memory changed the
decision or merely repeated known material; without a comparison this is a
task observation, not a measured incremental benefit. Preserve failures,
misleading references, and later supersession. Do not save hidden reasoning
or the full task transcript.
