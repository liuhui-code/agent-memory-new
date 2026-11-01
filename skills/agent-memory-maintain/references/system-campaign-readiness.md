# Real-Activity Readiness

Use before proposing or creating a prospective real-task activity. Readiness is a read-only
input audit, not permission to collect tasks or invoke a model. If the user requests only
development contracts/isolation checks, keep the real activity stopped and use controlled
development fixtures for verification.

```bash
python3 tools/agent_memory.py maintain-system-campaign-readiness --project . --json
```

Use the actual --memory-home if configured. No --execute exists. The command does not open
Memory SQLite, initialize storage, record tasks, read task/source contents or call a model.
It reads only supplied bounded documents, Runtime's own Python files and local Git metadata.

## Collect The Missing Inputs

The result separates internal, external, campaign and evidence. Keep no_go when the real
project, future source or contract is absent; do not select another project or fill the
worksheet from old fixtures, current meta-work, consumed evaluation cases or invented tasks.

Obtain the actual values from the user or an already authorized, attributable source:

| Required input | Needed fact |
|---|---|
| Campaign project | Project path and responsible role |
| Task-start Memory | Intended Memory Home and task-before-write boundary |
| Future stream | Arrival source, continuity owner, start point |
| Verification | Objective test/build/reproduction or confirmation rules; preserve unknowns |
| Raw-task custody | Location outside SQLite, retention and responsible role/access rules |
| Fixed stopping | Presented count, exclusions, fixed stop; no positive optional stopping |

Do not infer authorization from a path, "confirmed" field or an inputs_valid_only result.
No source authentication, no-missing-task proof, miss-rate denominator or efficacy verdict
is established by checking declarations. Existing task records are not read by this audit.

## Preserve The Existing Contract Scope

The existing cohort API supports diagnosis/selective-query-skill/v1 only. Default
--intent system_evolution therefore retains unsupported_campaign_contract, even if a
diagnosis protocol is supplied. Do not relabel workflow/design/learning tasks as diagnosis
to bypass it. A generic system-improvement activity still needs source-specific design.

For an explicitly intended legacy diagnosis activity, supply the already prepared
prospective-agent-cohort/v1 protocol and campaign-source-manifest/v1:

```bash
python3 tools/agent_memory.py maintain-system-campaign-readiness --project . --intent diagnosis_query --protocol-file <protocol.json> --campaign-manifest <source-manifest.json> --json
```

Files are UTF-8 JSON objects, at most 32 KiB each, without duplicate keys. Current protocol/
manifest validation is reused. Raw fields (owners, paths, stream details) are not echoed;
the report supplies digests, bounded errors and missing requirement names. Generated
calibration is never a real-task source. inputs_valid_only means the existing structural
checks passed; activity_started, execution_authorized, evidence_verified, efficacy_verified
and promotion_eligible remain false.

The actual target Git revision/tree/status digest and Runtime Python code digest bind the
observation. Dirty status is not a content snapshot. The hosting checkout revision is not
an installed Runtime release identity; model/Skill/environment identity is outside this
code-only digest. Recheck after material changes instead of using an old report as approval.

Invalid eval-cohort-create protocol/source inputs are rejected before Memory initialization.
This preserves the valid diagnosis/calibration flow without creating archives on a no-go.
Never interpret successful creation/initialization as verification of real task provenance.
