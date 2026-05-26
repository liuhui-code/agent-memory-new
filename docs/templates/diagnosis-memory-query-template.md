# Diagnosis Skill + Memory Query Template

Use this template inside a bug diagnosis skill when the Agent needs to locate a problem recursively.

The goal is not to query memory once. The goal is to repeatedly compress the current investigation state into sharper queries until the problem frame stops changing.

## Principle

```text
Observe current evidence
  -> compress into sharper query
  -> query memory
  -> update hypotheses
  -> inspect smallest useful code/log target
  -> rewrite problem frame
  -> repeat
```

Memory is not evidence. Memory suggests where to look. Current logs, code, tests, and reproduction steps decide truth.

## Diagnosis State

Maintain this state during the skill run:

```json
{
  "problem_frame": "",
  "known_facts": [],
  "open_questions": [],
  "hypotheses": [
    {
      "id": "H1",
      "text": "",
      "confidence": 0.0,
      "evidence_for": [],
      "evidence_against": []
    }
  ],
  "memory_queries": [],
  "next_inspection_targets": []
}
```

## Recursive Query Loop

Run at most 4 rounds.

For each round:

1. Rewrite the current state into a sharper query.

   Good query shape:

   ```text
   <domain> <error signal> <module/function> <suspected mechanism>
   ```

2. Query memory:

   ```bash
   python tools/agent_memory.py context --project . --query "<sharpened query>" --json
   ```

3. Integrate returned memory:

   - `semantic_facts` become project constraints.
   - `reflections` become diagnostic checks.
   - `episodes` become recent-history risks.
   - `wiki_matches` become inspection targets.

4. Inspect only the smallest useful target:

   ```bash
   python tools/agent_memory.py wiki-search --project . --query "<module/function/error>" --json
   ```

5. Read current files/logs/tests and update:

   - known facts
   - rejected assumptions
   - hypothesis confidence
   - next query

6. Stop if one stopping condition is met.

## Stopping Conditions

Stop recursive memory querying when any condition is true:

- One hypothesis is specific, testable, and supported by current evidence.
- The last memory query returned no new useful information.
- The problem frame did not materially change for 2 rounds.
- 4 rounds have run.
- The Agent needs missing user input, logs, credentials, or reproduction steps.

## Output Shape For Diagnosis Skill

Before editing code, report:

```text
Current problem frame:
- ...

Memory-informed hypotheses:
- H1 ...
- H2 ...

Evidence checked:
- ...

Next smallest inspection:
- ...
```

## Reflection After Diagnosis

After fixing or reaching a useful stopping point:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<diagnosis task>" \
  --summary "<what was found>" \
  --mistake "<wrong assumption or empty>" \
  --lesson "<durable diagnostic lesson>" \
  --future-rule "<next-time rule>"
```

Then:

```bash
python tools/agent_memory.py vault-export --project .
```
