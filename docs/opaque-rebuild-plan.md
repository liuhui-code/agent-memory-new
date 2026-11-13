# Opaque log admission reconstruction

Development reproduction on 97c0945 uses a new ArchiveReporter source and ten
public context calls. Both missing-event queries returned unrelated fixed and
wrapped logs. Existing code identity filtering did not govern log admission.
Real fixed identity and an independently named method are controls. A compatible
dynamic-template query already loses its anchor in compact output; that failing
control is retained, not represented as an existing success.

Repair boundary: constrain log admission by the same opaque identity request,
allow literal identity or a source template compatible with the requested text,
and preserve independently named code owners. No scoring or budgets change.
Only focused tests and the existing abstention case variants will run, according
to the user's latest direction. Full verification remains outstanding.

## Focused result

The original three Development abstention variants now pass 3/3; the retained
baseline report passed only the original variant (1/3). This restores the two
previously reported failing variants without rerunning all 231 cases. It is not
a newly verified aggregate 159/231 score. No full-suite acceptance is claimed.

Public missing-ID raw/compact outputs no longer contain code/log anchors. Fixed
identity and explicitly named qualified-code controls remain present. The
baseline dynamic-template compact gap remains explicitly expected-failing; raw
admission is preserved. Some localizer candidate metadata can remain when the
anchor output is empty; this reconstruction does not claim to repair that
separate existing pathway. Template compatibility is possible text matching,
not observed runtime variable binding.

The template matcher uses ordered literal searches rather than regex wildcards.
Focused controls cover adjacent placeholders, multiword values, trailing
placeholders, repeated literals, and wrong identifier prefixes. The explicit
code guard accepts both split owner/symbol and already-qualified symbol fields.
