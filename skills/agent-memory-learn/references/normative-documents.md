# Learning ADR And Feature Spec Documents

This reference ships with the Learn Skill. It describes the minimal implementation;
tests, performance and Agent efficacy have not been evaluated for this integration.
Use existing Git documents and actual review evidence. This file is a format guide,
not an ADR, Feature Spec, approval or acceptance record.

## Select The Source

Ask the user in natural language only when the existing task does not identify the
document or its scope. Keep `--project` as the memory archive; use `--source` for an
external source tree. Learn one document without following its links:

```bash
python3 tools/agent_memory.py learn-entry --project . --entry "<existing-document.md>" --depth 0 --json
```

For a known directory of relevant documents, use the existing `learn-path` command.
Do not scan a new catalog, create placeholder records or add `--replace` to update a
single document. `--replace` retains the existing code-index reset behavior and also
rebuilds normative records for the chosen source root.

## Flat Frontmatter

A normative document starts with `---`, has unique flat keys, and closes its header
with another `---`. Each key occupies one line. Values are plain scalars or quoted
strings; `scope` also accepts a single-line JSON string array. Nested YAML, block
scalars and multi-line YAML lists are outside this format.

The following is a draft format illustration. Replace its ID and paths with real
values only when authoring an actual document within the user's task:

```markdown
---
type: feature-spec
id: SPEC-replace-with-real-id
status: draft
scope: ["src/relevant-module/**"]
owner: ""
approved_by: ""
approved_at: ""
approval_ref: ""
supersedes: ""
superseded_by: ""
---
# Feature name

## Behavior and scope
Describe the actual requirement, invariants and exclusions.

## Acceptance scenarios
Describe the initial situation, trigger and observable expected result.
Keep unknown requirements and missing evidence explicit.
```

- `type` uses the literal spelling `adr` or `feature-spec`, optionally wrapped in
  single or double quotes. Do not JSON-escape this reserved type marker.
- `id` contains 1–80 ASCII letters, digits, dots, underscores or hyphens and starts
  with a letter or digit. Preserve it across edits; IDs should be unique within the
  source tree. Duplicate IDs are review gaps, not silently merged records.
- ADR statuses are `proposed`, `accepted`, `superseded`, `deprecated`, `rejected`.
  Feature Spec statuses are `draft`, `approved`, `superseded`, `withdrawn`, `rejected`.
  They normalize to `draft`, `approved`, `superseded`, `withdrawn`, `rejected` in the
  derived index. Missing or unrecognized status remains `unknown`.
- Scope is relative to that document's source root, with at most 12 paths/globs of
  at most 240 characters each. `.` or `**` declares project-wide scope; missing scope
  requires review. Project-wide scope belongs to that source tree. An external tree
  still requires Agent confirmation for the current task, even with global scope.
  Do not use absolute paths or `..` segments.
- Each replacement field names at most one stable document ID and cannot name the
  document itself. Confirm the actual relationship and applicable scope in Git.
- A claimed approved document needs the actual owner, approver, `YYYY-MM-DD` date
  and review reference. Each field is at most 512 characters. Metadata completeness
  does not authenticate the review or imply that implementation passed acceptance.
- The whole document is at most 65,536 original UTF-8 bytes, including an optional
  single leading BOM. Frontmatter is at most 4,096 original bytes from the start
  through the closing delimiter's line ending, including BOM, both delimiters and
  actual LF/CRLF bytes. A closing delimiter at EOF counts through its last byte,
  but the document still needs content below the header.
- The closing delimiter is within 48 physical lines after the opening delimiter,
  at source line 49 or earlier. The closing line, comments and blanks all count.
  Structural line endings are LF or CRLF; bare CR and Unicode paragraph separators
  do not create additional structural lines. The first level-one body heading
  supplies the display title.

Learning recognizes the marker from a prefix of at most 4 KiB, then reads the
remaining bounded content through the same file handle. Unmarked Markdown stops
after the prefix. Metadata, body and the document digest use those same bytes;
the source is not reopened between recognition and parsing. This does not establish
an atomic filesystem snapshot or certify approval.
The final partial line at the 4 KiB prefix boundary does not establish a type marker.
Normalize CRLF to LF only for the derived body and excerpt line positions; enforce
byte bounds and compute the source digest from original bytes before normalization.

Do not change a document to `accepted` or `approved` merely to satisfy metadata
checks. Material edits after approval require the owner's actual review; a Git
commit or an unchanged approval field does not approve the new content.

## Read The Learning Result

Read `parse_stats.normative_index` for the current source root and operation:

- `documents_indexed` is the sum of `documents_added`, `documents_updated` and
  `documents_unchanged`. Added means a new cached path; updated means its raw source
  digest changed. Unchanged source is still refreshed with the new observed revision
  and generation. None of these counts establishes approval or acceptance.
- `indexed_sample` lists at most 20 real indexed IDs/paths, their declared status,
  source digest, observed revision, index generation, change category and metadata
  review gaps. The revision is a learning-time repository observation, not a later
  query's HEAD or an approval-version seal. `documents_requiring_metadata_review`
  also counts validly parsed records with unknown status, missing scope or incomplete
  claimed approval. Follow the actual gaps without filling unknown fields by guesswork.
- `documents_retired`, `retirement_counts` and `retirement_sample` report actual cached
  removals in a successful batch: replaced scope, removed file, removed marker or
  invalid metadata. The retirement preview is capped at 20. A selected file disappearing
  during extraction is instead a source-read failure with attempted retirement diagnostics.
- `metadata_issues` reports format/content errors; `read_issues` separately reports
  missing or unreadable Markdown candidates. Each has a total count and a preview of
  at most 20. Their samples and indexed/retired previews have independent truncation flags.
  A source-read error aborts the learning batch before commit; read-error diagnostics
  then appear under the error response's `attempted_normative_index`, not as a
  successfully committed `parse_stats` result.

These are operation counts, not the complete catalog. `approval_inferred` remains false.
Follow `next_action`: review actual source/metadata gaps first; otherwise query the real
indexed IDs on the same archive, inspect retirements, or report no normative change.
Indexed normative documents from the selected source root are not automatic targets
for code business-semantic follow-ups. Mixed scopes can still return `semantic_followup`
for code. Do not substitute business summaries for the normative document workflow.

Removing the normative marker, making metadata invalid or retiring a deleted file
removes its derived document row on refresh. It does not remove Git history. Ordinary
Markdown still uses the existing wiki path. Do not copy a normative contract into
ordinary business summaries or reflections to compensate for a metadata issue.

A source-read failure during normative extraction, including a selected file that
disappears during learning, aborts the current code/document indexing transaction.
Its attempted changes roll back, including replacement retirements, and the failed
batch does not advance its learn Scope checkpoint. Existing rows and generations
remain available for review; Query still observes current bytes and can block excerpts.
Stable removals retire their rows through a later successful scoped refresh. Successfully
read invalid metadata and removed markers retain their documented retirement behavior.

For commands that already accept `--json`, read `normative-learning-error/v1` and the
nonzero exit code. `failed_batch` identifies the rollback/checkpoint boundary;
`attempted_normative_index` contains bounded diagnostics and attempted counts, not
committed changes. Maintenance errors include the failed Scope ID when known. Text
output shows at most five read issues on stderr; JSON retains the 20-entry preview.
Review the actual sources, then retry the same document or existing Scope. Do not
widen the scope or add `--replace` merely to retry a source-read failure.

Earlier scopes in a multi-Scope maintenance call may already be committed. Initialization,
earlier code-reading errors and later Scope registration have separate boundaries; this
error response is not a guarantee that the entire CLI invocation made no changes.

## Query And Maintain

Query by a real document ID or relevant requirement terms using the existing
`context` or `design-context` command. `normative_context` is optional and bounded.
Use the supplied source root and path to read the original, then review approval,
scope, current version and replacement claims. A missing match does not prove no
specification exists; open the known original directly when needed.

`source.digest` belongs to the indexed raw bytes. `source.observed_digest` belongs
to the query's bounded source read, shared with its freshness decision. A null
observed digest means the complete source could not be read within the contract.
Changed documents keep both digests for comparison without returning an old excerpt
or updating cached metadata. Compact output retains both fields. Digest equality
does not authenticate approval or establish an atomic repository snapshot.

`scope_basis` is `document_source_root`. `source.matches_query_project` compares
root directories only; it does not establish task applicability. A
`source_root_requires_agent_confirmation` gap applies to external trees, including
their project-wide documents. Review scope against the original tree and current task.

`replacement_lookup` reads cached metadata in the same archive and source root.
Forward lookups report `not_indexed`, `ambiguous` or `unique` and preview at most two
matching records. Reverse references preview at most three documents declared approved
that claim to replace this ID. Each preview has its own truncation flag; compact output
keeps forward IDs and lookup states rather than their full target previews.
Missing targets, kind differences, reciprocal disagreements and direct two-document
cycle declarations are review gaps, not adjudicated invalidity. Read both originals;
an unindexed target can still exist in Git. For a known target, read it directly or
learn its smallest explicit scope using the existing commands.

The lookup itself does not read target sources or authenticate approval:
`target_sources_checked`, `source_checked` and `approval_verified` remain false.
A separately selected candidate may have its own source observations. Do not count
linked metadata as inspected candidates or infer an automatic winner or status change.

`expected_contract_candidate` still requires Agent review. Drafts are hypothesis
material, and historical documents cannot be current hard constraints. Changed or
missing sources do not return stale excerpts. Expand truncated references or read
the original before checking expected-versus-actual behavior.

Read `examined_document_count` as the inspected candidate count. A true
`candidate_limit_exceeded` means additional matches were not inspected. Cumulative
`omitted_document_count` covers inspected candidates hidden by selection or the shared
budget; `omitted_evidence_gap_count` covers known gaps that were not shown. Neither is
a count of every unseen match. Partial source text also sets `truncated`; even full
query output is not a substitute for the complete original contract.

Full gaps identify source root/path and cached record ID. Compact gaps retain record
ID, document ID and reason. Use source identity when the same document ID exists in
several learned trees. Excerpt end lines describe the text actually emitted after
clipping. The operational last-context cache preserves positions without excerpt
bodies and cannot establish current freshness or approval.

After an authorized Git document change, refresh its existing learned scope:

```bash
python3 tools/agent_memory.py maintain-refresh-scope --project . --scope-id <existing-scope-id> --changed-only --json
```

Read the real scope ID returned by learning or maintenance. Refresh preserves entry
depth zero. A removed entry/path in an existing source root produces an empty scope
and retires its cached files; a missing source root remains an unresolved source gap.
When adopting changed parsing rules for an already indexed tree, fully refresh its
existing Scope without `--changed-only` so unchanged bytes are reparsed as well.
Search rebuild does not reparse documents or certify that old rows meet the new format.

`maintain-health.normative_index` reports exact stored status counts and duplicate
IDs, plus source and metadata observations for at most 20 recently indexed documents.
The review excerpt lists at most five affected documents. Read the unexamined count
and truncation fields; this sample is not a catalog-wide freshness or approval audit.
Review items retain record ID, indexed `source_digest` and the sample read's
`observed_digest`; the latter is null when unavailable. Their revision still describes
learning time. Read the actual source and approval materials before acting on the gap.
Replacement lookups use the same bounded cached metadata; linked targets are not
additional checked source samples merely because they appear in a review reference.

Search rebuild restores FTS from SQLite without learning new Git content. Vault export
creates generated `Normative Context` mirrors; editing a mirror cannot update or
approve the original document.
Mirrors link the original local file and clearly mark changed, missing or unverified
sources before the old snapshot. Read the original rather than using that old text
as current-source evidence.
Mirror metadata separates the indexed digest from the export-time observed digest,
showing `unavailable` when that bounded read cannot complete. Export does not refresh
the SQLite document or approve a changed contract.

If the normative FTS table has to be created, initialization fills it from the existing
SQLite document records. This restores derived search data and does not reread Git,
change a document's status or prove index correctness.
