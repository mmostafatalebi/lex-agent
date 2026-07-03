"""Ingest node: read a contract file and parse it into a Contract.

Pure and deterministic. Delegates to the PDF or DOCX parser based on the file
suffix and returns updated state with the contract populated.
"""

from pathlib import Path

from lexagent.models import GraphState
from lexagent.parse import parse_docx, parse_pdf


class IngestError(Exception):
    """Raised when a file cannot be ingested (unsupported type or parse failure)."""


def ingest(state: GraphState, path: Path) -> GraphState:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        contract = parse_pdf(path)
    elif suffix == ".docx":
        contract = parse_docx(path)
    else:
        raise IngestError(f"Unsupported file type: {path.suffix}")

    return state.model_copy(update={"contract": contract, "status": "analyzing"})
