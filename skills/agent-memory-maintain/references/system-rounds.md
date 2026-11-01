# Persistent System-Evolution Rounds

Use this workflow only for authorized durable recording of an actual system-change review.
R1 outcome context remains read-only. R2 records immutable plan/context snapshots, Agent
assessments and advisory decisions in the existing archive; it runs no model or deployment.

## Explicit Installation

The archive must already have governance v2. Preview and explicitly install the independent
round component with a new backup outside Memory Home:

```bash
python3 tools/agent_memory.py maintain-system-migrate --project . --target-version system-rounds-v1 --backup-file <new-backup.db> --json
python3 tools/agent_memory.py maintain-system-migrate --project . --target-version system-rounds-v1 --backup-file <new-backup.db> --execute --json
```

This uses the existing migration writer exclusion, backup, transaction and integrity checks.
No ordinary read/init or round record installs the table. Unknown versions, partial storage
or missing immutability guards are rejected. The component has no destructive uninstall;
preserve the compatible Runtime/records or implement a separately validated forward repair.
Never restore an old full backup over later Memory writes.

## Strict Record Format

Write bounded UTF-8 JSON, at most 32 KiB, with no duplicate keys or unsupported fields.
Every record requires schema_version=`system-evolution-round-record/v1`, kind, record_key,
study_key, round_key and expected_revision. Keys use 1–160 opaque ASCII letters/digits/`_.:-`,
starting with a letter/digit. record_key is an idempotency key within this project/archive.

Additional required fields depend on kind:

| Kind | Fields |
|---|---|
| open | parent_round_key (null for the first round), proposal_id, application_key, plan_file, budget |
| assessment | observations_file, observations_digest, finding, summary, evidence_refs, additional_cost |
| decision | assessment_revision, decision, note, evidence_refs |

Opening has expected_revision=0. round_key must equal the pre-bound R1 plan's round_key;
plan_file is relative to that proposal's development root. The actual completed application
must match R1. budget has exactly max_rounds (1–10) and max_assessments (1–20). Budgets freeze
at the first round of a study. These limit recorded rounds/assessments, not unobserved model
calls or Token spending. Host budgets still govern actual model/tool work.

Every child names the latest decided, non-stop parent in the same study and archive, uses
the same count budget, and has a new bound plan or candidate. One study has at most one
undecided round. Do not change study/archive/task keys to evade budget or independence rules.
Caller identity and external independence are not authenticated by this ledger.

An assessment declares the observation file's lowercase SHA-256; it must match actual R1
reading and the round's original plan/application identity. finding is supported,
contradicted or inconclusive: all are Agent opinions. summary is at most 600 characters.
evidence_refs has at most eight single-line references of 240 characters; supported or
contradicted requires at least one. additional_cost has exactly tokens and elapsed_ms,
each null or a nonnegative integer at most 2^53−1. These remain declared review costs.

A decision is keep_baseline, adopt_candidate, rollback, inconclusive or stop. note is at
most 600 characters; references have the same bound. Reference the latest assessment revision;
stop alone can use null without an assessment. Decision recording changes no proposal or
installed code. Actual apply/rollback continues through the existing separately authorized
lifecycle commands.

An adopt_candidate recommendation additionally requires a supported assessment, unchanged
observation input, a declared complete window with included all-pass outcomes, known task
costs, matching applied images and no failed monitoring, unresolved work or truncated history.
These are completeness guards, not authentication, causal evidence or external promotion.

## Preview, Record And Read

```bash
python3 tools/agent_memory.py maintain-system-round-record --project . --payload-file <record.json> --json
python3 tools/agent_memory.py maintain-system-round-record --project . --payload-file <record.json> --execute --json
python3 tools/agent_memory.py maintain-system-round --project . --json
python3 tools/agent_memory.py maintain-system-round --project . --round-key <key> --limit 5 --json
python3 tools/agent_memory.py maintain-system-round --project . --round-key <key> --revision 2 --json
```

Use the actual --memory-home when configured. Preview validates without writing. The explicit
writer serializes changes with BEGIN IMMEDIATE, checks expected_revision and appends exactly
one event. Same-key identical input returns history; conflicting input is rejected. Historical
retries do not reread today's source files or revalidate an old decision.

Read by key/revision needs no original input file. SQLite retains typed R1 plan/context and
task declarations with their digests; no raw logs, tasks, queries, source, commands or private
reasoning are added. Event digests and update/delete guards protect the normal API history,
not against a database owner who rewrites storage and hashes. history_authenticated stays false.
Full snapshots are bounded to 128 KiB; history defaults to 5 summaries, at most 20, with truncation.

Use receipt.state to determine whether a round is decided: the latest event may be a late
assessment. A non-stop decided round can accept new observed context within its original
assessment budget; the decision and decision_revision stay fixed. Identical-context late
opinions are rejected. A stopped round accepts no new events. New information never silently
reopens a round, alters a parent decision or starts another iteration.

Unresolved lifecycle work blocks opens/assessments and actionable recommendations. Explicit
stop/inconclusive recording can freeze the ledger without claiming that a child process or
application ended; its actual unresolved records remain untouched. Follow existing recovery
protocols, never infer process death from time or model assertions.

Always report declarations, negative/unknown evidence and missing costs separately. A stored
supported finding or adopt recommendation remains advisory; efficacy_verified,
evidence_verified, promotion_eligible and application_performed stay false. R2 supplies no
automatic loop, success sampling, causal measurement or independent task source.
