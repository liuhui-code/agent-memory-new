# Final clean-tree focused regression result

Accepted on commit `d505eb1fb1864aaa04f084efb6b7162c4a0fb8bc` (tree `96068ed6d8a346ac579d71e7709da47fc521d618`). The one fixed run completed with exit code 0: 71 control workers plus one coordinator.

- Private identity/tamper controls: 14 passed.
- Integrated controls: 10 passed. The original `over-output-budget` harness failure is retained and excluded, not retroactively passed.
- Late-fallback stages: 3 passed, including actual saved DB effects, duplicate-ID twins and sidefiles.
- Primitive group: 42 passed (28 dispatcher, 13 primitive boundary, 1 reader).
- Resource group: 1 unittest method passed, containing 51 fixed subcontrols.
- Budget V2: 1 shared-terminal-transaction control passed; this is not outer end-to-end budget configuration.

The 121 aggregate assertion obligations are not 121 unittest tests or independent defects. All 432 runtime file hashes and fixed input/runner hashes remained equal before and after the coordinator and every worker. No isolated bytecode cache was created, and the tested Git working tree remained clean. Independent read-only review confirmed exact planned worker order, all saved results, selected persistent effects and byte preservation without rerunning any product or control.

The portable wrapper adds no production-function replacements. Original frozen observation and failure-injection mechanisms remain unchanged. This focused component run does not replay historical BEFORE/AFTER, replace their separately qualified evidence, close original case 13, establish a full-suite pass, or establish CI/remote publication.
