"""Clause-boundary chunker.

Splits raw contract text into ``Clause`` objects while preserving exact
character offsets into the source text. The invariant every downstream stage
depends on is::

    raw_text[clause.char_start:clause.char_end] == clause.text

for every clause produced here.
"""

import re

from lexagent.models import Clause

SECTION_PATTERN = re.compile(
    r"^\s*(?:"
    r"(?:Article|Section|Clause)\s+\d+(?:\.\d+)*\.?\s*"
    r"|"
    r"\d+(?:\.\d+)*\.?\s+"
    r")",
    re.MULTILINE,
)

# Short joining words that stay lowercase in title-case headings.
_HEADING_STOPWORDS = frozenset(
    {"of", "and", "the", "to", "for", "a", "an", "in", "on", "or", "with", "by", "at"}
)


def chunk_into_clauses(raw_text: str) -> list[Clause]:
    """Split raw text into clauses at section boundaries.

    Preserves character offsets. Falls back to paragraph splitting if no
    numbered sections are detected.
    """
    matches = list(SECTION_PATTERN.finditer(raw_text))
    if len(matches) < 2:
        return _chunk_by_paragraph(raw_text)
    return _chunk_by_section_matches(raw_text, matches)


def _chunk_by_section_matches(raw_text: str, matches: list[re.Match[str]]) -> list[Clause]:
    """Chunk at each section-header match.

    Clause ``i`` spans from ``matches[i].start()`` to ``matches[i + 1].start()``
    (or end of text). Any non-whitespace preamble before the first match becomes
    its own leading clause with no section number.
    """
    starts = [m.start() for m in matches]
    boundaries = [*starts, len(raw_text)]

    segments: list[tuple[int, int, re.Match[str] | None]] = []
    if raw_text[: starts[0]].strip():
        segments.append((0, starts[0], None))
    for i, match in enumerate(matches):
        segments.append((starts[i], boundaries[i + 1], match))

    clauses: list[Clause] = []
    index = 1
    for seg_start, seg_end, seg_match in segments:
        clause = _build_clause(raw_text, seg_start, seg_end, seg_match, index)
        if clause is None:
            continue
        clauses.append(clause)
        index += 1
    return clauses


def _chunk_by_paragraph(raw_text: str) -> list[Clause]:
    """Split on blank lines. Each non-empty paragraph becomes a clause."""
    clauses: list[Clause] = []
    index = 1
    cursor = 0
    for block in re.split(r"\n\s*\n", raw_text):
        seg_start = raw_text.index(block, cursor)
        seg_end = seg_start + len(block)
        cursor = seg_end
        clause = _build_clause(raw_text, seg_start, seg_end, None, index)
        if clause is None:
            continue
        clauses.append(clause)
        index += 1
    return clauses


def _build_clause(
    raw_text: str,
    seg_start: int,
    seg_end: int,
    match: re.Match[str] | None,
    index: int,
) -> Clause | None:
    """Trim whitespace from a segment and build a ``Clause`` with exact offsets.

    Returns ``None`` for whitespace-only segments.
    """
    segment = raw_text[seg_start:seg_end]
    stripped = segment.strip()
    if not stripped:
        return None

    lead = len(segment) - len(segment.lstrip())
    char_start = seg_start + lead
    char_end = char_start + len(stripped)
    text = raw_text[char_start:char_end]

    section_number = _extract_section_number(match)
    heading = _extract_heading(text, section_number)

    return Clause(
        id=f"clause_{index:03d}",
        section_number=section_number,
        heading=heading,
        text=text,
        char_start=char_start,
        char_end=char_end,
    )


def _extract_section_number(match: re.Match[str] | None) -> str | None:
    """Pull a clean section label (e.g. ``"3.2"`` or ``"Article 1"``) from a match."""
    if match is None:
        return None
    label = match.group().strip().rstrip(".").strip()
    return label or None


def _extract_heading(text: str, section_number: str | None) -> str | None:
    """Return the first line of a clause if it reads like a heading.

    The section-number prefix is stripped first, so ``"3. Payment Terms"``
    yields the heading ``"Payment Terms"``.
    """
    first_line = text.split("\n", 1)[0].strip()
    if section_number and first_line.startswith(section_number):
        first_line = first_line[len(section_number) :].lstrip(". \t")
    if _looks_like_heading(first_line):
        return first_line
    return None


def _looks_like_heading(text: str) -> bool:
    """Heuristic: short, no sentence punctuation, all-caps or title-case."""
    if not text or len(text) > 80:
        return False
    if text.endswith((".", ";")):
        return False
    if text.isupper():
        return True
    words = [w for w in re.split(r"\s+", text) if w]
    significant = [w for w in words if w.lower() not in _HEADING_STOPWORDS]
    if not significant:
        return False
    return all(w[0].isupper() or not w[0].isalpha() for w in significant)
