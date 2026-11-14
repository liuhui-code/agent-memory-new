# Caller direction and requested multi-target retention

Baseline14663ac, independent Development. Reuse the exact fixed source/query
protocol from docs/eval/indirect-caller-current/protocol.json (three sources,
four queries); no new query, source noise, weight or oracle changes. Run normal
init/learn once and raw+compact context for each fixed query. Preserve legacy
strict set-equality outcomes, but do not reinterpret the absence of `only` in
queries as an exclusive caller-only request. Extra callee context is not itself
proof of a violated existing contract.

Primary investigation is the explicitly `both` requested two qualified methods:
check whether both true typed callers enter collection then an already-expressed
requested set is accidentally narrowed. Do not enlarge four-seed/two-caller caps,
infer global uniqueness, drop valid logs, or manufacture a role certificate.
If current code never expresses a retained set, specify that missing permission
and counterexamples before implementation rather than patching scores or caps.
No original/aggregate/holdout run. Public writes remain paused.

One additional unchanged `both` raw query is now frozen for return-only observation
of caller collector, code focus and diversity. It is not an added acceptance case.
The four clean raw outputs are already saved. Compare returned anchors and inspect
exact two admitted caller IDs/digests/ranges, not an injected source set.

Qualification refinement after initial candidate: require a query-time binding to
all recognized target references resolving uniquely in the existing collector.
This is not a full natural-language parse or proof of all callers. Generic,
quoted and unresolved recognized targets get no preservation binding. The binding
is an ephemeral dict-subclass attribute, not a published JSON authority field;
projection or a changed query/identity loses eligibility. Internal test factories
were supplemented with that binding after the original red freeze; their bytes
are not claimed unchanged. Public independent sources/queries remain unchanged.

After focused candidate verification, run only the original category42 Development
scenario (three unchanged variants) on baseline14663ac and candidate. Manifest
classification is development/editable/project_neutral, not holdout. No aggregate
or other scenario. This determines original improvement separately from independent
multi-target retention; strict caller-only equality is not silently relaxed.

Independent review tightened eligibility further: complete mode uses the unchanged
legacy separator grammar, rejecting no-space comma, trailing separators, unsupported
conjunctions/actions, or any matched caller-of clause with no qualified first token.
Its resolved targets must exactly equal the IDs used by the SQL edge filter before
private binding is issued. An intermediate permissive comma parser is not retained.
The default parser and caller collection results remain unchanged. Review counter-
examples and intermediate failing logs remain saved; no acceptance source was tuned.
