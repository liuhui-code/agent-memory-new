# Change Design Skill + Memory Query Template

Use this template inside a design or modification-planning skill when the Agent needs to propose a safe change.

The goal is to recursively refine the change plan by querying memory after each new design frame, not to query once and write a patch.

## Principle

```text
Understand requested change
  -> query memory for constraints
  -> inspect relevant code/wiki
  -> draft change frame
  -> query memory again using the draft's risks and touched areas
  -> refine plan
  -> stop when risks and affected areas are explicit
```

Memory is a source of constraints, prior decisions, and known failure modes. It is not proof that a design is correct.

## Change Design State

Maintain this state:

```json
{
  "change_goal": "",
  "affected_areas": [],
  "known_constraints": [],
  "open_design_questions": [],
  "candidate_approaches": [],
  "risks": [],
  "memory_queries": [],
  "files_to_inspect": []
}
```

## Recursive Query Loop

Run at most 4 rounds.

For each round:

1. Compress current design state into a sharper query.

   Good query shape:

   ```text
   <feature/module> <intended change> <risk/constraint> <affected symbol>
   ```

2. Query memory:

   ```bash
   python tools/agent_memory.py context --project . --query "<design query>" --json
   ```

3. Interpret memory:

   - `semantic_facts`: stable project rules and user preferences.
   - `reflections`: previous mistakes and design cautions.
   - `episodes`: related recent changes.
   - `wiki_matches`: files/symbols to inspect before planning.

4. Inspect relevant code/wiki:

   ```bash
   python tools/agent_memory.py wiki-search --project . --query "<affected module or symbol>" --json
   ```

5. Refine the design state:

   - add affected areas
   - remove invalid approaches
   - add risks
   - sharpen open questions
   - update files to inspect

6. Stop if a stopping condition is met.

## Stopping Conditions

Stop recursive memory querying when any condition is true:

- A minimal safe approach is clear.
- The next query repeats the previous query without new information.
- A blocking design question requires the user.
- 4 rounds have run.
- Risks and affected areas are explicit enough to write an implementation plan.

## Output Shape For Design Skill

Before implementation, report:

```text
Design goal:
- ...

Memory constraints:
- ...

Affected areas:
- ...

Candidate approaches:
- Recommended: ...
- Alternative: ...

Risks:
- ...

Verification plan:
- ...
```

## Reflection After Change

After implementation and verification:

```bash
python tools/agent_memory.py reflect \
  --project . \
  --task "<change task>" \
  --summary "<what changed>" \
  --lesson "<durable design lesson>" \
  --future-rule "<next-time rule>"
```

Then:

```bash
python tools/agent_memory.py vault-export --project .
```
