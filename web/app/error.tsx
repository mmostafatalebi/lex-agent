"use client";

import { AlertTriangle } from "lucide-react";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Surfaced to the browser console for local debugging.
    console.error(error);
  }, [error]);

  return (
    <div
      className="mx-auto flex max-w-md flex-col items-center gap-4 py-24 text-center"
      data-testid="error-boundary"
    >
      <AlertTriangle className="h-10 w-10 text-rose" />
      <h1 className="text-xl font-semibold">Something went wrong</h1>
      <p className="text-sm text-muted-foreground">
        We could not load this analysis. This is usually temporary.
      </p>
      <Button onClick={reset} data-testid="retry-button">
        Try again
      </Button>
    </div>
  );
}
