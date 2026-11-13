# Preserve compatible opaque templates without binding an event

Base 6fa506c. This is an independently reproduced positive-control defect, NOT an
old remaining 231 failure: retained dynamic-template-event-identity variants were
already 3/3 and earlier no-evidence-abstention failures had been repaired.

Independent ParcelTrace sources and fixed-template/missing-ID controls frozen in
d499f39. Public raw handoff contains parcel rejected code=${event} for a compatible
runtime-shaped query, while compact removes it. The loss is in compact_handoff:
direct logs are kept only when a program path activates or a wrapped log exists.
The source template's dynamic event value rightly does not establish fixed event
identity, so activating a path to avoid this filter would be an unsafe shortcut.

## Minimal fix

When neither existing retention branch applies, preserve ONLY already-recalled
candidate templates that have literal source text and pass the existing ordered
literal/opaque value-gap compatibility predicate. No candidate generation,
selection, scoring, query vocabulary or path gate is changed. The new helper
reuses template_contains_identity; it does not infer actual values or binding.
Return the original source template, never interpolate the query ID into it.

Existing event_match behavior remains unchanged: long distinctive literal text
may still locate template source ranges as before; short code=${event} remains
priority=0 even though compatible. Both cases retain path_context.activated=false
with no paths. Multiple source owners with the same template remain represented
(up to the existing projection limits), rather than inventing a unique emitter.

## Evidence

Frozen public tests now preserve raw template logs in compact for TS and ETS,
retain the correct emitter source, keep fixed-ID behavior, and still abstain for
unknown mismatched IDs. Ordered prefix/suffix, adjacent gaps, absent suffix,
placeholder-only, fixed/no-gap, no-ID, numeric-only, alphabetic-only and too-short
ID controls pass. Two-owner tests preserve both long-literal source owners and
both short-literal logs while leaving path activation false.

The previously expectedFailure in test_opaque_log_admission now passes as an
ordinary assertion with its original log-presence requirement unchanged. Base
compact implementation fails five new/previous positive assertions; red output
is retained. Final related results are in final-related.txt. Only the existing
dynamic-template and no-evidence scenarios were rerun: six variants all pass.
No full 231/full-suite/external generalization claim or aggregate reduction.

Runtime files are 440 and 58 lines, diff whitespace check passes. The same-template
compatibility is only a possible source match, not proof of runtime event identity,
root cause, or ownership of the observed concrete value.
