"use client";

import { KeyRound } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getStoredApiKey, requireApiKey, setStoredApiKey } from "@/lib/api-client";

export function ApiKeyGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [needsKey, setNeedsKey] = useState(false);
  const [value, setValue] = useState("");

  useEffect(() => {
    setNeedsKey(requireApiKey() && !getStoredApiKey());
    setReady(true);
  }, []);

  function save() {
    if (!value.trim()) return;
    setStoredApiKey(value);
    setNeedsKey(false);
  }

  if (!ready) return null;
  if (!needsKey) return <>{children}</>;

  return (
    <Card className="mx-auto max-w-md" data-testid="api-key-gate">
      <CardHeader>
        <div className="flex items-center gap-2">
          <KeyRound className="h-5 w-5 text-primary" />
          <CardTitle>API key required</CardTitle>
        </div>
        <CardDescription>
          This backend requires an API key. Paste it below to continue. It is stored in your
          browser only.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <Input
          type="password"
          placeholder="Paste your API key"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") save();
          }}
          aria-label="API key"
        />
        <Button onClick={save} disabled={!value.trim()}>
          Save and continue
        </Button>
      </CardContent>
    </Card>
  );
}
