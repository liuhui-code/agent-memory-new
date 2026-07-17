# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from .agent_benchmark_cases import generation_result, new_pack, write_case_pack
from .records import output
from .storage import ensure_initialized, resolve_project


BUG_WORDS = {"fix", "bug", "crash", "error", "fail", "blank", "regression", "修复", "错误", "白屏", "崩溃"}
DESIGN_WORDS = {"refactor", "design", "architecture", "extract", "重构", "设计", "架构", "拆分"}
CODE_SUFFIXES = {".ets", ".ts", ".tsx", ".js", ".json5", ".py", ".dart", ".swift"}


def eval_harvest_history_command(args: argparse.Namespace) -> None:
    project = resolve_project(args.project, args.memory_home)
    ensure_initialized(project)
    source = Path(args.source).expanduser().resolve() if args.source else project.root
    commits = read_git_history(source, int(args.scan_limit), args.since)
    cases = build_history_cases(commits, int(args.limit))
    pack = new_pack("git-history/v1", str(source), cases)
    pack["audit"] = {
        "commit_count_scanned": len(commits),
        "case_count": len(cases),
        "draft_only": True,
        "source_modified": False,
    }
    if not cases:
        raise SystemExit("no eligible code-changing history cases found")
    target = Path(args.target).expanduser()
    write_case_pack(target, pack, bool(args.force))
    output(generation_result(pack, target), args.json)


def read_git_history(root: Path, scan_limit: int, since: str | None) -> list[dict[str, Any]]:
    command = [
        "git", "log", "--no-merges", f"-n{max(1, scan_limit)}",
        "--date=iso-strict", "--pretty=format:--AGENT-CASE--%n%H%x1f%P%x1f%cI%x1f%s", "--name-only",
    ]
    if since:
        command.insert(2, f"--since={since}")
    process = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
    if process.returncode != 0:
        raise SystemExit(f"failed to read Git history: {process.stderr.strip() or 'not a Git repository'}")
    return parse_git_history(process.stdout)


def parse_git_history(text: str) -> list[dict[str, Any]]:
    commits: list[dict[str, Any]] = []
    for block in text.split("--AGENT-CASE--\n"):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or "\x1f" not in lines[0]:
            continue
        header = lines[0].split("\x1f", 3)
        if len(header) != 4:
            continue
        commit, parents, committed_at, subject = header
        files = [line for line in lines[1:] if safe_relative_path(line)]
        commits.append({
            "commit": commit,
            "parent": parents.split()[0] if parents else "",
            "committed_at": committed_at,
            "subject": subject,
            "files": files,
        })
    return commits


def build_history_cases(commits: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for commit in commits:
        code_files = [path for path in commit["files"] if Path(path).suffix.lower() in CODE_SUFFIXES]
        if not code_files or not commit["parent"]:
            continue
        subject = commit["subject"].lower()
        task_type = "design" if contains_keyword(subject, DESIGN_WORDS) else "diagnosis"
        tests = [path for path in commit["files"] if is_test_path(path)]
        implementation_files = [path for path in code_files if not is_test_path(path)] or code_files
        if not tests and not contains_keyword(subject, BUG_WORDS | DESIGN_WORDS):
            continue
        case_id = f"git-{commit['commit'][:12]}"
        cases.append({
            "id": case_id,
            "task_type": task_type,
            "review_status": "draft",
            "task": {
                "description": f"Review the behavior changed in {', '.join(implementation_files[:3])}",
                "constraints": ["Do not inspect the hidden fix revision or oracle"],
            },
            "source": {
                "before_revision": commit["parent"],
                "after_revision": commit["commit"],
                "changed_files": code_files[:30],
                "test_files": tests[:20],
            },
            "provenance": {
                "kind": "git_history",
                "fix_commit": commit["commit"],
                "commit_message": commit["subject"],
                "committed_at": commit["committed_at"],
            },
            "oracle": {
                "expected_files": implementation_files[:30],
                "forbidden_files": [],
                "root_cause_category": infer_category(commit["subject"]),
                "verification_tests": tests[:20],
            },
            "leakage_guard": {
                "hidden_fields": ["oracle", "source.after_revision", "provenance.commit_message"],
            },
        })
        if len(cases) >= max(1, limit):
            break
    return cases


def infer_category(subject: str) -> str:
    lowered = subject.lower()
    categories = (
        ("route", ("route", "router", "navigation", "nav ", "路由", "跳转")),
        ("resource", ("resource", "image", "资源", "图片")),
        ("media", ("media", "sticker", "video", "webm", "媒体", "贴纸", "视频")),
        ("ui_layout", ("layout", "spacing", "width", "breakpoint", "布局", "间距", "宽度", "断点")),
        ("database_failure", ("database", " db ", "sqlite", "rdb", "数据库")),
        ("push", ("push", "notification", "推送", "通知")),
        ("state", ("state", "session", "cache", "状态", "会话", "缓存")),
        ("async", ("async", "await", "race", "异步", "竞态")),
        ("api", ("api", "interface", "接口")),
    )
    return next((name for name, words in categories if any(word in lowered for word in words)), "code_change")


def is_test_path(path: str) -> bool:
    lowered = path.lower()
    return "test" in lowered or "spec" in lowered


def contains_keyword(text: str, keywords: set[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def safe_relative_path(value: str) -> bool:
    path = Path(value)
    return bool(value) and not path.is_absolute() and ".." not in path.parts
