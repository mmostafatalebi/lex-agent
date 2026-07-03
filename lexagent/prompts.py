"""Prompt builders for the analysis LLM calls.

Each function takes typed arguments and returns a composed prompt string. Prompts
are built as f-strings here rather than stored as raw templates so the shape of
every model input is visible next to the data it consumes.
"""

from lexagent.models import Clause, ClauseType, DocumentType
from lexagent.retrieve import RetrievedExample

_DOCUMENT_TYPE_VALUES = ", ".join(dt.value for dt in DocumentType)
_CLAUSE_TYPE_VALUES = ", ".join(ct.value for ct in ClauseType)


def classify_document_prompt(text_head: str) -> str:
    """Prompt for classifying a contract document into MSA / NDA / SOW / other."""
    return (
        "You are a contracts analyst. Classify the following contract into exactly "
        "one document type.\n\n"
        f"Allowed document_type values (use one exactly): {_DOCUMENT_TYPE_VALUES}.\n\n"
        "Base the decision on the structure and language of the text. Return the "
        "document_type and a one- or two-sentence reasoning.\n\n"
        "--- BEGIN CONTRACT TEXT ---\n"
        f"{text_head}\n"
        "--- END CONTRACT TEXT ---"
    )


def classify_clauses_prompt(document_type: DocumentType, clauses: list[Clause]) -> str:
    """Prompt for classifying a batch of clauses into ClauseType categories."""
    lines = [
        "You are a contracts analyst. Classify each clause below into exactly one "
        "clause type.\n",
        f"The document is a {document_type.value} contract.\n",
        f"Allowed clause_type values (use one exactly): {_CLAUSE_TYPE_VALUES}.\n",
        "Return one classification per clause, echoing the clause_id exactly as "
        "given. Classify every clause. Use 'other' when no specific type fits.\n",
        "--- BEGIN CLAUSES ---",
    ]
    for clause in clauses:
        heading = f" | heading: {clause.heading}" if clause.heading else ""
        lines.append(f"[{clause.id}]{heading}\n{clause.text}\n")
    lines.append("--- END CLAUSES ---")
    return "\n".join(lines)


def _format_examples(examples: list[RetrievedExample]) -> str:
    if not examples:
        return "(none provided)"
    blocks = []
    for i, example in enumerate(examples, start=1):
        blocks.append(f"{i}. {example.text}\n   Note: {example.notes}")
    return "\n".join(blocks)


def analyze_clause_prompt(
    document_type: DocumentType,
    clause: Clause,
    canonical_examples: list[RetrievedExample],
    risky_examples: list[RetrievedExample],
) -> str:
    """Prompt for identifying risks in a single clause, grounded by taxonomy examples."""
    clause_type = clause.clause_type.value if clause.clause_type else "unknown"
    return (
        "You are a contracts analyst representing an independent contractor. Identify "
        "the risks and missing protections in the clause below that disadvantage the "
        f"contractor. The document is a {document_type.value} contract and this clause "
        f"is of type {clause_type}.\n\n"
        "For calibration, here are canonical (balanced, market-standard) examples of "
        "this clause type:\n"
        f"{_format_examples(canonical_examples)}\n\n"
        "And here are recognizably problematic examples of this clause type:\n"
        f"{_format_examples(risky_examples)}\n\n"
        "Return a list of flags. Each flag needs a risk_description, a severity of "
        "'dealbreaker', 'important', or 'minor', a verbatim_quote, and a reasoning. "
        "Only report a risk when you can support it with a direct quotation. The "
        "verbatim_quote must be an exact substring of the clause text below, character "
        "for character. Do not paraphrase, normalize punctuation, or fix typos. If the "
        "clause is balanced and carries no material risk, return an empty list.\n\n"
        "--- BEGIN CLAUSE TEXT ---\n"
        f"{clause.text}\n"
        "--- END CLAUSE TEXT ---"
    )
