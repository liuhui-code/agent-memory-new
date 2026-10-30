# Prepare An Isolated Candidate For Checking

Use this reference when a prepared system proposal has an actual Git patch, a full base
commit and authorized development-copy preparation. The source has passed isolated
synthetic Git/SQLite regressions. Do not run it under a current skip-verification instruction merely
to make a report look complete; installed command availability is not guaranteed.

## Bind And Prepare

Read the current `maintain-system --change-id <id> --json` result. The proposal must be
prepared, its base_version a complete local Git commit OID, and the patch a relative file
inside artifact_manifest.development_root that is already listed in its artifact set.
Use the observed state_revision and an opaque namespaced candidate-key. Current check or
candidate-preparation work must be terminal before preparing another candidate.

Choose an existing authorized candidate-home outside the source tree and Memory Home.
The Runtime creates a fresh private child there. It does not overwrite an existing
workspace or stage/checkout changes in the source repository. Preview is the default:

```bash
python3 tools/agent_memory.py maintain-system-candidate --project . --id <id> --expected-revision <prepared-revision> --candidate-key <key> --patch-file candidate.patch --candidate-home <authorized-candidate-home> --json
```

Only when preparation is authorized, add `--execute`. The Runtime copies a local Git
baseline without shared object hardlinks/alternates, applies the bound patch to the new
copy's index and worktree, and records its resulting tree and changed-file byte identities.
It does not run candidate code, initialize submodules, commit, push or update an installed
product. Metadata goes to SQLite; source material stays in the explicit candidate directory.

Ready means preparation finished, not checks passed. Failed/interrupted candidates and
their partial directories are retained. A preparing row can be live or unresolved; do not
retry or infer termination from elapsed time. Same-key terminal retries return the original
history without recreating or revalidating the directory. New requests need new keys.

Use `maintain-system --candidate-key <key> --json` for the bounded record, or --change-id
for bounded history. Each patch is at most 1 MiB; at most 100 changed paths are observed,
at most 16 MiB per changed file/link and 256 MiB total. Unsafe/unobservable path types fail;
submodule internals and Gitlink changes do not become authenticated executable source.
Do not delete a retained directory automatically; inspect its ownership and user changes
before any separately authorized cleanup.

## Use Check Plan v2

Read system-checks.md for the shared check contract. To check the candidate, set
schema_version to system-change-check-plan/v2 and add the returned candidate_key plus
receipt.candidate_digest. Other fields stay required:

```json
{
  "schema_version": "system-change-check-plan/v2",
  "proposal_id": 1,
  "prepared_state_revision": 2,
  "artifact_digest": "<actual-prepared-artifact-digest>",
  "candidate_key": "<actual-candidate-key>",
  "candidate_digest": "<actual-candidate-digest>",
  "source_files": [{"path": "<candidate-relative-test-file>", "digest": "<actual-sha256>"}],
  "checks": [{"key": "<check-key>", "argv": ["<absolute-executable>", "<candidate-relative-script>"], "assertion_indices": [0], "timeout_seconds": 60}]
}
```

This is an unexecuted template. Keep the plan itself inside the original development
root; v2 source_files and process cwd refer to the recorded candidate root. Prefer the
candidate's relative entrypoints rather than absolute old-source scripts. The Runtime
checks actual HEAD/index/tracked-worktree observations and all patch-changed file bytes
before and after commands, plus the declared source/test digests. Drift stops later checks.

These observations are non-atomic and do not authenticate untracked/ignored files,
dependencies, environment, coverage or whether arbitrary commands actually used the
candidate's source. Inspect command entrypoints, imports, expected assertions and evidence
in the Agent. Records retain command_source_use_verified=false and no automatic
checked/applied transition. v1 remains available for declared-file observations; it does
not gain candidate binding or release eligibility retroactively.
