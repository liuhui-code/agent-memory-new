# Rendered-value contract audit

Baseline 6188afe; read-only Development recheck and counterexample observation.
No runtime change, no holdout, no aggregate run. Original repaired count remains 20.

Reuse the four frozen sources and four unchanged queries from
`docs/eval/owner-audit-current/render-protocol.json`. Run normal init, learn-path,
raw and compact context once per query. Preserve current outputs, source digests
and commands. Do not change input based on the result.

Then perform one independently specified source-binding negative observation:
replace only `Column() { Text(this.plainBody()) }` with
`this.plainBody(); Column() { Text(this.content) }`. It still calls the cleanup
method but discards its return and renders the untransformed field. Run the
same generic query once (raw and compact). This is a counterexample to treating
an ordinary call edge as a rendered-value dependency, NOT a new acceptance case
or authority to alter retrieval. Save all SQLite records and graph edges for
both source versions. No score or oracle relaxation and no further variations.

Stop if current metadata has no result-to-argument assertion: ordinary call
existence is insufficient. A new relation abstraction needs a second independent
defect class and a request permission contract, neither supplied by this audit.
