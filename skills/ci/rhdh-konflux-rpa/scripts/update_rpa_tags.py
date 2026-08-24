#!/usr/bin/env python3
"""Update RHDH patch versions in release-data RPA ``tags`` values."""

# SPDX-License-Identifier: EPL-2.0

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

TAGS_KEY = re.compile(r"^(?P<indent> *)tags[ ]*:(?P<rest>.*)$")
LIST_ITEM = re.compile(r"^(?P<prefix> *-[ ]*)(?P<rest>.*)$")
MAPPING_KEY = re.compile(r"^(?P<indent> *)(?P<key>[A-Za-z0-9_.-]+)[ ]*:(?P<rest>.*)$")
BLOCK_SCALAR = re.compile(r"^[|>][0-9+-]*(?:[ \t]+#.*)?$")
RPA_RELATIVE_DIR = Path("config/stone-prod-p02.hjvn.p1/product/ReleasePlanAdmission/rhdh")
EXPECTED_REMOTES = frozenset(
    {
        "https://gitlab.cee.redhat.com/releng/konflux-release-data",
        "git@gitlab.cee.redhat.com:releng/konflux-release-data",
        "ssh://git@gitlab.cee.redhat.com/releng/konflux-release-data",
    }
)


@dataclass(frozen=True)
class Edit:
    text: str
    count: int
    old_versions: frozenset[str]


class UnsupportedYaml(ValueError):
    """Raised when safe line-oriented editing cannot represent a tags value."""


def _candidate(value: str, stream: str) -> Optional[tuple[str, str]]:
    match = re.fullmatch(rf"({re.escape(stream)}\.[0-9]+)(--.+)?", value)
    if not match:
        return None
    return match.group(1), match.group(2) or ""


def _quoted_end(fragment: str, start: int, quote: str) -> Optional[int]:
    index = start + 1
    escaped = False
    while index < len(fragment):
        char = fragment[index]
        if quote == "'" and char == "'":
            if index + 1 < len(fragment) and fragment[index + 1] == "'":
                index += 2
                continue
            return index
        if quote == '"' and char == "\\" and not escaped:
            escaped = True
            index += 1
            continue
        if char == quote and not escaped:
            return index
        escaped = False
        index += 1
    return None


def _scalar_span(fragment: str) -> Optional[tuple[int, int]]:
    start = len(fragment) - len(fragment.lstrip(" "))
    if start == len(fragment) or fragment[start] == "#":
        return None
    quote = fragment[start] if fragment[start] in "\"'" else ""
    if quote:
        end = _quoted_end(fragment, start, quote)
        return (start + 1, end) if end is not None else None
    end = start
    while end < len(fragment) and fragment[end] not in " \t,#]\r\n":
        end += 1
    return (start, end) if end > start else None


def _replace_scalar(fragment: str, stream: str, target: str) -> Edit:
    span = _scalar_span(fragment)
    if span is None:
        return Edit(fragment, 0, frozenset())
    start, end = span
    value = fragment[start:end]
    candidate = _candidate(value, stream)
    if candidate is None:
        return Edit(fragment, 0, frozenset())
    old, suffix = candidate
    if old == target:
        return Edit(fragment, 0, frozenset())
    replacement = f"{target}{suffix}"
    return Edit(
        fragment[:start] + replacement + fragment[end:],
        1,
        frozenset({old}),
    )


def _reject_multiline_quoted_scalar(fragment: str) -> None:
    start = len(fragment) - len(fragment.lstrip(" "))
    if (
        start < len(fragment)
        and fragment[start] in "\"'"
        and _quoted_end(fragment, start, fragment[start]) is None
    ):
        raise UnsupportedYaml("multiline quoted tags values are not supported")


def _replace_inline_list(fragment: str, stream: str, target: str) -> Edit:
    start = len(fragment) - len(fragment.lstrip(" "))
    _reject_multiline_quoted_scalar(fragment)
    if start < len(fragment) and fragment[start] in "\"'":
        return _replace_scalar(fragment, stream, target)

    opening = fragment.find("[", start)
    if opening < 0:
        return _replace_scalar(fragment, stream, target)

    closing = -1
    index = opening + 1
    while index < len(fragment):
        char = fragment[index]
        if char in "\"'":
            quoted_end = _quoted_end(fragment, index, char)
            if quoted_end is None:
                raise UnsupportedYaml("unterminated quoted value under tags")
            index = quoted_end + 1
            continue
        if char == "]":
            closing = index
            break
        index += 1
    if closing < 0:
        raise UnsupportedYaml("multiline flow tags values are not supported")

    body = fragment[opening + 1 : closing]
    parts: list[str] = []
    current: list[str] = []
    index = 0
    while index < len(body):
        char = body[index]
        if char in "\"'":
            quoted_end = _quoted_end(body, index, char)
            if quoted_end is None:
                raise UnsupportedYaml("unterminated quoted value under tags")
            current.extend(body[index : quoted_end + 1])
            index = quoted_end + 1
            continue
        if char == ",":
            parts.extend(("".join(current), ","))
            current = []
        else:
            current.append(char)
        index += 1
    parts.append("".join(current))

    count = 0
    old_versions: set[str] = set()
    for index in range(0, len(parts), 2):
        edited = _replace_scalar(parts[index], stream, target)
        parts[index] = edited.text
        count += edited.count
        old_versions.update(edited.old_versions)
    rewritten = "".join(parts)
    return Edit(
        fragment[: opening + 1] + rewritten + fragment[closing:],
        count,
        frozenset(old_versions),
    )


def update_text(text: str, stream: str, target: str) -> Edit:
    output: list[str] = []
    tags_indent: Optional[int] = None
    tags_item_indent: Optional[int] = None
    annotations_indent: Optional[int] = None
    block_scalar_indent: Optional[int] = None
    count = 0
    old_versions: set[str] = set()

    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        newline = line[len(content) :]
        indent = len(content) - len(content.lstrip(" "))
        stripped = content.strip()

        if block_scalar_indent is not None:
            if not stripped or stripped.startswith("#") or indent > block_scalar_indent:
                output.append(content + newline)
                continue
            block_scalar_indent = None

        if annotations_indent is not None:
            if not stripped or stripped.startswith("#") or indent > annotations_indent:
                output.append(content + newline)
                continue
            annotations_indent = None

        if tags_indent is not None and stripped and not stripped.startswith("#"):
            item = LIST_ITEM.match(content)
            if indent < tags_indent or (indent == tags_indent and not item):
                tags_indent = None
                tags_item_indent = None
            else:
                if stripped.startswith("["):
                    raise UnsupportedYaml("multiline flow tags values are not supported")
                if tags_item_indent is None:
                    tags_item_indent = indent if item else -1
                if item and indent == tags_item_indent:
                    _reject_multiline_quoted_scalar(item.group("rest"))
                    edited = _replace_scalar(item.group("rest"), stream, target)
                    content = item.group("prefix") + edited.text
                    count += edited.count
                    old_versions.update(edited.old_versions)

        mapping = MAPPING_KEY.match(content)
        if mapping:
            visible = mapping.group("rest").strip()
            if mapping.group("key") == "annotations" and (not visible or visible.startswith("#")):
                annotations_indent = len(mapping.group("indent"))
            if BLOCK_SCALAR.fullmatch(visible):
                block_scalar_indent = len(mapping.group("indent"))

        key = TAGS_KEY.match(content)
        if key:
            rest = key.group("rest")
            visible = rest.lstrip(" ")
            if not visible or visible.startswith("#"):
                tags_indent = len(key.group("indent"))
                tags_item_indent = None
            else:
                edited = _replace_inline_list(rest, stream, target)
                content = content[: key.start("rest")] + edited.text
                count += edited.count
                old_versions.update(edited.old_versions)

        output.append(content + newline)

    return Edit("".join(output), count, frozenset(old_versions))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Update one RHDH patch stream in the four canonical konflux-release-data RPA files."
        )
    )
    parser.add_argument("version", help="target MAJOR.MINOR.PATCH version")
    parser.add_argument(
        "--repo-dir",
        type=Path,
        help=(
            "konflux-release-data root or canonical RPA directory "
            "(default: KONFLUX_RELEASE_DATA_REPO or the current directory)"
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="report changes without writing files",
    )
    mode.add_argument(
        "--local-only",
        action="store_true",
        help="write only the local working tree (the default)",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="run tox -e test after writing",
    )
    return parser


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _git_environment() -> dict[str, str]:
    """Keep ambient Git repository/config overrides from defeating ``-C``."""
    return {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}


def _git(directory: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *args],
        check=False,
        capture_output=True,
        env=_git_environment(),
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise ValueError(detail)
    return result.stdout.strip()


def _resolve_checkout(input_path: Path, stream: str) -> tuple[Path, Path, tuple[Path, ...]]:
    if not input_path.is_dir():
        raise ValueError(f"directory not found: {input_path}")
    supplied = input_path.resolve(strict=True)
    repository = Path(_git(supplied, "rev-parse", "--show-toplevel")).resolve(strict=True)
    rpa_dir = repository / RPA_RELATIVE_DIR
    if supplied not in (repository, rpa_dir):
        raise ValueError(f"use the repository root or its canonical RPA directory: {rpa_dir}")

    dashed = stream.replace(".", "-")
    paths = (
        rpa_dir / f"rhdh-{dashed}-prod.yaml",
        rpa_dir / f"rhdh-{dashed}-stage.yaml",
        rpa_dir / f"rhdh-plugin-catalog-{dashed}-prod.yaml",
        rpa_dir / f"rhdh-plugin-catalog-{dashed}-stage.yaml",
    )
    return repository, rpa_dir, paths


def _ensure_repository_identity(repository: Path) -> None:
    remote = _git(repository, "remote", "get-url", "origin").removesuffix(".git")
    if remote not in EXPECTED_REMOTES:
        raise ValueError("origin is not releng/konflux-release-data on gitlab.cee.redhat.com")


def _ensure_clean_checkout(repository: Path) -> None:
    if _git(repository, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(
            "repository has tracked or untracked changes; commit, stash, or remove them"
        )


def _validate_targets(rpa_dir: Path, paths: list[Path]) -> tuple[Path, ...]:
    directory = _absolute(rpa_dir)
    directory_stat = os.lstat(directory)
    if stat.S_ISLNK(directory_stat.st_mode) or not stat.S_ISDIR(directory_stat.st_mode):
        raise ValueError("the canonical RPA directory must be a physical directory")
    physical_directory = directory.resolve(strict=True)

    normalized = tuple(_absolute(path) for path in paths)
    if len(normalized) != 4 or len(set(normalized)) != 4:
        raise ValueError("exactly four distinct RPA files are required")
    for path in normalized:
        if path.parent != directory:
            raise ValueError(f"target is not directly inside the canonical RPA directory: {path}")
        target_stat = os.lstat(path)
        if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISREG(target_stat.st_mode):
            raise ValueError(f"target must be a physical regular file: {path}")
        if path.resolve(strict=True).parent != physical_directory:
            raise ValueError(f"physical target escapes the canonical RPA directory: {path}")
    return normalized


def _stage(path: Path, content: bytes, mode: int, suffix: str) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=suffix,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _write_atomically(
    edits: dict[Path, Edit], originals: dict[Path, bytes], modes: dict[Path, int]
) -> None:
    staged: dict[Path, Path] = {}
    backups: dict[Path, Path] = {}
    replaced: list[Path] = []
    preserve_backups: set[Path] = set()
    try:
        for path, edit in edits.items():
            staged[path] = _stage(path, edit.text.encode("utf-8"), modes[path], ".stage")
            backups[path] = _stage(path, originals[path], modes[path], ".backup")
        for path in edits:
            os.replace(staged[path], path)
            replaced.append(path)
    except BaseException as replace_error:
        preserve_backups.update(replaced)
        rollback_errors: list[tuple[Path, BaseException]] = []
        for path in reversed(replaced):
            try:
                os.replace(backups[path], path)
                preserve_backups.discard(path)
            except BaseException as rollback_error:
                rollback_errors.append((path, rollback_error))

        if isinstance(replace_error, (KeyboardInterrupt, SystemExit)):
            raise
        rollback_interrupt = next(
            (
                error
                for _, error in rollback_errors
                if isinstance(error, (KeyboardInterrupt, SystemExit))
            ),
            None,
        )
        if rollback_interrupt is not None:
            raise rollback_interrupt from replace_error
        if rollback_errors:
            detail = "; ".join(f"{path}: {error}" for path, error in rollback_errors)
            raise OSError(f"{replace_error}; rollback failed for {detail}") from replace_error
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
        for path, temporary in backups.items():
            if path not in preserve_backups:
                temporary.unlink(missing_ok=True)


def _update_files(
    rpa_dir: Path,
    paths: tuple[Path, ...],
    stream: str,
    target: str,
    *,
    write: bool,
) -> dict[str, object]:
    edits: dict[Path, Edit] = {}
    originals: dict[Path, bytes] = {}
    modes: dict[Path, int] = {}
    normalized = _validate_targets(rpa_dir, list(paths))
    for path in normalized:
        original = path.read_bytes()
        source = original.decode("utf-8")
        originals[path] = original
        modes[path] = stat.S_IMODE(os.lstat(path).st_mode)
        edits[path] = update_text(source, stream, target)

    replacement_count = sum(edit.count for edit in edits.values())
    old_versions = sorted(
        {version for edit in edits.values() for version in edit.old_versions},
        key=lambda version: tuple(int(part) for part in version.split(".")),
    )
    if replacement_count == 0:
        raise ValueError(f"no stale {stream}.PATCH tag values found")

    if write:
        _write_atomically(edits, originals, modes)

    return {
        "stream": stream,
        "target": target,
        "write": write,
        "old_versions": old_versions,
        "replacement_count": replacement_count,
        "files": {str(path): edit.count for path, edit in edits.items()},
    }


def _run_validation(repository: Path) -> None:
    tox = shutil.which("tox")
    if tox is None:
        raise ValueError("--validate requires tox on PATH")
    result = subprocess.run([tox, "-e", "test"], cwd=repository, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"tox -e test failed with exit code {result.returncode}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    match = re.fullmatch(r"([0-9]+\.[0-9]+)\.[0-9]+", args.version)
    if match is None:
        parser.error("version must be MAJOR.MINOR.PATCH (for example, 1.9.7)")
    if args.dry_run and args.validate:
        parser.error("--validate cannot be combined with --dry-run")

    stream = match.group(1)
    requested = args.repo_dir
    if requested is None:
        requested = Path(os.environ.get("KONFLUX_RELEASE_DATA_REPO", os.getcwd()))

    try:
        repository, rpa_dir, paths = _resolve_checkout(requested, stream)
        write = not args.dry_run
        if write:
            _ensure_repository_identity(repository)
            _ensure_clean_checkout(repository)
        report = _update_files(
            rpa_dir,
            paths,
            stream,
            args.version,
            write=write,
        )
        if args.validate:
            _run_validation(repository)
    except (OSError, UnicodeError, ValueError, RuntimeError) as error:
        print(json.dumps({"error": f"{type(error).__name__}: {error}"}), file=sys.stderr)
        return 2

    print(json.dumps(report, sort_keys=True))
    state = "Dry run complete; the checkout is unchanged"
    if report["write"]:
        state = "Local-only update complete; nothing was staged, committed, pushed, or opened"
    print(state, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
