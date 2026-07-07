"use client";

import { Loader2, UploadCloud } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";

import { toast } from "@/components/ui/toast";
import { useStartAnalysis, useUploadContract } from "@/lib/hooks";
import { ApiError } from "@/lib/api-client";
import { cn, formatBytes } from "@/lib/utils";

const MAX_BYTES = 6 * 1024 * 1024;
const ALLOWED = /\.(pdf|docx)$/i;

function messageFor(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}

export function UploadZone() {
  const router = useRouter();
  const upload = useUploadContract();
  const start = useStartAnalysis();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);

  async function handleFile(file: File | undefined) {
    if (!file) return;
    if (!ALLOWED.test(file.name)) {
      toast.error("Only PDF or DOCX files are supported.");
      return;
    }
    if (file.size > MAX_BYTES) {
      toast.error(`That file is ${formatBytes(file.size)}. The limit is 6MB.`);
      return;
    }
    setBusy(true);
    try {
      const uploaded = await upload.mutateAsync(file);
      const started = await start.mutateAsync(uploaded.contract_id);
      router.push(`/analyses/${started.thread_id}`);
    } catch (error) {
      toast.error(messageFor(error));
      setBusy(false);
    }
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload a contract"
      data-testid="upload-zone"
      onClick={() => !busy && inputRef.current?.click()}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !busy) inputRef.current?.click();
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        void handleFile(e.dataTransfer.files?.[0]);
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-border bg-panel px-6 py-16 text-center transition-colors",
        dragging && "border-primary bg-panel-2",
        busy && "pointer-events-none opacity-70"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.docx"
        className="hidden"
        data-testid="file-input"
        onChange={(e) => void handleFile(e.target.files?.[0])}
      />
      {busy ? (
        <>
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Uploading and starting analysis...</p>
        </>
      ) : (
        <>
          <UploadCloud className="h-8 w-8 text-primary" />
          <p className="font-medium">Drag a contract here, or click to choose a file</p>
          <p className="klabel">PDF or DOCX, up to 6MB</p>
        </>
      )}
    </div>
  );
}
