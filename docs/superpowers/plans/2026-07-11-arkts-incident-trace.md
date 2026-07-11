# ArkTS Incident Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a small but extensible ArkTS incident trace layer that turns temporary user logs and symptoms into compact, code-anchored diagnosis traces.

**Architecture:** Keep the four public skills unchanged and keep `tools/agent_memory.py` as the only runtime entry point. Store only compressed incident traces and links in SQLite; do not persist raw user log streams. Put new behavior in small focused runtime modules so no new file exceeds 500 lines and existing large files only receive thin adapter changes.

**Tech Stack:** Python 3.9+, SQLite, SQLite FTS5, existing `code_log_statements`, existing `memory_edges`, existing `context/search/maintain-plan` runtime commands.

---

## Design Boundary

ArkTS Incident Trace sits between raw runtime logs and durable reflections:

```text
temporary user log + symptom
  -> incident-trace command
  -> incident_traces + incident_trace_links
  -> context/search incident_trace_matches
  -> maintain-plan review/promote/stale actions
  -> reflect procedure_experience or incident strategy candidate
```

It must not become a general log platform. The runtime stores:

- normalized symptom
- ArkTS scene
- short dominant log event strings
- matched code log anchors
- linked code files, symbols, and memory edges
- compact candidate chain
- diagnosis or resolution summary when available

The runtime must not store full raw log files.

## File Size Rule

This feature must preserve long-term maintainability:

- Every new Python module must stay under 500 lines.
- Every new test file must stay under 500 lines.
- Existing files already over 500 lines must receive only thin imports, parser registration, or dispatch glue.
- If implementation pressure would push a new file over 500 lines, split by responsibility before continuing.
- Add a focused line-count check to the verification task for new incident trace files.

Current large files such as `query.py`, `governance.py`, `code_wiki.py`, and `tests/test_agent_memory.py` are not refactored in this feature. This plan prevents further growth by moving incident logic into new modules.

## New Modules And Responsibilities

Create these files:

- `tools/agent_memory_runtime/incident_trace_models.py`
  - constants, allowed statuses, ArkTS scene names, row shaping helpers
  - no database writes

- `tools/agent_memory_runtime/incident_trace_schema.py`
  - schema DDL strings and migration helper functions for incident tables and FTS
  - called from `storage.create_schema`

- `tools/agent_memory_runtime/incident_trace_builder.py`
  - symptom/log normalization
  - ArkTS scene classification
  - code log matching via existing FTS recall helpers
  - memory edge expansion
  - compact candidate chain building

- `tools/agent_memory_runtime/incident_trace.py`
  - public command handlers:
    - `incident_trace_command`
    - `incident_trace_status`
    - `incident_trace_list`
  - database writes and JSON output

- `tools/agent_memory_runtime/incident_trace_query.py`
  - incident trace retrieval for `context/search`
  - ranking and bounded output formatting

- `tools/agent_memory_runtime/incident_trace_governance.py`
  - maintain-plan candidates:
    - `review_incident_trace`
    - `merge_similar_incident_traces`
    - `promote_incident_trace_to_reflection`
    - `review_incident_trace_staleness`
    - `review_log_anchor_gap`

- `tests/test_incident_trace.py`
  - all incident trace tests
  - keep independent from the existing large `tests/test_agent_memory.py`

Modify these files with thin adapters only:

- `tools/agent_memory.py`
  - import command handlers and add them to the command map

- `tools/agent_memory_runtime/cli.py`
  - register new CLI subcommands

- `tools/agent_memory_runtime/storage.py`
  - call incident schema helper from `create_schema`

- `tools/agent_memory_runtime/query.py`
  - import and call `incident_trace_query.collect_incident_trace_matches`
  - add `incident_trace_matches` to bounded payloads

- `tools/agent_memory_runtime/governance.py`
  - import and extend actions with `incident_trace_governance.build_incident_trace_actions`

- `tools/agent_memory_runtime/records.py`
  - map `incident-trace` and `incident-trace-link` list types if list integration is chosen

- `references/schema.md`
  - document new tables

- `docs/code-log-statement-network.md`
  - document trace relation to code logs and memory edges

- `docs/runtime.md`
  - document command and query output

- `docs/usage-guide.md`
  - document skill usage through existing four skills

- `skills/agent-memory-query/SKILL.md`
  - explain how to consume `incident_trace_matches`

- `skills/agent-memory-maintain/SKILL.md`
  - explain trace governance actions

- `skills/agent-memory-reflect/SKILL.md`
  - explain how to reference `incident_trace:<id>` in `source_cases`

- `gitlog.md`
  - record local development notes and rollback path

## SQLite Model

Add `incident_traces`:

```sql
CREATE TABLE IF NOT EXISTS incident_traces (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  trace_key TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open',
  symptom TEXT NOT NULL,
  goal TEXT,
  arkts_scene TEXT NOT NULL DEFAULT 'unknown',
  time_window TEXT,
  entry_log_text TEXT,
  normalized_error TEXT,
  dominant_log_events TEXT,
  diagnosis_summary TEXT,
  suspected_chain TEXT,
  root_cause_hypothesis TEXT,
  resolution TEXT,
  confidence REAL DEFAULT 0.7,
  source TEXT DEFAULT 'incident-trace',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

Add `incident_trace_links`:

```sql
CREATE TABLE IF NOT EXISTS incident_trace_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL,
  trace_id INTEGER NOT NULL,
  target_type TEXT NOT NULL,
  target_id INTEGER,
  target_key TEXT,
  relation TEXT NOT NULL,
  score REAL DEFAULT 0.0,
  evidence TEXT,
  created_at TEXT NOT NULL
);
```

Add indexes:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS idx_incident_traces_project_key
ON incident_traces(project_id, trace_key);

CREATE INDEX IF NOT EXISTS idx_incident_traces_project_status
ON incident_traces(project_id, status, updated_at);

CREATE INDEX IF NOT EXISTS idx_incident_traces_project_scene
ON incident_traces(project_id, arkts_scene, updated_at);

CREATE INDEX IF NOT EXISTS idx_incident_trace_links_trace
ON incident_trace_links(project_id, trace_id);

CREATE INDEX IF NOT EXISTS idx_incident_trace_links_target
ON incident_trace_links(project_id, target_type, target_id);
```

Add FTS:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS incident_trace_fts USING fts5(
  project_id UNINDEXED,
  symptom,
  goal,
  arkts_scene,
  entry_log_text,
  normalized_error,
  dominant_log_events,
  diagnosis_summary,
  suspected_chain,
  root_cause_hypothesis,
  resolution
);
```

Create insert/update/delete triggers consistent with the existing FTS style in `storage.py`.

## Public Runtime Commands

Add:

```bash
python tools/agent_memory.py incident-trace --project . --symptom "<symptom>" --log-text "<short log text>" --json
python tools/agent_memory.py incident-trace --project . --symptom "<symptom>" --log-file /tmp/runtime.log --json
python tools/agent_memory.py incident-trace-status --project . --id 12 --status resolved --resolution "<summary>" --json
python tools/agent_memory.py list --project . --type incident-trace --json
python tools/agent_memory.py list --project . --type incident-trace-link --json
```

Validation rules:

- `--symptom` is required.
- Exactly one of `--log-text` or `--log-file` is required.
- `--log-file` reads at most a bounded number of bytes. First version limit: 64 KB.
- Store only `entry_log_text` trimmed to a maximum of 2,000 characters.
- `status` values: `open`, `diagnosed`, `resolved`, `stale`, `ignored`.

## ArkTS Scene Classifier

Implement deterministic first-pass scene classification:

```text
route:
  triggers: 页面跳转, 白屏, router, pushUrl, replaceUrl, route, navigation

resource:
  triggers: 图片, 图标, 字符串, 资源, $r, app.media, app.string, resource

network:
  triggers: 请求, 接口, 加载, fetch, request, response, http, profile, data

permission:
  triggers: 权限, permission, grant, authorize, network permission

ability:
  triggers: Ability, want, startup, lifecycle, onCreate, onForeground

state:
  triggers: session, token, login, auth, cache, empty state, 空数据

unknown:
  fallback
```

The classifier uses symptom + log text. Return both:

- `arkts_scene`
- `scene_reasons`

Only `arkts_scene` is persisted in the trace row. `scene_reasons` is returned in JSON output for explainability.

## Trace Builder Output

`incident_trace_builder.build_incident_trace_draft(project, symptom, log_text)` returns:

```python
{
    "trace_key": "...",
    "symptom": "...",
    "arkts_scene": "route",
    "scene_reasons": ["symptom:页面跳转", "log:router.pushUrl"],
    "entry_log_text": "...",
    "normalized_error": "...",
    "dominant_log_events": ["router.pushUrl failed"],
    "matched_code_logs": [
        {
            "id": 44,
            "file_path": "entry/src/main/ets/pages/Home.ets",
            "function": "openProfile",
            "message_template": "router.pushUrl failed",
            "score": 8.5
        }
    ],
    "linked_targets": [
        {
            "target_type": "code_log_statement",
            "target_id": 44,
            "target_key": "entry/src/main/ets/pages/Home.ets::router.pushUrl failed",
            "relation": "matched_log",
            "score": 8.5,
            "evidence": "matched dominant log event"
        }
    ],
    "candidate_chain": [
        "Home.ets::openProfile emits router.pushUrl failed"
    ],
    "inspection_targets": [
        "entry/src/main/ets/pages/Home.ets"
    ],
    "suggested_followup_query": "router.pushUrl Home.ets Profile route"
}
```

## Query Integration

`context/search` responses add:

```json
"incident_trace_matches": []
```

Bounded limits:

- context: max 5 incident traces
- search: max 10 incident traces
- each trace includes max 5 links
- each trace includes max 5 candidate chain entries

When `infer_memory_intent(query)` returns `incident_diagnosis`, query should surface:

```text
code_log_matches
edge_matches
incident_trace_matches
correction_guards
procedure_experience
```

Do not let incident traces outrank current source code or current code log anchors. Incident traces are diagnosis memory, not source truth.

## Maintain Integration

`maintain-plan` adds trace governance actions:

```text
review_incident_trace
merge_similar_incident_traces
promote_incident_trace_to_reflection
review_incident_trace_staleness
review_log_anchor_gap
```

Rules:

- `review_incident_trace`: open trace older than 7 days or confidence below 0.6.
- `merge_similar_incident_traces`: same scene and high token overlap in `symptom + dominant_log_events`.
- `promote_incident_trace_to_reflection`: trace is `resolved`, has at least one code anchor, and has no linked reflection.
- `review_incident_trace_staleness`: linked code file/log anchor no longer exists after learn refresh.
- `review_log_anchor_gap`: trace has strong log text but no `code_log_statement` match.

Actions are read-only and confirmation-oriented. They never auto-write reflections or mark traces stale.

## Reflection Integration

`reflect` does not need new columns in phase one.

Use existing fields:

```json
{
  "experience_type": "procedure_experience",
  "task_type": "diagnosis",
  "source_cases": ["incident_trace:12"],
  "inspection_targets": ["entry/src/main/ets/pages/Home.ets"],
  "useful_followup_focus": "route",
  "useful_followup_terms": ["router.pushUrl", "Profile", "route"],
  "verification_method": "Reproduce navigation and confirm route registry."
}
```

Maintain may return a `reflection_payload_template` for resolved traces, but the actual reflection write remains a separate explicit `reflect` command.

## Task 1: Schema And Storage Hook

**Files:**

- Create: `tools/agent_memory_runtime/incident_trace_models.py`
- Create: `tools/agent_memory_runtime/incident_trace_schema.py`
- Modify: `tools/agent_memory_runtime/storage.py`
- Modify: `references/schema.md`
- Test: `tests/test_incident_trace.py`

- [ ] **Step 1: Write failing schema test**

Add `tests/test_incident_trace.py` with a test that initializes a temp project and verifies these tables exist:

```python
def test_incident_trace_schema_is_created(self) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        project = Path(temp_dir)
        self.run_memory(project, "init")
        db_path = self.project_memory_dir(project) / "memory.db"
        with sqlite3.connect(db_path) as conn:
            names = {
                row[0]
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table', 'virtual')")
            }
        self.assertIn("incident_traces", names)
        self.assertIn("incident_trace_links", names)
        self.assertIn("incident_trace_fts", names)
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_incident_trace.AgentMemoryIncidentTraceTests.test_incident_trace_schema_is_created
```

Expected:

```text
FAIL: incident_traces not found
```

- [ ] **Step 3: Add model constants**

Create `incident_trace_models.py` with:

```python
from __future__ import annotations

INCIDENT_TRACE_STATUSES = {"open", "diagnosed", "resolved", "stale", "ignored"}
INCIDENT_TRACE_QUERY_LIMIT = 5
INCIDENT_TRACE_SEARCH_LIMIT = 10
INCIDENT_TRACE_LINK_LIMIT = 5
INCIDENT_LOG_TEXT_LIMIT = 2000
INCIDENT_LOG_FILE_BYTES_LIMIT = 64 * 1024

ARKTS_SCENES = {
    "route",
    "resource",
    "network",
    "permission",
    "ability",
    "state",
    "unknown",
}
```

- [ ] **Step 4: Add schema helper**

Create `incident_trace_schema.py` with a function:

```python
def create_incident_trace_schema(conn: sqlite3.Connection) -> None:
    ...
```

Implement the two tables, indexes, FTS virtual table, and FTS triggers from the SQLite model above.

- [ ] **Step 5: Hook schema helper into storage**

In `storage.py`, import and call:

```python
from .incident_trace_schema import create_incident_trace_schema

...

create_incident_trace_schema(conn)
```

Keep the storage change limited to import + one call.

- [ ] **Step 6: Run the schema test**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_incident_trace.AgentMemoryIncidentTraceTests.test_incident_trace_schema_is_created
```

Expected:

```text
OK
```

- [ ] **Step 7: Update schema docs**

In `references/schema.md`, add a short section describing `incident_traces` and `incident_trace_links`.

- [ ] **Step 8: Commit**

```bash
git add tools/agent_memory_runtime/incident_trace_models.py tools/agent_memory_runtime/incident_trace_schema.py tools/agent_memory_runtime/storage.py references/schema.md tests/test_incident_trace.py
git commit -m "feat: add incident trace schema"
```

## Task 2: Trace Builder

**Files:**

- Create: `tools/agent_memory_runtime/incident_trace_builder.py`
- Test: `tests/test_incident_trace.py`

- [ ] **Step 1: Write failing classifier tests**

Add tests:

```python
def test_classifies_arkts_route_incident(self) -> None:
    from tools.agent_memory_runtime.incident_trace_builder import classify_arkts_scene

    scene, reasons = classify_arkts_scene("页面跳转后白屏", "router.pushUrl failed")

    self.assertEqual(scene, "route")
    self.assertTrue(any("router" in reason.lower() for reason in reasons))


def test_classifies_arkts_resource_incident(self) -> None:
    from tools.agent_memory_runtime.incident_trace_builder import classify_arkts_scene

    scene, reasons = classify_arkts_scene("图片资源显示不出来", "$r('app.media.avatar')")

    self.assertEqual(scene, "resource")
    self.assertTrue(reasons)
```

- [ ] **Step 2: Run classifier tests and verify they fail**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_incident_trace.AgentMemoryIncidentTraceTests.test_classifies_arkts_route_incident tests.test_incident_trace.AgentMemoryIncidentTraceTests.test_classifies_arkts_resource_incident
```

Expected:

```text
ImportError or AttributeError for classify_arkts_scene
```

- [ ] **Step 3: Implement deterministic classifier**

Add `classify_arkts_scene(symptom: str, log_text: str) -> tuple[str, list[str]]`.

Use explicit trigger dictionaries for `route`, `resource`, `network`, `permission`, `ability`, and `state`. Return `unknown` when no trigger matches.

- [ ] **Step 4: Run classifier tests**

Run the same test command.

Expected:

```text
OK
```

- [ ] **Step 5: Write failing trace builder test**

Create a temp ArkTS file with a `router.pushUrl` log, run `learn-path`, then call `build_incident_trace_draft`.

Assert:

- `arkts_scene == "route"`
- at least one `matched_code_logs`
- at least one `linked_targets` with `relation == "matched_log"`
- `candidate_chain` is non-empty
- `suggested_followup_query` contains `router` or `pushUrl`

- [ ] **Step 6: Run trace builder test and verify it fails**

Expected failure:

```text
AttributeError: build_incident_trace_draft
```

- [ ] **Step 7: Implement trace builder**

Implement:

```python
def build_incident_trace_draft(project: Project, symptom: str, log_text: str) -> dict[str, Any]:
    ...
```

Use existing code log search paths instead of hand-written SQL wherever practical. Use `code_log_fts` and existing row shaping style from `query.py`. Keep output bounded.

- [ ] **Step 8: Run trace builder tests**

Expected:

```text
OK
```

- [ ] **Step 9: Commit**

```bash
git add tools/agent_memory_runtime/incident_trace_builder.py tests/test_incident_trace.py
git commit -m "feat: build ArkTS incident trace drafts"
```

## Task 3: CLI Write And Status Commands

**Files:**

- Create: `tools/agent_memory_runtime/incident_trace.py`
- Modify: `tools/agent_memory.py`
- Modify: `tools/agent_memory_runtime/cli.py`
- Modify: `tools/agent_memory_runtime/records.py`
- Test: `tests/test_incident_trace.py`

- [ ] **Step 1: Write failing CLI write test**

Test:

```python
def test_incident_trace_command_writes_compact_trace(self) -> None:
    ...
    result = self.run_memory(
        project,
        "incident-trace",
        "--symptom",
        "页面跳转后白屏",
        "--log-text",
        "router.pushUrl failed for ProfileDetail",
        "--json",
    )
    payload = json.loads(result.stdout)
    self.assertEqual(payload["arkts_scene"], "route")
    self.assertLessEqual(len(payload["entry_log_text"]), 2000)
    traces = self.list_records(project, "incident-trace")
    self.assertEqual(len(traces), 1)
```

- [ ] **Step 2: Run CLI write test and verify it fails**

Expected:

```text
invalid choice: incident-trace
```

- [ ] **Step 3: Implement command handler**

In `incident_trace.py`, implement:

```python
def incident_trace_command(args: argparse.Namespace) -> None:
    ...
```

Responsibilities:

- resolve project
- ensure initialized
- read bounded log text
- call `build_incident_trace_draft`
- upsert trace by `trace_key`
- replace links for that trace
- output JSON

- [ ] **Step 4: Register parser and command map**

In `cli.py`, add `incident-trace` parser with `--symptom`, `--log-text`, `--log-file`, `--json`.

In `tools/agent_memory.py`, import and add `incident_trace_command` to the command map.

- [ ] **Step 5: Add record list types**

In `records.py` and `cli.py`, support:

```text
incident-trace -> incident_traces
incident-trace-link -> incident_trace_links
```

- [ ] **Step 6: Run CLI write test**

Expected:

```text
OK
```

- [ ] **Step 7: Write and implement status test**

Test `incident-trace-status --id <id> --status resolved --resolution "<summary>" --json`.

Expected output includes `status == "resolved"` and persisted row has `resolution`.

- [ ] **Step 8: Commit**

```bash
git add tools/agent_memory_runtime/incident_trace.py tools/agent_memory.py tools/agent_memory_runtime/cli.py tools/agent_memory_runtime/records.py tests/test_incident_trace.py
git commit -m "feat: add incident trace runtime commands"
```

## Task 4: Query Integration

**Files:**

- Create: `tools/agent_memory_runtime/incident_trace_query.py`
- Modify: `tools/agent_memory_runtime/query.py`
- Modify: `docs/runtime.md`
- Modify: `skills/agent-memory-query/SKILL.md`
- Test: `tests/test_incident_trace.py`

- [ ] **Step 1: Write failing query test**

Test:

```python
def test_context_returns_incident_trace_matches_for_similar_symptom(self) -> None:
    ...
    self.run_memory(project, "incident-trace", "--symptom", "页面跳转后白屏", "--log-text", "router.pushUrl failed", "--json")
    result = self.run_memory(project, "context", "--query", "Profile 页面白屏 router failed", "--json")
    payload = json.loads(result.stdout)
    self.assertIn("incident_trace_matches", payload)
    self.assertEqual(payload["incident_trace_matches"][0]["arkts_scene"], "route")
```

- [ ] **Step 2: Run query test and verify it fails**

Expected:

```text
incident_trace_matches missing or empty
```

- [ ] **Step 3: Implement incident trace query module**

Implement:

```python
def collect_incident_trace_matches(project: Project, query: str, limit: int) -> list[dict[str, Any]]:
    ...
```

Use `incident_trace_fts` when available. Fall back to bounded LIKE matching only if FTS is unavailable.

- [ ] **Step 4: Add bounded output to query**

In `query.py`, add `incident_trace_matches` to:

- `collect_matches`
- `bounded_matches`
- `limited_context`
- `limited_search`

Keep the edit thin. Formatting and scoring stay in `incident_trace_query.py`.

- [ ] **Step 5: Run query test**

Expected:

```text
OK
```

- [ ] **Step 6: Update query docs**

Document `incident_trace_matches` in `docs/runtime.md` and `skills/agent-memory-query/SKILL.md`.

- [ ] **Step 7: Commit**

```bash
git add tools/agent_memory_runtime/incident_trace_query.py tools/agent_memory_runtime/query.py docs/runtime.md skills/agent-memory-query/SKILL.md tests/test_incident_trace.py
git commit -m "feat: return incident trace matches in query"
```

## Task 5: Maintain Governance

**Files:**

- Create: `tools/agent_memory_runtime/incident_trace_governance.py`
- Modify: `tools/agent_memory_runtime/governance.py`
- Modify: `skills/agent-memory-maintain/SKILL.md`
- Modify: `skills/agent-memory-reflect/SKILL.md`
- Test: `tests/test_incident_trace.py`

- [ ] **Step 1: Write failing maintain-plan test**

Create a resolved incident trace with one code anchor and no linked reflection.

Assert `maintain-plan --json` returns:

```text
promote_incident_trace_to_reflection
```

with a `reflection_payload_template` that includes `source_cases: ["incident_trace:<id>"]`.

- [ ] **Step 2: Run maintain-plan test and verify it fails**

Expected:

```text
StopIteration for promote_incident_trace_to_reflection
```

- [ ] **Step 3: Implement governance module**

Implement:

```python
def build_incident_trace_actions(project: Project, limit: int) -> list[dict[str, Any]]:
    ...
```

Include only read-only actions. Do not mutate traces.

- [ ] **Step 4: Hook into maintain-plan**

In `governance.py`, import and extend:

```python
actions.extend(build_incident_trace_actions(project, args.limit))
```

Add counts to `governance_summary`:

```text
incident_trace_reviews
```

- [ ] **Step 5: Run maintain-plan test**

Expected:

```text
OK
```

- [ ] **Step 6: Add log anchor gap test**

Create an incident trace with no matched code log link. Assert maintain-plan returns `review_log_anchor_gap`.

- [ ] **Step 7: Update maintain and reflect skill docs**

Document:

- reviewing trace actions
- using `incident_trace:<id>` in reflection `source_cases`
- not promoting traces automatically

- [ ] **Step 8: Commit**

```bash
git add tools/agent_memory_runtime/incident_trace_governance.py tools/agent_memory_runtime/governance.py skills/agent-memory-maintain/SKILL.md skills/agent-memory-reflect/SKILL.md tests/test_incident_trace.py
git commit -m "feat: govern incident traces in maintain-plan"
```

## Task 6: Vault, Docs, And Verification

**Files:**

- Modify: `tools/agent_memory_runtime/vault.py`
- Modify: `docs/code-log-statement-network.md`
- Modify: `docs/usage-guide.md`
- Modify: `gitlog.md`
- Test: `tests/test_incident_trace.py`

- [ ] **Step 1: Write failing vault export test**

Assert `vault-export` writes:

```text
Codebase Wiki/incident-traces.md
Governance/Incident Trace Review.md
```

- [ ] **Step 2: Run vault export test and verify it fails**

Expected:

```text
incident trace vault files missing
```

- [ ] **Step 3: Add vault export pages**

In `vault.py`, keep changes thin:

- delegate content generation to small helper functions if needed
- list recent traces
- list open trace review actions
- do not include raw log text beyond short `entry_log_text`

- [ ] **Step 4: Run vault export test**

Expected:

```text
OK
```

- [ ] **Step 5: Update docs**

Update:

- `docs/code-log-statement-network.md`
- `docs/usage-guide.md`
- `gitlog.md`

Include rollback notes:

```text
Remove incident trace tables, command registration, query lane, maintain actions, and docs if trace storage proves too noisy.
```

- [ ] **Step 6: Run full incident trace tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_incident_trace
```

Expected:

```text
OK
```

- [ ] **Step 7: Run existing runtime tests**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m unittest tests.test_agent_memory.AgentMemoryRuntimeTests
```

Expected:

```text
OK
```

- [ ] **Step 8: Run compile and whitespace checks**

Run:

```bash
PYTHONPYCACHEPREFIX=.pycache python3 -m py_compile tools/agent_memory.py tools/agent_memory_runtime/*.py
git diff --check
```

Expected:

```text
both commands exit 0
```

- [ ] **Step 9: Verify file size rule**

Run:

```bash
wc -l tools/agent_memory_runtime/incident_trace*.py tests/test_incident_trace.py
```

Expected:

```text
each listed file is <= 500 lines
```

- [ ] **Step 10: Commit**

```bash
git add tools/agent_memory_runtime/vault.py docs/code-log-statement-network.md docs/usage-guide.md gitlog.md tests/test_incident_trace.py
git commit -m "docs: document ArkTS incident trace workflow"
```

## Final Acceptance Checklist

- [ ] Raw user log files are not persisted.
- [ ] `incident-trace` accepts symptom plus bounded log text or log file.
- [ ] ArkTS scene classification covers route, resource, network, permission, ability, state, and unknown.
- [ ] Trace rows link back to code logs, files, symbols, or memory edges when anchors exist.
- [ ] `context/search` include bounded `incident_trace_matches`.
- [ ] `maintain-plan` proposes trace review actions without mutating traces.
- [ ] `reflect` can cite `incident_trace:<id>` through existing `source_cases`.
- [ ] New incident trace modules and tests are each under 500 lines.
- [ ] Existing large runtime files only contain adapter-level changes.
- [ ] Full runtime tests, incident tests, py_compile, and diff check pass.

## Future Extensions Outside This Plan

- Add a golden evaluation suite for ArkTS incident diagnosis.
- Add p95 query latency benchmark with 10k, 100k, and 500k trace/code-memory rows.
- Add current projection for resolved incident traces once trace quality is proven.
- Add optional Drain-style event templates only after trace matching shows repeated noisy log patterns.
- Add automatic skill candidate promotion only after evaluator metrics exist.
