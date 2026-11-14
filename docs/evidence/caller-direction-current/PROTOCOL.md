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
