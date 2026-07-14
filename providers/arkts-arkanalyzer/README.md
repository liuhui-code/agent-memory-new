# ArkAnalyzer Semantic Provider

Optional out-of-process ArkTS provider for Agent Memory. It builds an ArkAnalyzer `Scene`, runs type inference, and emits only analyzer-resolved entities and relations through `semantic-provider-result/v1`.

```bash
cd providers/arkts-arkanalyzer
pnpm install
chmod +x provider.mjs
export AGENT_MEMORY_SEMANTIC_PROVIDER_ARKTS="$PWD/provider.mjs"
python ../../tools/agent_memory.py learn-path --project /path/to/ohos-project --path entry/src/main/ets --json
```

The package is optional. HarmonyOS SDK resolution is delegated to the target project's ArkAnalyzer configuration; projects that import SDK declarations must make that SDK available to ArkAnalyzer. Missing dependencies, incompatible analyzer APIs, stale source digests, and analysis failures return a nonzero exit; the core runtime records the failure and uses its static adapter.

Run the checked-in exact capability pack before routine use:

```bash
python ../../tools/agent_memory.py eval-semantic --project ../.. \
  --cases ../../docs/eval/arkts-arkanalyzer-cases.json --mode external --json
```
