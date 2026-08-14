#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""Scan a proposed write for credential-shaped content before it is shown or run.

The write gate states each operation's target, command, and preview to the user.
Any of those can carry a token that was pasted, interpolated from an environment
variable, or returned by a tool. This scanner is the automated half of the gate's
credential rule: it refuses to let a secret reach a plan preview, a log, or a
transcript.

Read JSON on stdin or from a file, or pass ``--text`` to scan a single string.
Exit status is 0 when clean and 1 when something credential-shaped is found.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

CREDENTIAL_KEYS = {
    "auth",
    "accesskey",
    "apikey",
    "apisecret",
    "apitoken",
    "authorization",
    "clientsecret",
    "cookie",
    "credential",
    "credentials",
    "encryptionkey",
    "passphrase",
    "password",
    "privatekey",
    "refreshtoken",
    "secret",
    "secretaccesskey",
    "secretkey",
    "signingkey",
    "sshkey",
    "token",
    "accesstoken",
    "webhooksecret",
}
# An authorization header is a credential wherever it appears. A bare "basic" or
# "bearer" is ordinary prose ("basic auth", "basic example") unless its operand is
# credential-shaped: long enough and carrying a digit or base64 padding.
CREDENTIAL_VALUE = re.compile(
    r"""(?ix)
    authorization \s* : \s* (?: bearer | basic | token ) \s+ \S+
  | \b (?: bearer | basic ) \s+
      (?= [A-Za-z0-9+/=._~-]* [0-9+/=] ) [A-Za-z0-9+/=._~-]{6,}
  | (?: ----- )? BEGIN \s (?: [A-Z0-9]+ \s )* PRIVATE \s KEY (?: \s BLOCK )?
    """
)
OPAQUE_CREDENTIAL_VALUE = re.compile(
    r"(?i)^(?:gh[pousr]_[A-Za-z0-9_]+|github_pat_[A-Za-z0-9_]+|glpat-[A-Za-z0-9_-]+|"
    r"xox[baprs]-[A-Za-z0-9-]+|sk-[A-Za-z0-9_-]{12,}|AKIA[A-Z0-9]{16})$"
)


def credential_key(key: Any) -> bool:
    """Report whether a field name reads as a credential holder."""
    raw = str(key)
    normalized = re.sub(r"[^a-z0-9]", "", raw.lower())
    if normalized in CREDENTIAL_KEYS:
        return True

    separated = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    segments = [part.lower() for part in re.split(r"[^A-Za-z0-9]+", separated) if part]
    joined_pairs = {"".join(pair) for pair in zip(segments, segments[1:])}
    if joined_pairs & {
        "accesstoken",
        "apikey",
        "clientsecret",
        "privatekey",
        "refreshtoken",
    }:
        return True
    if set(segments) & {
        "authorization",
        "cookie",
        "credential",
        "credentials",
        "password",
        "secret",
    }:
        return True
    return any(
        segment == "token"
        and (index + 1 == len(segments) or segments[index + 1] not in {"count", "counts", "limit"})
        for index, segment in enumerate(segments)
    )


def _redact(matched: str) -> str:
    """Name the offending text without repeating the secret itself."""
    if "private key" in matched.lower():
        return matched.strip()
    words = matched.split()
    if len(words) > 1:
        return " ".join(words[:-1] + ["<redacted>"])
    prefix = re.match(r"^[A-Za-z]+[-_]?", matched)
    return f"{prefix.group(0)}<redacted>" if prefix else "<redacted>"


def credential_error(value: Any, path: str = "") -> dict[str, str] | None:
    """Return the first credential finding in ``value``, or None when clean."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if credential_key(key) or credential_key(child_path):
                return {
                    "code": "CREDENTIAL_FIELD",
                    "message": f"{child_path} is not allowed in a mutation preview",
                }
            error = credential_error(child, child_path)
            if error:
                return error
    elif isinstance(value, list):
        for index, child in enumerate(value):
            error = credential_error(child, f"{path}[{index}]")
            if error:
                return error
    elif isinstance(value, str):
        match = CREDENTIAL_VALUE.search(value)
        opaque = OPAQUE_CREDENTIAL_VALUE.fullmatch(value)
        if match or opaque:
            offending = _redact(match.group(0) if match else value)
            return {
                "code": "CREDENTIAL_VALUE",
                "message": (f"{path or '<root>'} contains credential-shaped content: {offending}"),
            }
    return None


def scan(value: Any) -> dict[str, Any]:
    """Report whether a proposed write is free of credential-shaped content."""
    error = credential_error(value)
    return {"clean": error is None, "errors": [] if error is None else [error]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("path", nargs="?", help="JSON file to scan; omit to read stdin")
    source.add_argument("--text", help="Scan a single string instead of JSON")
    parser.add_argument("--json", action="store_true", help="Always emit JSON")
    args = parser.parse_args(argv)

    if args.text is not None:
        payload: Any = args.text
    else:
        raw = open(args.path, encoding="utf-8").read() if args.path else sys.stdin.read()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"invalid JSON: {exc}", file=sys.stderr)
            return 2

    result = scan(payload)
    if args.json or not sys.stdout.isatty():
        print(json.dumps(result, indent=2))
    elif result["clean"]:
        print("clean: no credential-shaped content found")
    else:
        for error in result["errors"]:
            print(f"{error['code']}: {error['message']}")
    return 0 if result["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
