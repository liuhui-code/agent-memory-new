# Project fingerprint: sha256:3b1b65c2fbef798c170b269728b2ae552a31c850253887f9d3f716e70f954c77

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .models import CODE_EXTENSIONS


@dataclass(frozen=True)
class SourceProfile:
    adapter_id: str
    language: str
    artifact_role: str


class SourceAdapter(Protocol):
    def profile(self, path: Path) -> SourceProfile | None: ...


class NamedBuildAdapter:
    names = {
        "build", "build.bazel", "cmakelists.txt", "gnumakefile", "makefile",
        "workspace", "workspace.bazel", "build.gradle", "build.gradle.kts",
        "cargo.toml", "package.json", "package.swift", "pyproject.toml",
        "pubspec.yaml",
    }
    suffixes = {".cmake", ".gradle", ".mk", ".sh"}

    def profile(self, path: Path) -> SourceProfile | None:
        if path.name.casefold() in self.names or path.suffix.casefold() in self.suffixes:
            return SourceProfile("build-artifact-static", "Build Artifact", "build")
        return None


class NativeSourceAdapter:
    suffixes = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}

    def profile(self, path: Path) -> SourceProfile | None:
        if path.suffix.casefold() in self.suffixes:
            return SourceProfile("native-source-static", "C/C++", "source")
        return None


class LegacySourceAdapter:
    def profile(self, path: Path) -> SourceProfile | None:
        language = CODE_EXTENSIONS.get(path.suffix.casefold())
        if not language:
            return None
        role = "documentation" if language == "Markdown" else "configuration" if language == "HarmonyOS Config" else "source"
        return SourceProfile("legacy-source", language, role)


SOURCE_ADAPTERS: tuple[SourceAdapter, ...] = (
    NamedBuildAdapter(),
    NativeSourceAdapter(),
    LegacySourceAdapter(),
)


def source_profile_for(path: Path) -> SourceProfile | None:
    for adapter in SOURCE_ADAPTERS:
        profile = adapter.profile(path)
        if profile is not None:
            return profile
    return None


def source_language_for(path: Path) -> str | None:
    profile = source_profile_for(path)
    return profile.language if profile else None
