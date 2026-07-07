"use client";

import { ApiKeyGate } from "@/components/api-key-gate";
import { UploadZone } from "@/components/upload-zone";

const STEPS = [
  "01  upload a contract PDF or DOCX",
  "02  review each flagged clause and accept or reject",
  "03  get redlines drafted for what you accepted",
];

export default function HomePage() {
  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-8">
      <div className="flex flex-col gap-3 text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
          Review a contract in five minutes.
        </h1>
        <p className="text-lg text-muted-foreground">
          Drop in a freelance contract and get a lawyer-lite second opinion, then draft redlines
          for the terms you want to change.
        </p>
      </div>

      <ApiKeyGate>
        <UploadZone />
      </ApiKeyGate>

      <div className="rounded-lg border border-border bg-panel-2 p-4">
        <p className="klabel mb-2">How it works</p>
        <ul className="flex flex-col gap-1 font-mono text-sm text-muted-foreground">
          {STEPS.map((step) => (
            <li key={step}>{step}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
