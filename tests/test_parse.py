from pathlib import Path

import pytest

from lexagent.models import Contract
from lexagent.parse import ParseError, parse_docx, parse_pdf


def _assert_offset_invariant(contract: Contract) -> None:
    """Every clause's recorded span must equal its stored text exactly."""
    for clause in contract.clauses:
        assert contract.raw_text[clause.char_start : clause.char_end] == clause.text
        assert 0 <= clause.char_start <= clause.char_end <= len(contract.raw_text)


def test_parse_pdf_returns_contract_with_clauses(sample_msa_pdf: Path) -> None:
    contract = parse_pdf(sample_msa_pdf)
    assert isinstance(contract, Contract)
    assert contract.filename == "sample_msa.pdf"
    assert len(contract.raw_text) > 1000
    assert len(contract.clauses) >= 6


def test_parse_docx_returns_contract_with_clauses(sample_msa_docx: Path) -> None:
    contract = parse_docx(sample_msa_docx)
    assert isinstance(contract, Contract)
    assert contract.filename == "sample_msa.docx"
    assert len(contract.raw_text) > 1000
    assert len(contract.clauses) >= 6


def test_offset_invariant_pdf(sample_msa_pdf: Path) -> None:
    _assert_offset_invariant(parse_pdf(sample_msa_pdf))


def test_offset_invariant_docx(sample_msa_docx: Path) -> None:
    _assert_offset_invariant(parse_docx(sample_msa_docx))


def test_contract_id_is_stable(sample_msa_pdf: Path) -> None:
    first = parse_pdf(sample_msa_pdf)
    second = parse_pdf(sample_msa_pdf)
    assert first.id == second.id
    assert len(first.id) == 16


def test_parse_pdf_empty_file_raises(tmp_path: Path) -> None:
    from pypdf import PdfWriter

    empty = tmp_path / "empty.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with empty.open("wb") as handle:
        writer.write(handle)

    with pytest.raises(ParseError):
        parse_pdf(empty)


def test_parse_docx_empty_file_raises(tmp_path: Path) -> None:
    from docx import Document

    empty = tmp_path / "empty.docx"
    Document().save(str(empty))

    with pytest.raises(ParseError):
        parse_docx(empty)
