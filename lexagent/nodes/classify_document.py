"""Document classification node: one Bedrock call over the document head."""

from pydantic import BaseModel

from lexagent.bedrock import BedrockClient
from lexagent.models import DocumentType, GraphState
from lexagent.prompts import classify_document_prompt

_TEXT_HEAD_CHARS = 3000


class DocumentClassification(BaseModel):
    document_type: DocumentType
    reasoning: str


def classify_document(state: GraphState, bedrock: BedrockClient) -> GraphState:
    if state.contract is None:
        raise ValueError("classify_document requires an ingested contract")

    prompt = classify_document_prompt(state.contract.raw_text[:_TEXT_HEAD_CHARS])
    result, usage = bedrock.complete_json(prompt, DocumentClassification)

    updated_contract = state.contract.model_copy(
        update={"document_type": result.document_type}
    )
    return state.model_copy(
        update={
            "contract": updated_contract,
            "total_cost_usd": state.total_cost_usd + usage.total_cost_usd,
        }
    )
