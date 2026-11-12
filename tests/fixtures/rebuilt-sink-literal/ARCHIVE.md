# Frozen investigation provenance

`prepare.py.txt` and `run_once.py.txt` are exact, unmodified bytes of the
pre-execution investigation scripts. They are archived text, not runnable project
modules. The original `freeze.json` keeps their original filenames and SHA-256
values. The regression test explicitly resolves those two historical filenames
to their `.txt` archives and verifies every frozen file. This preserves the
original freeze without rewriting the scripts to add a later project header.

The initial full regression found the original `.py` copies did not satisfy the
repository-wide public fingerprint policy. That failed run remains in the
companion evidence. No runtime, source fixture, query or expectation changes
accompany this archive-format correction.
