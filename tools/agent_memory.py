#!/usr/bin/env python3
# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77
"""Stable executable entry point for the local Agent Memory runtime."""

from __future__ import annotations

from agent_memory_runtime.runtime_entry import main


if __name__ == "__main__":
    raise SystemExit(main())
