# Builder work recovery after workspace rollback

The resumed workspace no longer contained the newer integration checkout or its
Builder worktree/bundle. The public repair branch was independently read back at
6371d43054d17867ef79ea039b5b0ccbeaed2291; main remained
320e95137a890403cbd6496858a8a1c7de79c6ec. A fresh clone of that branch is clean and
passes git fsck connectivity checks. Published work is intact.

Unpublished local Builder implementation and integration commits previously
reported as 33a55ee/fef3ceb/e28feb3 cannot be verified from retained local objects.
Their prior 66-related/39-integration observations are historical reports, not
fresh acceptance evidence. Rebuild the bounded positive declaration-role change
from the published design, freeze controls again, and retain new actual results.
Do not claim byte-identical recovery or synthesize the missing test outputs.

The implementation scope is unchanged: real supported ArkTS @Builder binding in
existing callable metadata; no consumer ranking, new schema, absence inference,
query rewrite or full suite. Rejected request-grammar drafts were not executed and
are not serving candidates. Original repaired-variant count remains 20.
