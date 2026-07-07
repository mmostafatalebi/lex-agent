"use client";

import Link from "next/link";
import { notFound, useParams } from "next/navigation";

import { AnalysisProgress } from "@/components/analysis-progress";
import { FlagList } from "@/components/flag-list";
import { RedlineList } from "@/components/redline-list";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api-client";
import { useAnalysisStatus } from "@/lib/hooks";

export default function AnalysisPage() {
  const params = useParams<{ thread_id: string }>();
  const threadId = params.thread_id;
  const { data, error, isLoading } = useAnalysisStatus(threadId);

  if (error) {
    if (error instanceof ApiError && error.statusCode === 404) {
      notFound();
    }
    // Bubble other failures to the global error boundary.
    throw error;
  }

  if (isLoading || !data) {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  const content = () => {
    switch (data.status) {
      case "awaiting_review":
        return <FlagList threadId={threadId} flags={data.flags ?? []} />;
      case "drafting":
        return <AnalysisProgress message="Drafting redlines..." />;
      case "complete": {
        const redlines = data.redlines ?? [];
        return <RedlineList redlines={redlines} acceptedCount={redlines.length} />;
      }
      case "failed":
        return (
          <Alert variant="destructive" data-testid="analysis-failed">
            <AlertTitle>Analysis failed</AlertTitle>
            <AlertDescription className="flex flex-col gap-3">
              <span>{data.error ?? "The analysis could not be completed."}</span>
              <Link href="/" className={buttonVariants({ variant: "outline", size: "sm" })}>
                Start over
              </Link>
            </AlertDescription>
          </Alert>
        );
    }
  };

  return <div className="mx-auto max-w-3xl">{content()}</div>;
}
