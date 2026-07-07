import type { Page, Route } from "@playwright/test";

import type { AnalysisStatusResponse, Flag, HumanDecision, Redline } from "../lib/api-types";

export const CANNED_FLAGS: Flag[] = [
  {
    id: "flag_a",
    clause_id: "clause_006",
    risk_description: "Contractor bears unlimited liability.",
    severity: "dealbreaker",
    verbatim_quote: "unlimited liability for any and all damages",
    reasoning: "No cap on damages.",
    suggested_redline: null,
  },
  {
    id: "flag_b",
    clause_id: "clause_003",
    risk_description: "IP assignment includes pre-existing work.",
    severity: "important",
    verbatim_quote: "including all pre-existing intellectual property",
    reasoning: "Hands over prior work.",
    suggested_redline: null,
  },
  {
    id: "flag_c",
    clause_id: "clause_008",
    risk_description: "Non-compete runs three years.",
    severity: "minor",
    verbatim_quote: "for a period of three (3) years",
    reasoning: "Broad restriction.",
    suggested_redline: null,
  },
];

function redlineFor(flagId: string): Redline {
  return {
    id: `redline_${flagId}`,
    clause_id: "clause_006",
    flag_id: flagId,
    original_text: "unlimited liability for any and all damages",
    revised_text: "liability capped at fees paid",
    justification: "Caps the exposure.",
  };
}

async function fulfillJson(route: Route, status: number, body: unknown): Promise<void> {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

// Anchored to the API host so the app's own page navigations on localhost:3000
// are never intercepted; only fetch calls to the API base are mocked.
const API = "localhost:9000";
const CONTRACTS = new RegExp(`${API}/contracts$`);
const START = new RegExp(`${API}/analyses$`);
const STATUS = new RegExp(`${API}/analyses/[^/]+$`);
const DECISIONS = new RegExp(`${API}/analyses/[^/]+/decisions$`);

export async function mockUploadAndReview(
  page: Page,
  opts: { threadId?: string; flags?: Flag[] } = {}
): Promise<void> {
  const threadId = opts.threadId ?? "mock-thread-id";
  const flags = opts.flags ?? CANNED_FLAGS;

  let submitted = false;
  let redlines: Redline[] = [];

  await page.route(CONTRACTS, (route) =>
    fulfillJson(route, 200, { contract_id: "c1", s3_key: "contracts/c1.pdf" })
  );
  await page.route(START, (route) =>
    fulfillJson(route, 200, {
      thread_id: threadId,
      status: "awaiting_review",
      flags,
      redlines: null,
      error: null,
    } satisfies AnalysisStatusResponse)
  );
  await page.route(DECISIONS, async (route) => {
    const payload = route.request().postDataJSON() as { decisions: HumanDecision[] };
    const accepted = payload.decisions.filter((d) => d.decision === "accept");
    redlines = accepted.map((d) => redlineFor(d.flag_id));
    submitted = true;
    await fulfillJson(route, 200, {
      thread_id: threadId,
      status: "complete",
      flags,
      redlines,
      error: null,
    } satisfies AnalysisStatusResponse);
  });
  await page.route(STATUS, (route) =>
    fulfillJson(route, 200, {
      thread_id: threadId,
      status: submitted ? "complete" : "awaiting_review",
      flags,
      redlines: submitted ? redlines : null,
      error: null,
    } satisfies AnalysisStatusResponse)
  );
}

export async function mockStatusError(page: Page, status: number): Promise<void> {
  await page.route(STATUS, (route) => fulfillJson(route, status, { message: "boom" }));
}
