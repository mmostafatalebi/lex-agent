from lexagent.chunk import chunk_into_clauses


def _assert_offsets(raw_text: str) -> None:
    for clause in chunk_into_clauses(raw_text):
        assert raw_text[clause.char_start : clause.char_end] == clause.text


def test_numbered_sections_split_into_two_clauses() -> None:
    raw_text = "1. Foo\nBar.\n\n2. Baz\nQux."
    clauses = chunk_into_clauses(raw_text)
    assert len(clauses) == 2
    assert clauses[0].text == "1. Foo\nBar."
    assert clauses[1].text == "2. Baz\nQux."


def test_unstructured_text_splits_by_paragraph() -> None:
    raw_text = (
        "This is the first paragraph with some prose and no numbering.\n\n"
        "This is the second paragraph, also without any section markers.\n\n"
        "And a third paragraph to be sure."
    )
    clauses = chunk_into_clauses(raw_text)
    assert len(clauses) == 3
    assert all(c.section_number is None for c in clauses)


def test_offsets_correct_for_sectioned_text() -> None:
    _assert_offsets("1. Foo\nBar.\n\n2. Baz\nQux.\n\n3. Alpha\nBeta.")


def test_offsets_correct_for_paragraph_text() -> None:
    _assert_offsets("First paragraph here.\n\nSecond paragraph here.\n\nThird one.")


def test_clause_ids_are_sequential() -> None:
    raw_text = "1. One\nA.\n\n2. Two\nB.\n\n3. Three\nC."
    clauses = chunk_into_clauses(raw_text)
    assert [c.id for c in clauses] == ["clause_001", "clause_002", "clause_003"]


def test_section_numbers_extracted() -> None:
    raw_text = "1. Alpha\nText.\n\n2.1 Beta\nMore.\n\nArticle 3 Gamma\nEnd."
    clauses = chunk_into_clauses(raw_text)
    numbers = [c.section_number for c in clauses]
    assert numbers[0] == "1"
    assert numbers[1] == "2.1"
    assert numbers[2] == "Article 3"


def test_paragraph_clauses_have_no_section_number() -> None:
    clauses = chunk_into_clauses("Just one block of prose without structure at all here.")
    assert len(clauses) == 1
    assert clauses[0].section_number is None


def test_heading_extracted_from_titlecase_first_line() -> None:
    raw_text = "1. Payment Terms\nClient shall pay all invoices.\n\n2. Scope of Work\nDo the work."
    clauses = chunk_into_clauses(raw_text)
    assert clauses[0].heading == "Payment Terms"
    assert clauses[1].heading == "Scope of Work"
