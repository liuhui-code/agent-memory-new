# Read-only main/work branch comparison

Reviewed 2026-11-19 through GitHub connector GET requests. No fetch into local refs, merge, branch move, source edit, or history rewrite was performed.

## Exact revisions and ancestry

Repository: `liuhui-code/agent-memory-new`.

- Main revision supplied for review: `8590f148437a63a61089928c8ce78561c5ab21cd`.
- Work revision supplied for review: `3b3d8d0b47fab598701f77958da5ee2ce2f7492e`.
- Merge base: `320e95137a890403cbd6496858a8a1c7de79c6ec`.
- GitHub compare, base=work and head=main: `diverged`, ahead_by=2, behind_by=642. Thus main has two unique commits and work has 642 by the API ancestry count; this is not a quality or feature count.
- Recursive Git trees were non-truncated: main 1784 entries, ancestor 1412, work 6021 (entries include trees). Blob path/SHA comparison against ancestor gives 357 changed main paths and 4411 changed work paths.

GET evidence endpoints:

- https://api.github.com/repos/liuhui-code/agent-memory-new/compare/3b3d8d0b47fab598701f77958da5ee2ce2f7492e...8590f148437a63a61089928c8ce78561c5ab21cd
- https://api.github.com/repos/liuhui-code/agent-memory-new/commits?sha=8590f148437a63a61089928c8ce78561c5ab21cd&per_page=3
- Recursive Git tree GETs for each exact revision above.
- First unique commit files read with `per_page=100`, pages 1–4: 100/100/90/0 files. Second unique commit returned 77 files. Compare endpoint file output alone was not treated as exhaustive.

## Main-only commits and attribution limits

1. `3c6a07a591d0e139256e515323993616d1ec08cc`, author/committer timestamp `2026-11-18T15:30:51Z` (UTC+08: 2026-11-18 23:30:51), subject `feat(memory): add bounded Rust context and design guidance`.
2. `8590f148437a63a61089928c8ce78561c5ab21cd`, timestamp `2026-11-19T00:22:13Z` (UTC+08: 2026-11-19 08:22:13), subject `feat(memory): add design cases and quality meta-reflection`.

Both author and committer name fields say `liuhui-code`. GitHub's associated author/committer account objects are null and commit verification is false with reason `unsigned`. These metadata do not establish which human or agent performed the work, nor user authorization to integrate it. Commit-message validation statements were not independently rerun during this comparison.

## Four intersecting paths

Only four paths changed on both branches since the common ancestor; all four final blob SHAs differ. A path intersection is not itself a demonstrated textual merge conflict.

- `tools/agent_memory_runtime/models.py`: main adds `.rs` → Rust. Work adds `.mjs`/`.cjs` → JavaScript and the `literal_property_path` code-symbol column. The changes are substantively different and should coexist; whole-file replacement would lose one side.
- `skills/agent-memory-query/SKILL.md`: ancestor has 176 lines, main 184, work 119. Main adds design-reference guidance but retains the ancestor's unconditional causal-stop and diagnostic-output requirements. Work has progressive disclosure and diagnosis-scoped requirements plus source-reading guidance. Taking main's whole file would regress those fixes. Simply appending the eight main lines to the 119-line entry would produce 127 lines; retain the established entry constraint by using the relevant design reference rather than relaxing it.
- `README.md`: distinct feature/documentation additions need preservation from both sides.
- `gitlog.md`: distinct records need preservation from both sides; do not rewrite historical evidence to imply integrated verification.

## Independent changes and verification implications

Main's first commit changes runtime behavior: adds `rust_source.py` and `semantic_rust.py`, registers Rust in `semantic_adapters.py`, connects Rust summaries/declarations in `source_static_extractors.py`, and orders `design_context.py` source nodes with explicit `scope_entry_points` first before truncation. Rust parsing explicitly remains source-declaration navigation, not resolved macros, active cfg, types, or calls.

The second main commit changes Skill/reference materials and evidence, including six design-case references and design-quality reflection; its changed files contain no Runtime implementation changes.

These are not duplicate implementations of the work branch's SQL-source body supplement or default guarded-field path followup. However, learning scopes and design-context projection can change after integration, and shared Skill consumption can change. The work branch's existing tests and gate results cannot automatically be claimed for an untested combined tree. This review did not run either branch's tests or create a combined tree, and cannot certify absence of semantic integration conflicts from path overlap alone.

Recommended next action, if integration is authorized: use a separate integration branch, preserve both sets of changes and evidence, resolve the four shared paths deliberately, then run focused Rust/design-context, schema/learning, Skill-entry/disclosure/installation, and affected source-reading checks. Do not overwrite main or rewrite either history as a shortcut.
