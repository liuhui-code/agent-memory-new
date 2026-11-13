# Process output read loop investigation

Base: 4005b65. Independent Development only; no full gate/231/holdout run.
Existing process-output-read-loop group is still 1/3 (English paraphrase passes;
original and Chinese fail with extra anchors). Required source spans are present.

Frozen independent competition has PipeCollector.collect with a real readLine
loop, push accumulation and join, plus descriptive label methods and SingleRead.
Public compact chooses OutputDescription.label for the generic request. Explicit
method queries retain the right file but use class/file anchors; the protocol's
specific symbol controls therefore also do not pass. Do not rewrite expectations.

A narrow trial attached the existing OUTPUT_LOOP/READ/ACCUMULATION predicates to
masked nonnested callable evidence. It did not improve any public outcomes or
the original group. The production change was reverted, retained only as
rejected-marker.patch. No new marker/selection/scoring/threshold change is shipped.

Read-only instrumentation of diverse_code_matches records the first loss:
- Candidate collect is recalled with outputreadloop, score 18.5.
- Descriptive OutputDescription.label scores 55.5, PipeCollector.label 30.5.
- focus_code_candidates returns the full set, focused=False. This differs from
  archive's strong-identity focus loss.
- Diversity/budget selection returns five candidates including the description
  class/file and drops the real collector before compact localization.
Thus another method label cannot fix this downstream admission/budget boundary.
Shared evidence with the selection worker; no relaxed guard or new special case.

Only this three-variant scenario and the three frozen independent queries ran,
with baseline/candidate and diagnostic observations separated. No accepted
production fix, aggregate improvement, external efficacy or publication claim.
