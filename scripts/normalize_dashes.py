#!/usr/bin/env python3
"""Normalize long dashes to simple hyphens (-) in tracked text files."""

from __future__ import annotations

import subprocess
from pathlib import Path

LONG_DASHES = ("\u2013", "\u2014")
HYPHEN = "-"

# Keep this list small and explicit to avoid touching binary/generated artifacts.
TEXT_EXTENSIONS = {
    ".html",
    ".htm",
    ".md",
    ".txt",
    ".xml",
    ".csv",
    ".json",
    ".js",
    ".css",
    ".py",
    ".yml",
    ".yaml",
}


def tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    files: list[Path] = []
    for rel in result.stdout.splitlines():
        path = Path(rel)
        if path.suffix.lower() in TEXT_EXTENSIONS:
            files.append(path)
    return files


def normalize_file(path: Path) -> int:
    content = path.read_text(encoding="utf-8")
    count = sum(content.count(dash) for dash in LONG_DASHES)
    if count == 0:
        return 0

    updated = content
    for dash in LONG_DASHES:
        updated = updated.replace(dash, HYPHEN)
    path.write_text(updated, encoding="utf-8")
    return count


def main() -> int:
    total_replacements = 0
    touched_files: list[tuple[Path, int]] = []

    for path in tracked_files():
        replacements = normalize_file(path)
        if replacements:
            touched_files.append((path, replacements))
            total_replacements += replacements

    if touched_files:
        print("Updated files:")
        for file_path, replacements in touched_files:
            print(f"- {file_path} ({replacements} replacements)")
    else:
        print("No long dashes found.")

    print(f"Total replacements: {total_replacements}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
