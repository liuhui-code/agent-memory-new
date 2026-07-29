# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

import re
from dataclasses import dataclass


ECMA_LANGUAGES = ("ArkTS", "JavaScript", "TypeScript")


@dataclass(frozen=True)
class LogApiModel:
    languages: tuple[str, ...]
    names: tuple[str, ...]
    levels: tuple[str, ...] = ()
    logger: str = ""
    fixed_level: str = ""
    message_argument: int = 0

    @property
    def member_call(self) -> bool:
        return bool(self.levels)

    def scan_pattern(self) -> str:
        names = "|".join(re.escape(name) for name in self.names)
        if self.member_call:
            levels = "|".join(re.escape(level) for level in self.levels)
            return rf"\b(?:{names})\.(?:{levels})\s*\("
        return rf"\b(?:{names})\s*\("

    def parse(self, statement: str) -> "LogApiCall | None":
        names = "|".join(re.escape(name) for name in self.names)
        if self.member_call:
            levels = "|".join(re.escape(level) for level in self.levels)
            pattern = rf"^\s*(?P<name>{names})\.(?P<level>{levels})\s*\((?P<args>[\s\S]*)\)\s*;?\s*$"
        else:
            pattern = rf"^\s*(?P<name>{names})\s*\((?P<args>[\s\S]*)\)\s*;?\s*$"
        match = re.match(pattern, statement)
        if match is None:
            return None
        level = match.groupdict().get("level") or self.fixed_level
        return LogApiCall(
            logger=self.logger or match.group("name"),
            level="warning" if level == "warn" else level,
            args_text=match.group("args"),
            message_argument=self.message_argument,
        )


@dataclass(frozen=True)
class LogApiCall:
    logger: str
    level: str
    args_text: str
    message_argument: int


LOG_API_MODELS = (
    LogApiModel(ECMA_LANGUAGES, ("console",), ("log", "debug", "info", "warn", "error"), "console"),
    LogApiModel(ECMA_LANGUAGES, ("logger", "Logger"), ("log", "debug", "info", "warn", "warning", "error", "exception"), "logger"),
    LogApiModel(ECMA_LANGUAGES, ("hilog", "HiLog"), ("debug", "info", "warn", "error", "fatal"), "hilog", message_argument=2),
    LogApiModel(("Python",), ("print",), logger="print", fixed_level="print"),
    LogApiModel(("Python",), ("logging", "logger"), ("debug", "info", "warning", "warn", "error", "exception"), "logger"),
    LogApiModel(("Dart",), ("print",), logger="print", fixed_level="print"),
    LogApiModel(("Dart",), ("debugPrint",), logger="debugPrint", fixed_level="debug"),
    LogApiModel(("Dart",), ("log",), logger="log", fixed_level="log"),
    LogApiModel(("Swift",), ("print",), logger="print", fixed_level="print"),
    LogApiModel(("Swift",), ("NSLog",), logger="NSLog", fixed_level="log"),
    LogApiModel(("Swift",), ("os_log",), logger="os_log", fixed_level="log"),
    LogApiModel(("Swift",), ("logger",), ("debug", "info", "warning", "error"), "logger"),
)


def models_for(language: str) -> tuple[LogApiModel, ...]:
    return tuple(model for model in LOG_API_MODELS if language in model.languages)


def direct_log_pattern(language: str) -> str:
    patterns = [model.scan_pattern() for model in models_for(language)]
    return "(?:" + "|".join(patterns) + ")" if patterns else ""


def parse_log_api_call(statement: str, language: str) -> LogApiCall | None:
    for model in models_for(language):
        parsed = model.parse(statement)
        if parsed is not None:
            return parsed
    return None
