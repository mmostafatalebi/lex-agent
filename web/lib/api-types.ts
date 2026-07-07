// TypeScript mirrors of the backend Pydantic schemas in lexagent/api/schemas.py.
// Field names match the backend exactly so responses deserialize directly.

export type Severity = "dealbreaker" | "important" | "minor";

export type Flag = {
  id: string;
  clause_id: string;
  risk_description: string;
  severity: Severity;
  verbatim_quote: string;
  reasoning: string;
  suggested_redline: string | null;
};

export type Redline = {
  id: string;
  clause_id: string;
  flag_id: string;
  original_text: string;
  revised_text: string;
  justification: string;
};

export type HumanDecision = {
  flag_id: string;
  decision: "accept" | "reject";
  comment: string | null;
};

export type AnalysisStatus = "awaiting_review" | "drafting" | "complete" | "failed";

export type UploadContractResponse = {
  contract_id: string;
  s3_key: string;
};

export type AnalysisStatusResponse = {
  thread_id: string;
  status: AnalysisStatus;
  flags: Flag[] | null;
  redlines: Redline[] | null;
  error: string | null;
};

export type ResultsResponse = {
  thread_id: string;
  status: "complete";
  redlines: Redline[];
};
