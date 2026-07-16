# Long-Term Data Governance Kernel Execution Plan

## Goal

Implement the current delivery phase from the long-term governance design while
keeping all existing databases and the fixed four-Skill user contract compatible.

## Tasks

- [x] Record the long-term hybrid governance architecture and explicit deferrals.
- [x] Remove the unfinished generic context-feedback table and CLI surface.
- [x] Add correlation, verification, idempotency, and lifecycle fields to
  retrieval and usage observations with in-place migrations.
- [x] Validate observation targets and implement lifecycle closure through the
  existing retrieval-feedback command.
- [x] Replace global-tail feedback reads with candidate-directed batched reads.
- [x] Require verified or independently repeated signals before ranking changes.
- [x] Treat `used`, `ignored`, and `superseded` as governance observations rather
  than direct ranking labels.
- [x] Expose stable/pending summaries and closure templates through maintain.
- [x] Update schema, runtime, Skill, and usage documentation.
- [x] Add lifecycle, idempotency, scale, and compatibility tests.
- [x] Run focused tests, full tests, compile checks, diff checks, and the 500-line
  source-file guard.

## Verification

- Focused feedback, calibration, usage, active-learning, and quality tests: 23 passed.
- Fingerprint, retrieval-feedback, and usage regression tests: 31 passed.
- Full regression: 366 tests passed in 1467.990 seconds.
- A synthetic 500,000-row SQLite probe used the candidate composite index and
  returned the bounded candidate set; the whole setup and probe took about 1.16
  seconds and is recorded as an index check, not a production benchmark.
- Python compilation, CLI help, diff whitespace, exactly-four-Skill, and
  500-line source-file checks passed.

## Deferred

- Durable `governance_cases` table.
- Append-only `governance_events` audit table.
- Feedback retention/archive jobs.
- Runtime self-modification or automatic ranking policy changes.
- Feedback for temporary runtime logs, code paths, or Agent reasoning.
