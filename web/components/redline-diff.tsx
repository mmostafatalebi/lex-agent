"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Card, CardContent } from "@/components/ui/card";
import type { Redline } from "@/lib/api-types";

export function RedlineDiff({ redline }: { redline: Redline }) {
  const [copied, setCopied] = useState(false);

  async function copyRevised() {
    try {
      await navigator.clipboard.writeText(redline.revised_text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard can be unavailable; ignore quietly
    }
  }

  return (
    <Card data-testid="redline-diff">
      <CardContent className="flex flex-col gap-4 p-6">
        <div className="flex items-center justify-between">
          <span className="klabel">{redline.clause_id}</span>
          <button
            type="button"
            onClick={copyRevised}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            aria-label="Copy the revised clause"
          >
            {copied ? <Check className="h-4 w-4 text-emerald" /> : <Copy className="h-4 w-4" />}
            {copied ? "Copied" : "Copy revised"}
          </button>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex flex-col gap-2">
            <span className="klabel">Original</span>
            <div className="panel-block border-l-2 border-l-rose">{redline.original_text}</div>
          </div>
          <div className="flex flex-col gap-2">
            <span className="klabel">Revised</span>
            <div className="panel-block border-l-2 border-l-emerald">{redline.revised_text}</div>
          </div>
        </div>

        <div className="flex flex-col gap-1">
          <span className="klabel">Why this change</span>
          <p className="text-sm text-muted-foreground">{redline.justification}</p>
        </div>
      </CardContent>
    </Card>
  );
}
