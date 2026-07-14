# External Semantic Provider

The external semantic-provider protocol lets a compiler, language server, or SCIP bridge produce exact semantic evidence without becoming a dependency of Agent Memory.

## Configure

Set one explicit executable path in the Agent process environment:

```bash
export AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS=/absolute/path/to/arkts-semantic-provider
python tools/agent_memory.py learn-path --project . --path entry/src/main/ets --json
```

The value is one executable, not a shell command. Arguments, pipes, redirects, and project-local configuration are not evaluated. Put toolchain arguments in a separately reviewed wrapper executable when required.

Normal learning uses `auto` mode:

```text
configured exact provider succeeds -> persist exact batch
provider absent                    -> use built-in static adapter
provider fails validation/runtime -> report fallback and use static adapter
```

`parse_stats.semantic_index.provider_runs` reports the selected path, provider identity, toolchain, duration, accepted output bytes, and fallback reason. Compact configured-provider telemetry is retained at `runtime/semantic_provider_runs.jsonl`, capped at 200 records.

## Request

The executable runs once per language and learned scope, with the source project as cwd. It receives one JSON document on stdin:

```json
{
  "schema_version": "semantic-provider-request/v1",
  "request_id": "correlation-id",
  "semantic_schema": "semantic-index/v1",
  "language": "ArkTS",
  "project_root": "/absolute/project",
  "files": [
    {"path": "entry/src/main/ets/pages/Home.ets", "digest": "sha256"}
  ],
  "limits": {
    "timeout_seconds": 20,
    "max_output_bytes": 16777216
  }
}
```

Entities and source digests may cover only requested relative files. A relation target may use a safe project-relative path outside the current scope so it can bind to an already indexed symbol. The provider reads requested sources from cwd; source content and ASTs are not copied into the request or persisted by Agent Memory.

## Result

The executable writes exactly one JSON document to stdout:

```json
{
  "schema_version": "semantic-provider-result/v1",
  "request_id": "correlation-id",
  "provider": {
    "id": "arkts-es2panda",
    "version": "1.0.0",
    "toolchain": "OpenHarmony SDK ..."
  },
  "batch": {
    "schema_version": "semantic-index/v1",
    "adapter": {
      "id": "arkts-es2panda",
      "version": "1.0.0",
      "language": "ArkTS"
    },
    "capabilities": ["definitions", "calls", "types"],
    "source_digests": {
      "entry/src/main/ets/pages/Home.ets": "sha256"
    },
    "entities": [],
    "relations": [],
    "gaps": []
  }
}
```

Every external entity/relation must be `exact`. Symbol keys must equal the deterministic `symbol_key(language, file_path, qualified_name, signature)` identity defined by `semantic-index/v1`. Cross-scope targets may use that stable key and/or qualified-name/path hints; unknown keys remain unresolved instead of creating graph nodes.

The runtime rejects stale digests, unsafe paths, unstable keys, non-exact evidence, malformed JSON, identity mismatch, request mismatch, unsupported schema, nonzero exit, timeout, and oversized accepted output.

## Evaluation

Run the checked-in static baseline:

```bash
python tools/agent_memory.py eval-semantic --project . \
  --cases docs/eval/semantic-cases.json --mode static --json
```

Evaluate a configured exact provider and compare it with static output:

```bash
python tools/agent_memory.py eval-semantic --project . \
  --cases /path/to/provider-cases.json --mode external --json
```

The report includes expected relation recall, forbidden-edge rate, resolution rate, entity/relation/gap counts, latency, output size, and `common`, `selected_only`, and `static_only` relation counts. Differences are diagnostic; they are not automatically classified as provider errors because valid programs can contain multiple targets for the same relation.

`tests/fixtures/exact_semantic_provider.py` is a protocol test double, not an ArkTS compiler. A production es2panda, Language Server, or SCIP bridge stays outside the core runtime and must derive its exact claims from the real toolchain.
