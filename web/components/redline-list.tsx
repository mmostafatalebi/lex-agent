"use client";

import Link from "next/link";

import { RedlineDiff } from "@/components/redline-diff";
import { buttonVariants } from "@/components/ui/button";
import type { Redline } from "@/lib/api-types";

export function RedlineList({
  redlines,
  acceptedCount,
}: {
  redlines: Redline[];
  acceptedCount: number;
}) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight">Your redlines</h1>
          <p className="text-sm text-muted-foreground" data-testid="redline-summary">
            {acceptedCount} {acceptedCount === 1 ? "flag" : "flags"} accepted, {redlines.length}{" "}
            {redlines.length === 1 ? "redline" : "redlines"} drafted.
          </p>
        </div>
        <Link href="/" className={buttonVariants({ variant: "outline" })}>
          Review another
        </Link>
      </div>

      {redlines.length === 0 ? (
        <div className="rounded-lg border border-border bg-panel p-8 text-center text-sm text-muted-foreground">
          No redlines were drafted, because no flags were accepted.
        </div>
      ) : (
        <div className="flex flex-col gap-4" data-testid="redline-list">
          {redlines.map((redline) => (
            <RedlineDiff key={redline.id} redline={redline} />
          ))}
        </div>
      )}
    </div>
  );
}
