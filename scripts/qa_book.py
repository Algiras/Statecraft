#!/usr/bin/env python3
"""Publisher QA checks for the Statecraft Quarto book."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOK_SOURCES = [ROOT / "index.qmd", *sorted((ROOT / "chapters").glob("*.md"))]
README = ROOT / "README.md"

FORBIDDEN_SOURCE_PATTERNS = {
    "manual-panel legacy markup": re.compile(r"manual-panel|manual-blocks"),
    "rendered code/pre block markup": re.compile(r"<pre|sourceCode"),
    "box-drawing ASCII diagram": re.compile(r"[┌┐└┘│]"),
    "plus-rule ASCII diagram": re.compile(r"\+[-]{6,}\+"),
    "obsolete How to Use This Edition section": re.compile(r"How to Use This Edition|how-to-read"),
}

STALE_PUBLISHING_COPY = [
    "Mermaid diagrams",
    "download buttons",
    "PDF linked from the header",
    "manual figures",
    "how to use this edition",
]

IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def line_number(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def add_issue(issues: list[str], path: Path, message: str, line: int | None = None) -> None:
    rel = path.relative_to(ROOT)
    location = f"{rel}:{line}" if line is not None else str(rel)
    issues.append(f"{location}: {message}")


def check_forbidden_patterns(path: Path, text: str, issues: list[str]) -> None:
    if path.name != "index.qmd":
        for match in re.finditer(r"^```", text, re.MULTILINE):
            add_issue(issues, path, "fenced code block in chapter source", line_number(text, match.start()))

    for label, pattern in FORBIDDEN_SOURCE_PATTERNS.items():
        for match in pattern.finditer(text):
            add_issue(issues, path, label, line_number(text, match.start()))


def check_images(path: Path, text: str, issues: list[str]) -> None:
    for match in IMAGE_PATTERN.finditer(text):
        alt, target = match.groups()
        line = line_number(text, match.start())
        if not alt.strip():
            add_issue(issues, path, "image is missing useful alt text", line)
        if target.startswith(("http://", "https://")):
            continue
        image_path = (path.parent / target.split("#", 1)[0]).resolve()
        try:
            image_path.relative_to(ROOT)
        except ValueError:
            add_issue(issues, path, f"image target escapes repository: {target}", line)
            continue
        if not image_path.exists():
            add_issue(issues, path, f"image target is missing: {target}", line)


def check_readme(text: str, issues: list[str]) -> None:
    lowered = text.lower()
    for phrase in STALE_PUBLISHING_COPY:
        if phrase.lower() in lowered:
            index = lowered.index(phrase.lower())
            add_issue(issues, README, f"stale publishing copy: {phrase}", line_number(text, index))
    if "https://buymeacoffee.com/algiras" not in text:
        add_issue(issues, README, "support link is missing")


def main() -> int:
    issues: list[str] = []

    for path in BOOK_SOURCES:
        text = path.read_text(encoding="utf-8")
        check_forbidden_patterns(path, text, issues)
        check_images(path, text, issues)

    readme_text = README.read_text(encoding="utf-8")
    check_readme(readme_text, issues)

    if issues:
        print("Book QA failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Book QA passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
