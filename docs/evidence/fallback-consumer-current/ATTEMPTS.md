# Execution correction

First execution followed freeze ea3de4e plus runner list addition. Init, learn,
raw context, compact context and code-symbol list executed. The final list used
invalid `--type code-edge` instead of `memory-edge`, exiting 2. Its exception
prevented public.json from being written; stdout of successful commands was not
checkpointed. Attempt1 traces are preserved unchanged. This was a runner error,
not a runtime defect or a failed oracle.

Parent explicitly approved one replay solely to recover lost output. Runner now
checkpoints each successful stdout and uses valid memory-edge. Sources, query,
oracle, budget and production are unchanged. There are TWO raw/compact executions,
not one. No query or source was tuned from first results. Compare shared trace
fields; numeric project/record generation metadata may differ on a fresh index.
