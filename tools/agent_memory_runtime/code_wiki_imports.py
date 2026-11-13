# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
import os
from dataclasses import replace
from pathlib import Path

from .models import Project
from .ecma_import_lexical import admitted_module_specs
from .learning_coverage import record_skip, source_skip_reason
from .code_wiki_extractors import extract_arkts_reference_symbols, language_for, should_skip_dir

def resolve_learning_source(project: Project, raw_source: str | None) -> Path:
    source = Path(raw_source).expanduser() if raw_source else project.root
    if not source.is_absolute():
        source = project.root / source
    source = source.resolve()
    if not source.exists() or not source.is_dir():
        raise SystemExit(f"source must be a directory: {source}")
    return source



def project_for_learning_source(project: Project, raw_source: str | None) -> Project:
    source = resolve_learning_source(project, raw_source)
    return replace(project, root=source, project_name=source.name)



def resolve_target(project: Project, raw_path: str) -> Path:
    target = Path(raw_path).expanduser()
    if not target.is_absolute():
        target = project.root / target
    target = target.resolve()
    try:
        target.relative_to(project.root)
    except ValueError:
        raise SystemExit(f"path must be inside project: {target}")
    return target



def collect_project_files(
    project: Project, skipped_by_reason: dict[str, int] | None = None,
) -> list[Path]:
    return collect_path_files(project, project.root, skipped_by_reason)



def collect_path_files(
    project: Project, target: Path, skipped_by_reason: dict[str, int] | None = None,
) -> list[Path]:
    if not target.exists():
        raise SystemExit(f"path does not exist: {target}")
    if target.is_file():
        reason = source_skip_reason(project, target)
        if reason:
            record_skip(skipped_by_reason, reason)
            return []
        return [target]
    files_to_index: list[Path] = []

    def on_walk_error(_error: OSError) -> None:
        record_skip(skipped_by_reason, "unreadable_directory")

    for root, dirs, files in os.walk(target, onerror=on_walk_error):
        root_path = Path(root)
        if should_skip_dir(root_path.relative_to(project.root)):
            record_skip(skipped_by_reason, "ignored_directory")
            dirs[:] = []
            continue
        retained_dirs = []
        for name in dirs:
            directory = root_path / name
            if should_skip_dir(directory.relative_to(project.root)):
                record_skip(skipped_by_reason, "ignored_directory")
            elif directory.is_symlink():
                # os.walk does not follow directory links; make that omission visible.
                record_skip(skipped_by_reason, "symlink_directory")
            else:
                retained_dirs.append(name)
        dirs[:] = retained_dirs
        for filename in files:
            path = root_path / filename
            reason = source_skip_reason(project, path)
            if reason:
                record_skip(skipped_by_reason, reason)
            else:
                files_to_index.append(path)
    return files_to_index



def collect_entry_related_files(
    project: Project, entry: Path, depth: int,
    skipped_by_reason: dict[str, int] | None = None,
) -> list[Path]:
    seen: set[Path] = set()
    selected: set[Path] = set()
    frontier: list[tuple[Path, int]] = [(entry.resolve(), 0)]
    while frontier:
        current, current_depth = frontier.pop(0)
        if current in seen:
            continue
        seen.add(current)
        reason = source_skip_reason(project, current)
        if reason:
            record_skip(skipped_by_reason, reason)
            continue
        selected.add(current)
        if current_depth >= depth:
            continue
        for imported in resolve_project_imports(project, current):
            if imported not in seen:
                frontier.append((imported, current_depth + 1))
    return sorted(selected)



def resolve_project_imports(project: Project, path: Path) -> list[Path]:
    language = language_for(path)
    if not language:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    candidates: list[Path] = []
    if language == "Python":
        candidates.extend(resolve_python_imports(project, path, text))
    elif language in {"TypeScript", "JavaScript"}:
        candidates.extend(resolve_js_imports(project, path, text))
    elif language == "ArkTS":
        candidates.extend(resolve_js_imports(project, path, text, [".ets", ".ts", ".js"]))
        candidates.extend(resolve_arkts_router_targets(project, path, text))
    elif language == "Dart":
        candidates.extend(resolve_quoted_relative_imports(project, path, text, [".dart"]))
    elif language == "Markdown":
        candidates.extend(resolve_markdown_links(project, path, text))
    return [candidate for candidate in candidates if candidate.exists() and language_for(candidate)]



def resolve_python_imports(project: Project, path: Path, text: str) -> list[Path]:
    candidates: list[Path] = []
    for line in text.splitlines():
        line = line.strip()
        rel_match = re.match(r"from\s+(\.+[\w\.]*)\s+import\s+([\w,\s*]+)", line)
        if rel_match:
            module = rel_match.group(1)
            names = [name.strip() for name in rel_match.group(2).split(",") if name.strip() and name.strip() != "*"]
            candidates.extend(resolve_python_module(project, path, module))
            for name in names:
                candidates.extend(resolve_python_module(project, path, f"{module}.{name}"))
            continue
        abs_match = re.match(r"(?:from|import)\s+([A-Za-z_][\w\.]*)", line)
        if abs_match:
            candidates.extend(resolve_python_module(project, path, abs_match.group(1)))
    return candidates



def resolve_python_module(project: Project, path: Path, module: str) -> list[Path]:
    base: Path
    parts: list[str]
    if module.startswith("."):
        dot_count = len(module) - len(module.lstrip("."))
        base = path.parent
        for _ in range(max(dot_count - 1, 0)):
            base = base.parent
        parts = [part for part in module.lstrip(".").split(".") if part]
    else:
        base = project.root
        parts = [part for part in module.split(".") if part]
    module_path = base.joinpath(*parts) if parts else base
    return existing_module_paths(module_path, [".py"])



def existing_module_paths(base: Path, extensions: list[str]) -> list[Path]:
    matches: list[Path] = []
    for ext in extensions:
        file_path = base.with_suffix(ext)
        if file_path.exists():
            matches.append(file_path.resolve())
    for ext in extensions:
        init_path = base / f"__init__{ext}"
        if init_path.exists():
            matches.append(init_path.resolve())
    return matches



def resolve_js_imports(
    project: Project,
    path: Path,
    text: str,
    extensions: list[str] | None = None,
) -> list[Path]:
    imports = admitted_module_specs(text)
    candidates: list[Path] = []
    extensions = extensions or [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
    for spec in imports:
        if spec.startswith("."):
            candidates.extend(resolve_relative_spec(path.parent / spec, extensions))
    return candidates



def resolve_arkts_router_targets(project: Project, path: Path, text: str) -> list[Path]:
    candidates: list[Path] = []
    for route, kind in extract_arkts_reference_symbols(text):
        if kind != "route":
            continue
        if route.startswith("$") or route.startswith("@"):
            continue
        if route.startswith("/"):
            route = route.lstrip("/")
        bases = [project.root, arkts_ets_root(path), path.parent]
        for base in bases:
            candidates.extend(resolve_relative_spec(base / route, [".ets"]))
    return candidates



def arkts_ets_root(path: Path) -> Path:
    for parent in [path.parent, *path.parents]:
        if parent.name == "ets":
            return parent
    return path.parent



def resolve_quoted_relative_imports(project: Project, path: Path, text: str, extensions: list[str]) -> list[Path]:
    imports = re.findall(r"import\s+['\"]([^'\"]+)['\"]", text)
    candidates: list[Path] = []
    for spec in imports:
        if spec.startswith("."):
            candidates.extend(resolve_relative_spec(path.parent / spec, extensions))
    return candidates



def resolve_relative_spec(base: Path, extensions: list[str]) -> list[Path]:
    matches: list[Path] = []
    if base.suffix and base.exists():
        matches.append(base.resolve())
    matches.extend(existing_module_paths(base, extensions))
    for ext in extensions:
        index_path = base / f"index{ext}"
        if index_path.exists():
            matches.append(index_path.resolve())
    return matches



def resolve_markdown_links(project: Project, path: Path, text: str) -> list[Path]:
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    candidates: list[Path] = []
    for link in links:
        if "://" in link or link.startswith("#"):
            continue
        target = (path.parent / link.split("#", 1)[0]).resolve()
        try:
            target.relative_to(project.root)
        except ValueError:
            continue
        if target.exists() and target.is_file():
            candidates.append(target)
    return candidates



def relative_project_path(project: Project, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(project.root))
    except ValueError:
        return str(path)
        function_name = row["function"]
        symbol_id = symbol_ids.get((row["file_path"], function_name)) if function_name else None
        if symbol_id:
            insert_memory_edge(
                conn,
                project_id,
                "code_symbol",
                symbol_id,
                "emits_log",
                "code_log_statement",
                row["id"],
                evidence,
                0.8,
                ts,
            )
