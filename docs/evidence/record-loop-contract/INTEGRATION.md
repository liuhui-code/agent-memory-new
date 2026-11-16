# Integrated finite record-loop repair

The integration checkout fast-forwarded from a012737 to the independently reviewed
f7438388b3a1879358597677849a08add4f1b7d3 (tree
a4c1530f88b8a91173c1a329fc1739ac4d19e636). No other investigation branch was merged.

The coordinator reran `python -m unittest tests.test_record_loop_source
tests.test_record_loop_selection tests.test_record_loop_transaction`: 25 tests
passed. All 14 changed Python files compile, remain at or below 500 lines, and
the complete diff passes whitespace checks. These checks are additional to the
worker's 69 relevant tests and the independent reviewer's 25 tests; they are not
a full suite or an aggregate evaluation.

The unchanged original26 group is verified 3/3. A separately frozen post-hoc
comparison against clean a012737 is 1/3 with the same case, oracle and all 253
source hashes, supporting two net fail-to-pass variants for the combined
producer and terminal transaction. It does not apportion that gain to either
layer or establish a new aggregate score. The two independent bare-accumulator
requests remain failed and are not silently removed.

Stage B recall failure, Stage D protected-log failure, first implementation
errors and subsequent fixes remain in history. The accepted terminal view is
lossy in code-source selection, not an absence or unique-owner certificate.
Raw handoff and non-code compact evidence are preserved; source, identity,
protection and unchanged budget checks fall back to the original payload.
The documented repeated bounded source reads are real cost, not a performance
improvement. Source-span overlap metrics alone do not prove full original bodies.

This integration has not been published. The public branch still requires
approval for this new exact history; main is not to be changed.
