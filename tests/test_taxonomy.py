from collections import Counter

from lexagent.models import ClauseType
from lexagent.taxonomy import TAXONOMY, TaxonomyEntry

_SUBSTANTIVE_TYPES = [ct for ct in ClauseType if ct is not ClauseType.OTHER]


def test_taxonomy_has_27_entries() -> None:
    assert len(TAXONOMY) == 27
    assert all(isinstance(entry, TaxonomyEntry) for entry in TAXONOMY)


def test_every_type_has_three_entries() -> None:
    counts = Counter(entry.clause_type for entry in TAXONOMY)
    for clause_type in _SUBSTANTIVE_TYPES:
        assert counts[clause_type] == 3
    assert counts[ClauseType.OTHER] == 0


def test_every_type_has_two_canonical_one_risky() -> None:
    for clause_type in _SUBSTANTIVE_TYPES:
        entries = [e for e in TAXONOMY if e.clause_type == clause_type]
        canonical = [e for e in entries if not e.is_risky]
        risky = [e for e in entries if e.is_risky]
        assert len(canonical) == 2
        assert len(risky) == 1


def test_all_text_fields_are_substantial() -> None:
    for entry in TAXONOMY:
        assert isinstance(entry.text, str)
        assert len(entry.text) >= 100
        assert isinstance(entry.notes, str)
        assert entry.notes.strip()
