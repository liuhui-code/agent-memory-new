# Before observer setup correction

The first raw context subprocess failed before the runner recorded any completed
public case. before-run.txt retains the failed command. The observer captured the
graph `matched` dictionary, whose keys are typed endpoint tuples; ordinary JSON
serialization does not accept tuple keys. The observer now encodes those keys as
JSON array strings recursively, preserving endpoint type/id and values. Runtime,
source, queries, expectations and selected trace functions are unchanged. No
completed-case result existed to rerun selectively. The corrected attempt uses
before-fixed and a fresh identically materialized workspace, leaving the failed
attempt/log untouched. This is not a product test failure or a query adjustment.
