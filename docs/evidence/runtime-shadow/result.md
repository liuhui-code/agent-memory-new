# Runtime operation shadow safety repair

Base 27d6afd. The published v2 name-shape witness did not recognize destructuring
or direct reassignment of its runtime API names. Independent fixed controls
reproduce that source_operation:runtimecapability was granted to locally rebound
canIUse, hasSystemCapability or bundleManager.

Conservatively mark relevant declaration/assignment destructuring and direct or
compound rebinding unknown. This does not resolve platform binding; calls remain
bounded syntactic evidence. Text/comments and unrelated destructuring controls
remain unchanged. No new operation kind, selection rule or score is added.

Checked token is now v2.1. The consumer rejects old v1/v2 roles rather than accept
cached pre-fix proof. Existing indexed projects must relearn before regaining
source-operation priority; ordinary lexical retrieval remains available.

Focused validation: 20 tests pass, including the existing public capability
fixture and stale checked-token rejection. Original capability group is 3/3.
No full suite/231 run. This is independent of unaccepted archive/loop v3 work.
