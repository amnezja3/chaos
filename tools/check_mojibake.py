from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


SUSPICIOUS_PATTERNS = (
    "\u00c3",
    "\u00c4",
    "\u00c5",
    "\u00c2",
    "\u00e2\u20ac",
    "\ufffd",
    "\u0139",
    "\u0102",
    "\u0111\u017a",
    "\u010f\ufe38",
    "\u00e2\u0165",
    "\u00e2\u0161",
    "\u00e2\u015b",
    "\u00e2\u00ac",
    "\u00e2\u0179",
    "\u00e2\u2020",
)

TEXT_SUFFIXES = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}

DEFAULT_PATHS = (
    "run.py",
    "database.py",
    "profileManagment.py",
    "static",
    "templates",
    "scripts",
    "tests",
    "doc",
)

EXCLUDED_DIRS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "data/backups",
    "flask_session",
    "node_modules",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".sqlite3",
}


def _is_excluded(path: Path) -> bool:
    parts = set(path.as_posix().split("/"))
    if parts & EXCLUDED_DIRS:
        return True
    normalized = path.as_posix()
    return any(normalized.startswith(item + "/") for item in EXCLUDED_DIRS)


def iter_text_files(paths: Iterable[str]) -> Iterable[Path]:
    for raw_path in paths:
        path = Path(raw_path)
        if not path.exists() or _is_excluded(path):
            continue
        if path.is_file():
            if path.suffix.lower() in TEXT_SUFFIXES and path.suffix.lower() not in EXCLUDED_SUFFIXES:
                yield path
            continue
        for child in path.rglob("*"):
            if _is_excluded(child) or not child.is_file():
                continue
            suffix = child.suffix.lower()
            if suffix in TEXT_SUFFIXES and suffix not in EXCLUDED_SUFFIXES:
                yield child


def scan_file(path: Path) -> list[tuple[int, str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        return [(0, "invalid-utf8", str(exc))]
    findings: list[tuple[int, str, str]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        for pattern in SUSPICIOUS_PATTERNS:
            if pattern in line:
                findings.append((line_number, pattern.encode("unicode_escape").decode("ascii"), line.strip()))
                break
    return findings


def scan_paths(paths: Iterable[str] = DEFAULT_PATHS) -> list[tuple[str, int, str, str]]:
    findings: list[tuple[str, int, str, str]] = []
    for path in iter_text_files(paths):
        for line_number, pattern, line in scan_file(path):
            findings.append((path.as_posix(), line_number, pattern, line))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Detect common UTF-8 mojibake in CHAOS text files.")
    parser.add_argument("paths", nargs="*", default=list(DEFAULT_PATHS))
    args = parser.parse_args()
    findings = scan_paths(args.paths)
    if not findings:
        print("No mojibake patterns found.")
        return 0
    for path, line_number, pattern, line in findings:
        print(f"{path}:{line_number}: {pattern}: {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
