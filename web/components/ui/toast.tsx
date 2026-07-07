"use client";

import { Toaster as SonnerToaster } from "sonner";

// Thin wrapper over sonner so toast styling matches the theme tokens.
export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "font-sans rounded-md border border-border bg-panel text-foreground shadow-lg",
          description: "text-muted-foreground",
          error: "border-rose/40",
          success: "border-emerald/40",
        },
      }}
    />
  );
}

export { toast } from "sonner";
