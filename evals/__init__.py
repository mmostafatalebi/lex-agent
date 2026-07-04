"""Evaluation harness for the analysis pipeline.

Runs the pipeline against hand-labelled contracts, scores retrieval,
classification, and flag detection, and writes a Markdown report. Responses are
cached on disk so runs are deterministic and cheap to repeat.
"""

from lexagent.models import ClauseType

RISK_CATEGORIES: tuple[str, ...] = (
    "unlimited_liability",
    "broad_ip_assignment",
    "one_sided_termination",
    "missing_payment_timeline",
    "overbroad_non_compete",
    "one_sided_amendment",
    "unfavorable_dispute_forum",
    "vague_scope",
    "broad_confidentiality",
    "indefinite_term",
    "other",
)

# Maps each risk category to the clause type whose taxonomy examples are the
# ground-truth relevant contexts for retrieval scoring.
CATEGORY_TO_CLAUSE_TYPE: dict[str, ClauseType] = {
    "unlimited_liability": ClauseType.LIABILITY,
    "broad_ip_assignment": ClauseType.IP_ASSIGNMENT,
    "one_sided_termination": ClauseType.TERMINATION,
    "missing_payment_timeline": ClauseType.PAYMENT_TERMS,
    "overbroad_non_compete": ClauseType.NON_COMPETE,
    "one_sided_amendment": ClauseType.OTHER,
    "unfavorable_dispute_forum": ClauseType.DISPUTE_RESOLUTION,
    "vague_scope": ClauseType.SCOPE_OF_WORK,
    "broad_confidentiality": ClauseType.CONFIDENTIALITY,
    "indefinite_term": ClauseType.TERMINATION,
    "other": ClauseType.OTHER,
}
