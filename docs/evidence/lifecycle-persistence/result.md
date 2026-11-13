# Lifecycle persistence negative reproduction result

Fixed base 43921fc existing scenario remains 1/3. Independent BufferSession
combines hook/read/state/write, competing with isolated writer and setter. All
three fixed public queries pass. A second preregistered split-owner file supplies
hook, writer and state in distinct classes; the same three queries still pass.
No production changes justified for this class; do not copy whole-file combined
lifecyclesync onto a single unrelated callable. The first split-probe runner had
a sed replacement typo and failed before CLI execution; corrected runner produced
the preserved first public observations.
