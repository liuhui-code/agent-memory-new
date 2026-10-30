# Accept, Apply, Observe And Roll Back A System Change

Use this reference after a real proposal has a prepared artifact and candidate. Bind the
actual project, Memory Home, target and recovery directory to existing authorization.
Do not ask again for already authorized development work. A missing deployment target
or unknown migration compatibility is a concrete gap, not permission to select a project.

The source supports this workflow; verify the installed version before using new commands.
Keep `maintain-system-status` for its original limited states. Advanced states use the
entries below. A model's pass, a zero exit and a completed application are different facts.

## Prepare Before Checking

Read [system-candidates.md](system-candidates.md) and [system-checks.md](system-checks.md).
In addition to the actual patch, include an acceptance plan as one of the 1-3 prepared
artifacts. Choose the future prepared revision and run/check keys before executing.
For a basic requirement, the strict acceptance shape is:

```json
{
  "schema_version": "system-change-acceptance-plan/v1",
  "proposal_id": 1,
  "prepared_state_revision": 2,
  "gates": [
    {"key":"functionality","run_key":"check-change","check_key":"verify","result_file":"functionality.json"},
    {"key":"negative_cases","run_key":"check-change","check_key":"verify","result_file":"negative.json"},
    {"key":"compatibility","run_key":"check-change","check_key":"verify","result_file":"compatibility.json"},
    {"key":"cost","run_key":"check-change","check_key":"verify","result_file":"cost.json"},
    {"key":"rollback","run_key":"check-change","check_key":"verify","result_file":"rollback.json"}
  ],
  "criteria": [{"index":0,"run_key":"check-change","check_key":"verify","result_file":"functionality.json"}],
  "follow_up": {
    "source_files": [{"path":"verify.py","digest":"<actual-sha256>"}],
    "checks": [{"key":"after-apply","argv":["<absolute-executable>","verify.py","--after-apply"],"assertion_indices":[0],"timeout_seconds":60,"result_files":["after-apply.json"]}],
    "close_condition": "<bounded condition actually established by these post-application checks>"
  }
}
```

This is a template, not executable evidence. Replace IDs, digests, paths, actual commands
and assertions. Gates must represent the corresponding real checks; empty files or
relabeling a successful command do not establish correctness, compatibility or rollback.

All changes need the five gates above. Add independent_reproduction and
public_output_reproduction for defects; independent_defect_class_1/2 for structural
changes, with distinct check evidence and Agent-reviewed source independence. Evaluator
changes also need known_expected. Query/Learn/Reflect/evaluator changes need existing_gates,
performance and file_size. Data-model changes need reader_writer_matrix, data_preservation,
migration_restart and post_upgrade_writes. At most 12 distinct gates and 5 criteria fit
this format. Every criterion must appear once and map to an actual check assertion index.

Use check plan v3: the v2 top-level fields plus `result_files` in each check. Each check
declares 1-10 distinct contained output paths, absent before the new run. The runner
observes up to 1 MiB per result after execution; it does not parse arbitrary output into
a correctness verdict. Existing source, command, timeout and candidate bindings still
apply. Keep raw argv in prepared plan files; SQLite receipts retain digests and metadata.

## Review And Accept

After actual checking, the user's current Agent inspects the evidence, expected results,
counterexamples, source use and policy scope. Write this separate bounded review inside
the development root; do not edit the already-bound acceptance plan to fit the result:

```json
{
  "schema_version":"system-change-acceptance-review/v1",
  "proposal_id":1,
  "prepared_state_revision":2,
  "candidate_key":"<actual-key>",
  "candidate_digest":"<actual-digest>",
  "reviewer_ref":"<actual-current-agent/task-reference>",
  "criterion_reviews":[{"index":0,"reason":"<evidence and expected-result assessment>"}],
  "gate_reviews":[
    {"key":"functionality","reason":"<actual assessment>"},
    {"key":"negative_cases","reason":"<actual assessment>"},
    {"key":"compatibility","reason":"<actual assessment>"},
    {"key":"cost","reason":"<actual assessment>"},
    {"key":"rollback","reason":"<actual assessment>"}
  ],
  "source_use_review":"<which actual entry/import/source paths were inspected and exercised; remaining limitations>"
}
```

Reviews cover exactly the planned criteria/gates. Plans/reviews are at most 32 KiB;
reasons are at most 500 characters and source_use_review at most 1,000. Reviewer references
do not authenticate identity or Oracle quality. Runtime flags remain evidence_verified=false
and promotion_eligible=false even after checked; external release policy is separate.

Governance v2 is required for lifecycle writes. When authorized, preview and explicitly
execute migration with a new backup file outside Memory Home:

```bash
python3 tools/agent_memory.py maintain-system-migrate --project . --target-version system-evolution-v2 --backup-file <new-backup.db> --json
python3 tools/agent_memory.py maintain-system-accept --project . --id <id> --expected-revision <prepared-revision> --operation-key <accept-key> --acceptance-file <acceptance.json> --review-file <review.json> --json
```

Both default to preview; `--execute` performs the explicit action within existing authority.
Acceptance checks v3 runs, candidate/artifact/result digests and Agent review before
entering checked. Any changed input requires a new prepared revision and checks.

## Apply And Recover

```bash
python3 tools/agent_memory.py maintain-system-apply --project . --id <id> --expected-revision <checked-revision> --operation-key <apply-key> --target-root <authorized-target> --recovery-home <existing-recovery-directory> --layout source --json
```

Preview first to inspect the exact delivery paths; use `--execute` when already authorized.
source uses source-relative paths. installed maps skills to .agents/skills and applies
only installer-managed Runtime/four-Skill payloads; inspect skipped_delivery_paths for
non-installable changes. Neither layout writes archive data or invokes arbitrary SQL.

The existing target must match the checked base files. Execution uses a target-level
POSIX file lock, private retained before/after material, atomic replacement per file and
SQLite progress. It preserves existing file permissions and does not stage the target Git
index. No whole-directory atomic switch or running-process hot reload is implied.
The target retains .agent-memory-system.lock as coordination metadata; do not delete it
while work may be alive. Rollback restores declared file images; check outputs and newly
created empty parent directories may remain.

Read `maintain-system --operation-key <key> --json`. Same-key terminal requests return
history; they do not revalidate today's files or repeat application. Running/interrupted
work is not retried on elapsed time. Inspect and explicitly resume:

```bash
python3 tools/agent_memory.py maintain-system-resume --project . --operation-key <apply-or-rollback-key> --json
```

`--execute` resumes only after acquiring the actual target lock and comparing retained
images. Already-correct paths are skipped; unexpected user edits, changed material or
journals stop without overwriting the conflict. Keep recovery directories until the
agreed retention/rollback scope ends; no automatic deletion is performed.

## Observe, Close Or Roll Back

```bash
python3 tools/agent_memory.py maintain-system-follow-up --project . --id <id> --expected-revision <applied-revision> --operation-key <monitor-key> --status monitoring --note <scope> --json
python3 tools/agent_memory.py maintain-system-follow-up --project . --id <id> --expected-revision <monitoring-revision> --operation-key <close-key> --status closed --note <reason> --json
python3 tools/agent_memory.py maintain-system-rollback --project . --id <id> --expected-revision <current-revision> --operation-key <rollback-key> --application-key <completed-apply-key> --json
```

These preview by default; actual checks/writes use `--execute` within authority. Monitoring
runs the predeclared checks in the applied directory. Failure, missing output and known
exit facts remain distinct. Closing needs successful current-application monitoring and
unchanged source/results. Its claim is limited to the declared checks, not long-term benefit.

Rollback restores code/rule preimages and leaves later Memory writes intact. It refuses
unexpected edits. Recover interrupted rollback with the same explicit resume entry.
To invalidate a checked candidate before application, follow-up supports needs_evidence.

`maintain-system-resolve` can abort a non-application operation without a success claim.
Valid previews return exit code 0. A completed resolve action also returns 0 while retaining
the original operation as failed; this means the abort completed, not that its checks passed.
An unobserved active child from a hard-crashed check cannot be cleared merely by time,
a stored PID or a model assertion; retain the unknown until independently reconciled.

Data downgrade is a separate `maintain-system-migrate --target-version system-evolution-v1`
action with a new backup. It preserves post-upgrade writes only when all proposal states
remain representable; otherwise retain a compatible Runtime or implement a forward repair.
Never overwrite the live archive with an old backup to make a code rollback look complete.
