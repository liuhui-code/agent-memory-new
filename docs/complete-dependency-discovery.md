# Complete discovery before incremental invalidation

This change is an independent reconstruction on an older locally available
baseline. It is not a restoration of the inaccessible previous candidate.

Incremental writers now use a stable physical-row cursor to read dependency
pages through EOF, instead of treating 2,000 returned paths as complete. The
existing three-hop ordinary-call policy remains unchanged. Legacy bounded
read-only discovery helpers are unchanged.

A single budget covers reverse and dispatch discovery, including endpoint
resolution and changed-source reads: 1,000,000 returned rows, 50,000 unique
paths, 20,000 SQL queries, 16 MiB source bytes, and 30 seconds. Exceeding a
budget, missing a referenced endpoint, or failing to inspect a changed source
raises `IncompleteDependencyDiscovery` before edge tracking or invalidation.
This is refusal, not a successful refresh or an incomplete-success result.

The writer holds one SQLite `BEGIN IMMEDIATE` transaction from discovery to
activation. Passage schema statements execute individually without
`executescript`'s implicit commit, including trigger bodies. Exceptions roll
back the writer's database mutations. This does not promise atomicity for
outer CLI scope bookkeeping or filesystem mirrors.

The new path does not fix non-call relation retention beyond the existing
three-hop rebuild scope, query ranking, or any previously reported 62 context
capability failures. Performance and complete regressions require separate
validation. Historical test evidence is not inherited by this reconstruction.

## Required source reads (new follow-up candidate)

The writer now rejects missing/unreadable required rebuild sources before invalidation,
and enforces the same rule at actual graph and semantic reads. Non-declared dependent
source bytes must match their indexed code_files source_digest; explicitly refreshed
files must match the bytes digested for this refresh. Changed dependents are not silently
added to the refresh scope. Include them explicitly or retry after restoring their indexed
contents. Required text is decoded from the exact checked bytes. Explicit retirement
and full replacement still permit removal; optional reads outside this writer scope
retain their former behavior. The policy is context-local and reset on success/failure.
These checks cover the bytes used, not a filesystem-wide transaction: filesystem edits
after a completed read are not locked. Original frozen candidate results are not
automatically evidence for this follow-up candidate.
