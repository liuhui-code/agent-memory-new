# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
MAX_LINES = 500
SCAN_ROOTS = ("install.py", "tools", "tests")
SKIP_PARTS = {".git", ".pycache", ".agent-memory"}


def iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root_name in SCAN_ROOTS:
        root = REPO_ROOT / root_name
        if root.is_file() and root.suffix == ".py":
            files.append(root)
            continue
        if root.is_dir():
            files.extend(
                path
                for path in root.rglob("*.py")
                if not (set(path.relative_to(REPO_ROOT).parts) & SKIP_PARTS)
            )
    return sorted(set(files))


def count_lines(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def main() -> int:
    violations = [
        (count_lines(path), path.relative_to(REPO_ROOT))
        for path in iter_python_files()
        if count_lines(path) > MAX_LINES
    ]
    if not violations:
        print(f"OK: all Python files are <= {MAX_LINES} lines")
        return 0
    print(f"Python files over {MAX_LINES} lines:")
    for line_count, path in sorted(violations, reverse=True):
        print(f"{line_count:5d} {path}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
