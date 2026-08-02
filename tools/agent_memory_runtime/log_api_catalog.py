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
    LogApiModel(("C/C++",), ("LOG_DEBUG", "HILOG_DEBUG"), logger="native", fixed_level="debug"),
    LogApiModel(("C/C++",), ("LOG_INFO", "HILOG_INFO"), logger="native", fixed_level="info"),
    LogApiModel(("C/C++",), ("LOG_WARN", "HILOG_WARN"), logger="native", fixed_level="warning"),
    LogApiModel(("C/C++",), ("LOG_ERROR", "HILOG_ERROR"), logger="native", fixed_level="error"),
    LogApiModel(("C/C++",), ("LOG_FATAL", "HILOG_FATAL"), logger="native", fixed_level="fatal"),
    LogApiModel(("C/C++",), ("printf",), logger="stdio", fixed_level="info"),
    LogApiModel(("C/C++",), ("fprintf",), logger="stdio", fixed_level="error", message_argument=1),
    LogApiModel(("C/C++",), ("OH_LOG_Print",), logger="hilog", fixed_level="log", message_argument=4),
)

NAMED_IMPORT_RE = re.compile(
    r"\bimport\s*\{(?P<bindings>[^}]*)\}\s*from\s*['\"](?P<module>[^'\"]+)['\"]",
    re.DOTALL,
)
DEFAULT_IMPORT_RE = re.compile(
    r"\bimport\s+(?P<local>[A-Za-z_$][\w$]*)\s+from\s*['\"](?P<module>[^'\"]+)['\"]"
)


def models_for(language: str) -> tuple[LogApiModel, ...]:
    return tuple(model for model in LOG_API_MODELS if language in model.languages)


def log_receiver_bindings(source: str, language: str) -> dict[str, str]:
    if language not in ECMA_LANGUAGES:
        return {}
    canonical = {
        name: name
        for model in models_for(language)
        if model.member_call
        for name in model.names
    }
    result: dict[str, str] = {}
    for match in NAMED_IMPORT_RE.finditer(source):
        for raw_binding in match.group("bindings").split(","):
            parts = re.split(r"\s+as\s+", raw_binding.strip())
            original = parts[0].removeprefix("type ").strip()
            local = parts[-1].strip()
            if original in canonical and local and local != original:
                result[local] = canonical[original]
    for match in DEFAULT_IMPORT_RE.finditer(source):
        module = match.group("module").casefold()
        if "hilog" in module:
            result[match.group("local")] = "hilog"
    return result


def direct_log_pattern(
    language: str,
    receiver_bindings: dict[str, str] | None = None,
) -> str:
    models = models_for(language)
    patterns = [model.scan_pattern() for model in models]
    by_name = {name: model for model in models if model.member_call for name in model.names}
    for local, canonical in (receiver_bindings or {}).items():
        model = by_name.get(canonical)
        if model is None:
            continue
        levels = "|".join(re.escape(level) for level in model.levels)
        patterns.append(rf"\b{re.escape(local)}\.(?:{levels})\s*\(")
    return "(?:" + "|".join(patterns) + ")" if patterns else ""


def parse_log_api_call(
    statement: str,
    language: str,
    receiver_bindings: dict[str, str] | None = None,
) -> LogApiCall | None:
    for model in models_for(language):
        parsed = model.parse(statement)
        if parsed is not None:
            return parsed
    receiver = re.match(r"^\s*([A-Za-z_$][\w$]*)\.", statement)
    canonical = (receiver_bindings or {}).get(receiver.group(1)) if receiver else None
    if canonical:
        normalized = re.sub(
            rf"^(\s*){re.escape(receiver.group(1))}\.",
            rf"\1{canonical}.",
            statement,
            count=1,
        )
        for model in models_for(language):
            parsed = model.parse(normalized)
            if parsed is not None:
                return parsed
    return None
