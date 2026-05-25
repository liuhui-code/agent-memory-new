#!/usr/bin/env python3
"""Install Agent Memory MVP into a local project."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
RUNTIME_SOURCE = REPO_ROOT / "tools" / "agent_memory.py"
SKILLS_SOURCE = REPO_ROOT / "skills"


def copy_file(source: Path, target: Path, force: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and source.resolve() == target.resolve():
        return
    if target.exists() and not force:
        print(f"skip existing {target}")
        return
    shutil.copy2(source, target)
    print(f"installed {target}")


def copy_skill_dir(source: Path, target: Path, force: bool) -> None:
    if target.exists():
        if not force:
            print(f"skip existing {target}")
            return
        shutil.rmtree(target)
    shutil.copytree(source, target)
    print(f"installed {target}")


def run(cmd: list[str], cwd: Path) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, cwd=str(cwd), check=True)


def install(args: argparse.Namespace) -> None:
    if sys.version_info < (3, 9):
        raise SystemExit("Python 3.9+ is required")
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        raise SystemExit(f"project path does not exist: {project}")

    runtime_target = project / "tools" / "agent_memory.py"
    copy_file(RUNTIME_SOURCE, runtime_target, args.force)

    if args.global_skills:
        skill_target_root = Path.home() / ".codex" / "skills"
    else:
        skill_target_root = project / ".agent-skills"

    if SKILLS_SOURCE.exists():
        skill_target_root.mkdir(parents=True, exist_ok=True)
        for skill_dir in sorted(SKILLS_SOURCE.iterdir()):
            if skill_dir.is_dir():
                copy_skill_dir(skill_dir, skill_target_root / skill_dir.name, args.force)

    run([sys.executable, str(runtime_target), "init", "--project", str(project)], project)
    run([sys.executable, str(runtime_target), "doctor", "--project", str(project)], project)

    print("")
    print("Agent Memory MVP installed.")
    print("")
    print("Try:")
    print(f"  python {runtime_target.relative_to(project)} update --project . --type semantic --fact \"用户偏好先做 MVP\" --source user --confidence 1.0")
    print(f"  python {runtime_target.relative_to(project)} context --project . --query \"实现本地 agent memory\" --json")
    print(f"  python {runtime_target.relative_to(project)} vault-export --project .")
    print("")
    print("Optional shell alias:")
    print(f"  alias agent-memory='python {runtime_target}'")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="install.py")
    parser.add_argument("--project", default=".")
    parser.add_argument("--local-skills", action="store_true", default=True)
    parser.add_argument("--global-skills", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    install(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
