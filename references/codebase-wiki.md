# Lightweight Codebase Wiki

The MVP codebase wiki is a small searchable index, not a full code intelligence system.

It stores:

- file path
- language
- simple file summary
- lightweight symbols

Supported extraction:

- Python: `def`, `class`
- TypeScript/JavaScript: `function`, `class`, `const name =`
- ArkTS: `.ets`, `struct` components, `class`, `function`, component lifecycle/build methods, `router.*` targets, `$r(...)` resources
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
