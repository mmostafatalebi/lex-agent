"use client";

import { useMemo, useState } from "react";

import { FlagCard, type Decision } from "@/components/flag-card";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { useSubmitDecisions } from "@/lib/hooks";
import { ApiError } from "@/lib/api-client";
import type { Flag, HumanDecision } from "@/lib/api-types";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Could not submit your decisions. Please try again.";
}

export function FlagList({ threadId, flags }: { threadId: string; flags: Flag[] }) {
  const [decisions, setDecisions] = useState<Record<string, Decision>>({});
  const submit = useSubmitDecisions(threadId);

  const decidedCount = Object.keys(decisions).length;
  const allDecided = decidedCount === flags.length;
  const acceptedCount = useMemo(
    () => Object.values(decisions).filter((d) => d === "accept").length,
    [decisions]
  );

  function decide(flagId: string, decision: Decision) {
    setDecisions((prev) => ({ ...prev, [flagId]: decision }));
  }

  async function submitAll() {
    const payload: HumanDecision[] = flags.map((flag) => ({
      flag_id: flag.id,
      decision: decisions[flag.id],
      comment: null,
    }));
    try {
      await submit.mutateAsync(payload);
    } catch (error) {
      toast.error(messageFor(error));
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold tracking-tight">Review the flags</h1>
        <p className="text-sm text-muted-foreground">
          Accept or reject each flag. Redlines are drafted only for the ones you accept.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {flags.map((flag, index) => (
          <FlagCard
            key={flag.id}
            flag={flag}
            index={index}
            decision={decisions[flag.id] ?? null}
            onDecision={(decision) => decide(flag.id, decision)}
          />
        ))}
      </div>

      <div className="sticky bottom-4 flex items-center justify-between rounded-lg border border-border bg-panel/90 p-4 backdrop-blur">
        <span className="klabel">
          {decidedCount} / {flags.length} decided &middot; {acceptedCount} accepted
        </span>
        <Button
          onClick={submitAll}
          disabled={!allDecided || submit.isPending}
          data-testid="submit-decisions"
        >
          {submit.isPending ? "Submitting..." : "Submit decisions"}
        </Button>
      </div>
    </div>
  );
}
