"""PDF and DOCX parsers.

Both parsers produce a ``Contract`` whose ``raw_text`` preserves paragraph
structure and whose clauses carry exact character offsets into that text.
"""

import hashlib
from pathlib import Path

import pypdf
from docx import Document

from lexagent.chunk import chunk_into_clauses
from lexagent.models import Contract


class ParseError(Exception):
    """Raised when a document cannot be parsed into a usable ``Contract``."""


def parse_pdf(path: Path) -> Contract:
    """Parse a text-based PDF into a ``Contract``.

    Raises ``ParseError`` for empty files or scanned PDFs with no extractable
    text (OCR is out of scope for now).
    """
    reader = pypdf.PdfReader(str(path))
    if not reader.pages:
        raise ParseError(f"Empty PDF: {path}")

    text_parts: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text_parts.append(page_text)
    raw_text = "\n\n".join(text_parts).strip()

    if len(raw_text) < 100:
        raise ParseError("Scanned PDF, OCR not supported")

    return _build_contract(path.name, raw_text)


def parse_docx(path: Path) -> Contract:
    """Parse a DOCX file into a ``Contract``."""
    document = Document(str(path))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    raw_text = "\n\n".join(paragraphs).strip()
    if not raw_text:
        raise ParseError(f"Empty DOCX: {path}")
    return _build_contract(path.name, raw_text)


def _build_contract(filename: str, raw_text: str) -> Contract:
    """Content-address the document and attach chunked clauses."""
    contract_id = hashlib.sha256((filename + raw_text[:1000]).encode("utf-8")).hexdigest()[:16]
    clauses = chunk_into_clauses(raw_text)
    return Contract(
        id=contract_id,
        filename=filename,
        raw_text=raw_text,
        clauses=clauses,
        # document_type stays as DocumentType.OTHER; classification happens downstream.
    )
