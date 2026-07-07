// In-memory mock backend used when NEXT_PUBLIC_USE_MOCK=true, so the app runs
// locally without a live API. It mirrors the five real endpoints and walks the
// same status transitions the real graph produces.

import type {
  AnalysisStatusResponse,
  Flag,
  HumanDecision,
  Redline,
  ResultsResponse,
  UploadContractResponse,
} from "./api-types";

const CONTRACT_ID = "mock-contract-id";
const THREAD_ID = "mock-thread-id";

const CANNED_FLAGS: Flag[] = [
  {
    id: "flag_006_001",
    clause_id: "clause_006",
    risk_description: "Contractor bears unlimited, uncapped liability.",
    severity: "dealbreaker",
    verbatim_quote: "Contractor shall have unlimited liability for any and all damages",
    reasoning:
      "There is no cap on damages, so a single dispute could exceed the total contract value many times over.",
    suggested_redline: null,
  },
  {
    id: "flag_003_001",
    clause_id: "clause_003",
    risk_description: "The IP assignment sweeps in pre-existing work.",
    severity: "important",
    verbatim_quote: "including all pre-existing intellectual property owned by Contractor",
    reasoning:
      "Assigning pre-existing IP hands over assets the contractor built before this engagement.",
    suggested_redline: null,
  },
  {
    id: "flag_008_001",
    clause_id: "clause_008",
    risk_description: "The non-compete runs three years across every industry.",
    severity: "minor",
    verbatim_quote: "for a period of three (3) years following its termination",
    reasoning: "A three-year, all-industry restriction is broad enough to be hard to enforce.",
    suggested_redline: null,
  },
];

type MockThread = {
  status: AnalysisStatusResponse["status"];
  flags: Flag[];
  redlines: Redline[];
  draftingPollsRemaining: number;
};

const threads = new Map<string, MockThread>();

function redlineFor(flag: Flag, index: number): Redline {
  return {
    id: `redline_${flag.id}`,
    clause_id: flag.clause_id,
    flag_id: flag.id,
    original_text: flag.verbatim_quote,
    revised_text:
      index === 0
        ? "Contractor's total liability shall not exceed the fees paid under the applicable statement of work."
        : "Contractor assigns only the deliverables created for Client and retains all pre-existing materials.",
    justification: "Caps the exposure and keeps the contractor's prior work out of the assignment.",
  };
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const mockBackend = {
  async uploadContract(_file: File): Promise<UploadContractResponse> {
    await delay(300);
    return { contract_id: CONTRACT_ID, s3_key: `contracts/${CONTRACT_ID}.pdf` };
  },

  async startAnalysis(_contractId: string): Promise<AnalysisStatusResponse> {
    await delay(400);
    threads.set(THREAD_ID, {
      status: "awaiting_review",
      flags: CANNED_FLAGS,
      redlines: [],
      draftingPollsRemaining: 0,
    });
    return {
      thread_id: THREAD_ID,
      status: "awaiting_review",
      flags: CANNED_FLAGS,
      redlines: null,
      error: null,
    };
  },

  async getAnalysis(threadId: string): Promise<AnalysisStatusResponse> {
    const thread = threads.get(threadId);
    if (!thread) {
      return {
        thread_id: threadId,
        status: "awaiting_review",
        flags: CANNED_FLAGS,
        redlines: null,
        error: null,
      };
    }
    if (thread.status === "drafting" && thread.draftingPollsRemaining > 0) {
      thread.draftingPollsRemaining -= 1;
      if (thread.draftingPollsRemaining === 0) {
        thread.status = "complete";
      }
    }
    return {
      thread_id: threadId,
      status: thread.status,
      flags: thread.flags,
      redlines: thread.status === "complete" ? thread.redlines : null,
      error: null,
    };
  },

  async submitDecisions(
    threadId: string,
    decisions: HumanDecision[]
  ): Promise<AnalysisStatusResponse> {
    await delay(300);
    const thread = threads.get(threadId) ?? {
      status: "awaiting_review" as const,
      flags: CANNED_FLAGS,
      redlines: [],
      draftingPollsRemaining: 0,
    };
    const accepted = new Set(
      decisions.filter((d) => d.decision === "accept").map((d) => d.flag_id)
    );
    thread.redlines = CANNED_FLAGS.filter((f) => accepted.has(f.id)).map(redlineFor);
    thread.status = "drafting";
    thread.draftingPollsRemaining = 1;
    threads.set(threadId, thread);
    return {
      thread_id: threadId,
      status: "drafting",
      flags: thread.flags,
      redlines: null,
      error: null,
    };
  },

  async getResults(threadId: string): Promise<ResultsResponse> {
    const thread = threads.get(threadId);
    return {
      thread_id: threadId,
      status: "complete",
      redlines: thread?.redlines ?? [],
    };
  },
};
