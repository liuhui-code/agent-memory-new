#!/usr/bin/env python3
# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from examples.ollama_benchmark_runner import run_request  # noqa: E402


def main() -> int:
    request = json.load(sys.stdin)
    result = run_request(
        request,
        host=os.environ.get("AGENT_BENCHMARK_OLLAMA_HOST", "http://127.0.0.1:11434"),
        model=os.environ.get("AGENT_BENCHMARK_OLLAMA_MODEL", "qwen3-coder:30b"),
        timeout=int(os.environ.get("AGENT_BENCHMARK_OLLAMA_TIMEOUT", "300")),
    )
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
