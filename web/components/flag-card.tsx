"use client";

import { Check, ChevronDown, X } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Flag, Severity } from "@/lib/api-types";

export type Decision = "accept" | "reject";

const SEVERITY_LABEL: Record<Severity, string> = {
  dealbreaker: "Dealbreaker",
  important: "Important",
  minor: "Minor",
};

export function FlagCard({
  flag,
  index,
  decision,
  onDecision,
}: {
  flag: Flag;
  index: number;
  decision: Decision | null;
  onDecision: (decision: Decision) => void;
}) {
  const [showReasoning, setShowReasoning] = useState(false);

  return (
    <Card data-testid="flag-card">
      <CardHeader className="gap-3">
        <div className="flex items-center justify-between">
          <Badge variant={flag.severity}>{SEVERITY_LABEL[flag.severity]}</Badge>
          <span className="klabel">
            Flag {index + 1} / {flag.clause_id}
          </span>
        </div>
        <p className="text-base font-medium">{flag.risk_description}</p>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="panel-block border-l-2 border-l-amber">
          &ldquo;{flag.verbatim_quote}&rdquo;
        </div>

        <button
          type="button"
          onClick={() => setShowReasoning((v) => !v)}
          className="flex items-center gap-1 self-start text-sm text-muted-foreground hover:text-foreground"
          aria-expanded={showReasoning}
        >
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", showReasoning && "rotate-180")}
          />
          Why this matters
        </button>
        {showReasoning && <p className="text-sm text-muted-foreground">{flag.reasoning}</p>}

        <div className="flex gap-2 pt-1">
          <button
            type="button"
            data-testid="accept-flag"
            onClick={() => onDecision("accept")}
            className={cn(
              "inline-flex flex-1 items-center justify-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors",
              decision === "accept"
                ? "border-emerald bg-emerald/15 text-emerald"
                : "border-border text-muted-foreground hover:border-emerald/60 hover:text-emerald"
            )}
            aria-pressed={decision === "accept"}
          >
            <Check className="h-4 w-4" /> Accept
          </button>
          <button
            type="button"
            data-testid="reject-flag"
            onClick={() => onDecision("reject")}
            className={cn(
              "inline-flex flex-1 items-center justify-center gap-2 rounded-md border px-4 py-2 text-sm font-medium transition-colors",
              decision === "reject"
                ? "border-rose bg-rose/15 text-rose"
                : "border-border text-muted-foreground hover:border-rose/60 hover:text-rose"
            )}
            aria-pressed={decision === "reject"}
          >
            <X className="h-4 w-4" /> Reject
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
