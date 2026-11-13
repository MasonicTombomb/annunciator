#!/usr/bin/env python3
"""Examine documentation text against rules of ASD-STE100 Issue 9.

The tool examines reStructuredText files and, optionally, the documentation
text in Python source files. It reports these findings:

* ``LEN-PROC``: a procedural sentence (a numbered step) of more than 20 words,
* ``LEN-DESC``: a descriptive sentence of more than 25 words,
* ``PARA``: a paragraph of more than 6 sentences,
* ``WORD``: a word from the built-in list of words that are not approved,
* ``CONTRACTION``: a contraction, for example "don't".

The tool does not contain the STE dictionary. It cannot examine the meaning
of a word or the voice of a sentence. A person must examine these items.

Usage::

    python tools/ste_check.py docs
    python tools/ste_check.py docs --python src/annunciator

The exit status is 0 if the tool has no findings, and 1 if it has findings.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Tuple

MAX_PROCEDURAL = 20
MAX_DESCRIPTIVE = 25
MAX_SENTENCES = 6

#: Words that are not approved, with an approved alternative.
NOT_APPROVED: Dict[str, str] = {
    "additional": "more", "allow": "let", "allows": "lets",
    "allowed": "permitted", "although": "(write two sentences)",
    "commence": "start", "could": "can", "create": "make",
    "creates": "makes", "created": "made", "currently": "now",
    "determine": "find", "disable": "set to off", "easily": "(remove)",
    "enable": "let", "enables": "lets", "ensure": "make sure",
    "ensures": "makes sure", "execute": "do / run", "however": "but",
    "indicate": "show", "indicates": "shows", "just": "(remove)",
    "may": "can", "might": "can", "modify": "change", "multiple": "many",
    "need": "is necessary", "needs": "is necessary", "needed": "necessary",
    "obtain": "get", "perform": "do", "performs": "does",
    "prior": "before", "provide": "give / supply",
    "provides": "gives / supplies", "provided": "given / supplied",
    "require": "is necessary", "requires": "is necessary",
    "required": "necessary", "shall": "must", "should": "must",
    "simply": "(remove)", "terminate": "stop", "therefore": "thus",
    "upon": "on", "utilise": "use", "utilize": "use", "various": "different",
    "verify": "make sure", "via": "through", "which": "that",
    "whilst": "while", "within": "in", "would": "(use simple present)",
    "using": "with / that uses", "following": "that follows",
    "including": "that includes", "containing": "that contains",
}

_CONTRACTION = re.compile(
    r"\b\w+n't\b|\b\w+'(?:re|ve|ll|d)\b|\b(?:it|that|there|what|let)'s\b",
    re.IGNORECASE,
)
_SENTENCE_END = re.compile(r"(?<=[.!?:])\s+(?=[A-Z\"'(\[])")
_SKIP_BODY = (
    "code-block", "code", "sourcecode", "literalinclude", "toctree", "index",
    "automodule", "autoclass", "autofunction", "annunciator-catalogue",
    "graphviz", "only", "list-table", "figure", "image", "rubric", "glossary",
)
_PROSE_BODY = ("note", "caution", "warning", "list-table", "only", "figure",
               "glossary")


class Finding(NamedTuple):
    path: str
    line: int
    rule: str
    text: str


class Block(NamedTuple):
    line: int
    text: str
    procedural: bool
    listed: bool


def clean_inline(text: str) -> str:
    """Replace inline markup with one neutral word."""
    text = re.sub(r"``[^`]+``", "X", text)
    text = re.sub(r":[\w:-]+:`([^`<]+?)\s*<[^`>]+>`", r"\1", text)
    text = re.sub(r":[\w:-]+:`[^`]+`", "X", text)
    text = re.sub(r"`([^`<]+?)\s*<[^`>]+>`_+", r"\1", text)
    text = re.sub(r"\|[\w-]+\|", "X", text)
    text = re.sub(r"https?://\S+", "X", text)
    text = re.sub(r"\*\*?([^*]+)\*\*?", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def rst_blocks(lines: List[str]) -> Iterable[Block]:
    """Yield the prose blocks of a reStructuredText file."""
    current: List[str] = []
    start = 0
    procedural = listed = False
    skip_indent = None  # indent of a block to skip

    def flush():
        nonlocal current
        if current:
            yield Block(start, " ".join(current), procedural, listed)
        current = []

    index = 0
    total = len(lines)
    while index < total:
        raw = lines[index].rstrip("\n")
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip())
        index += 1

        if skip_indent is not None:
            if not stripped or indent > skip_indent:
                continue
            skip_indent = None

        if not stripped:
            yield from flush()
            continue
        # Section underline or overline.
        if re.fullmatch(r"([=\-~^\"'#*+])\1{2,}", stripped):
            current = []  # the line before was a title
            continue
        match = re.match(r"\.\. ([\w-]+)::", stripped)
        if match:
            yield from flush()
            if match.group(1) not in _PROSE_BODY:
                skip_indent = indent
            continue
        if stripped.startswith(".. "):  # comment or target
            yield from flush()
            continue
        if re.match(r":[\w -]+:(\s|$)", stripped):  # field or option
            yield from flush()
            continue
        item = re.match(r"(\*|-|\d+\.|#\.)\s+(.*)", stripped)
        if item:
            yield from flush()
            body = item.group(2)
            nested = re.match(r"-\s+(.*)", body)  # list-table row "* - text"
            if nested:
                body = nested.group(1)
            start = index
            procedural = bool(re.match(r"\d+\.|#\.", item.group(1)))
            listed = True
            current = [body]
        else:
            if not current:
                start = index
                procedural = False
                listed = False
            current.append(stripped)
        if stripped.endswith("::"):
            yield from flush()
            skip_indent = indent
    yield from flush()


def docstring_blocks(path: Path) -> Iterable[Block]:
    """Yield the prose blocks of the documentation text in a Python file."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            continue
        text = ast.get_docstring(node, clean=True)
        if not text:
            continue
        first = getattr(node, "lineno", 1)
        lines = text.splitlines()
        kept: List[str] = []
        in_example = False
        in_literal = False
        for number, line in enumerate(lines):
            stripped = line.strip()
            following = lines[number + 1].strip() if number + 1 < len(lines) else ""
            if in_literal:
                if stripped and not line.startswith(" "):
                    in_literal = False
                else:
                    kept.append("")
                    continue
            if stripped.startswith(">>>"):
                in_example = True
            if in_example:
                if not stripped:
                    in_example = False
                kept.append("")
                continue
            if re.fullmatch(r"-{3,}", following) or re.fullmatch(r"-{3,}", stripped):
                kept.append("")
                continue
            if stripped.startswith(".. ") or stripped.endswith("::"):
                in_literal = True
                kept.append("")
                continue
            # Parameter name lines of the NumPy style.
            if not line.startswith(" ") and re.fullmatch(
                r"[\w*.]+(\s*:\s*.+)?", stripped
            ):
                kept.append("")
                continue
            kept.append(stripped)
        for block in rst_blocks([item + "\n" for item in kept]):
            yield Block(first + block.line, block.text, False, block.listed)


def examine(path: str, block: Block) -> Iterable[Finding]:
    """Yield the findings for one prose block."""
    text = clean_inline(block.text)
    if not text or not re.search(r"[A-Za-z]{2}", text):
        return
    sentences = [part for part in _SENTENCE_END.split(text) if part.strip()]
    limit = MAX_PROCEDURAL if block.procedural else MAX_DESCRIPTIVE
    rule = "LEN-PROC" if block.procedural else "LEN-DESC"
    for sentence in sentences:
        words = [w for w in sentence.split() if re.search(r"[A-Za-z0-9]", w)]
        if len(words) > limit:
            yield Finding(path, block.line, rule, f"{len(words)} words: {sentence}")
    if not block.listed and len(sentences) > MAX_SENTENCES:
        yield Finding(
            path, block.line, "PARA", f"{len(sentences)} sentences: {text[:60]}..."
        )
    for word in re.findall(r"[A-Za-z']+", text):
        advice = NOT_APPROVED.get(word.lower())
        if advice:
            yield Finding(path, block.line, "WORD", f"'{word}' -> {advice}")
    for match in _CONTRACTION.finditer(text):
        yield Finding(path, block.line, "CONTRACTION", match.group(0))


def collect(paths: List[str], python: List[str]) -> Tuple[List[Finding], int]:
    """Examine all files. Return the findings and the number of blocks."""
    findings: List[Finding] = []
    blocks = 0
    for root in paths:
        base = Path(root)
        files = sorted(base.rglob("*.rst")) if base.is_dir() else [base]
        for file in files:
            if "_build" in file.parts:
                continue
            lines = file.read_text(encoding="utf-8").splitlines(keepends=True)
            for block in rst_blocks(lines):
                blocks += 1
                findings.extend(examine(str(file), block))
    for root in python:
        base = Path(root)
        files = sorted(base.rglob("*.py")) if base.is_dir() else [base]
        for file in files:
            for block in docstring_blocks(file):
                blocks += 1
                findings.extend(examine(str(file), block))
    return findings, blocks


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("paths", nargs="*", default=["docs"],
                        help="reStructuredText files or directories")
    parser.add_argument("--python", action="append", default=[], metavar="PATH",
                        help="Python files or directories (documentation text)")
    args = parser.parse_args(argv)
    findings, blocks = collect(args.paths, args.python)
    for item in findings:
        print(f"{item.path}:{item.line}: {item.rule}: {item.text}")
    print(f"{blocks} text blocks examined, {len(findings)} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
