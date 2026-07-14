# Lightweight Codebase Wiki

The codebase wiki is a small searchable index with an optional language-neutral semantic layer, not a complete code intelligence system.

It stores:

- file path
- language
- file summary with important domain signals
- lightweight symbols with short summaries
- deterministic one-hop edges between files, symbols, logs, routes, and resources

Supported extraction:

- Python: `def`, `class`
- TypeScript/JavaScript: `function`, class methods, `class`, `interface`, `const name =`
- ArkTS: `.ets`, `struct` components, `class`, `function`, component lifecycle/build methods, relative project imports, `router.*` targets, `$r(...)` resources
- HarmonyOS config: `.json5` module/app/package config, abilities, permissions, dependencies, page profiles
- Dart: `class`, `Future<`, `void`, `Widget build`
- Swift: `class`, `struct`, `func`
- Markdown: headings

Ignored directories:

- `.git/`
- `node_modules/`
- `build/`
- `dist/`
- `.dart_tool/`
- `__pycache__/`
- `.agent-memory/`

ArkTS knowledge edges:

- `code_file --imports--> code_file`
- `code_file --routes_to--> code_file`
- `code_file --uses_resource--> code_symbol`

These are query hints for Agent reasoning. They are not a complete call graph or runtime trace.

ArkTS and TypeScript files additionally pass through `semantic-index/v1`. Resolved relations include calls, state reads/writes, inheritance, callbacks, API boundaries, and await edges. Adapter provenance, source digest, source span, and evidence class stay attached to the SQLite records. Ambiguous targets are omitted and reported as gaps.
