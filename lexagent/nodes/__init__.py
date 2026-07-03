"""Analysis nodes: pure and LLM-backed steps composed by the graph."""

import unicodedata


def normalized_contains(haystack: str, needle: str) -> bool:
    """Substring check after NFKC normalization on both sides.

    Defuses smart-quote and ligature mismatches between the model's quoted text
    and the source clause, which would otherwise fail a raw substring check.
    """
    return unicodedata.normalize("NFKC", needle) in unicodedata.normalize("NFKC", haystack)
