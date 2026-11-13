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
